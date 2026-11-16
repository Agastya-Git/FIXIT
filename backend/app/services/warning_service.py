import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from app.core.database import get_database
from app.core.audit import record_audit_log
from app.models.ticket import TicketStatus
from app.services.notification_service import (
    send_warning_notification,
    send_strike_notification,
    send_review_required_notification_to_admins,
    notify_admins
)

logger = logging.getLogger(__name__)

# Grace periods (in hours) allowed past SLA deadline before an SLA breach warning is issued:
# - Critical: +2 hours
# - High:     +4 hours
# - Medium:   +6 hours
# - Low:      +8 hours
GRACE_PERIOD_HOURS = {
    "critical": 2,
    "high": 4,
    "medium": 6,
    "low": 8
}

# Rolling window for warnings to accumulate into strikes (30 days)
WARNING_ROLLING_WINDOW_DAYS = 30

# Maximum strikes before administrative review is mandated
MAX_STRIKES_BEFORE_REVIEW = 3


async def check_sla_breaches_and_issue_warnings() -> List[Dict[str, Any]]:
    """
    Background job: checks all active tickets past their SLA deadline + grace period.
    Issues SLA warnings against assigned staff members with complete fairness guards:
    - Excludes tickets currently on hold or on-hold time
    - Deduplicates warnings so 1 ticket produces at most 1 warning per assignment
    - Automatically bundles every 3 warnings within 30 days into 1 Strike
    - At 3 Strikes, flags staff profile as 'Review Required' and alerts administrators
    """
    db = get_database()
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    active_tickets = await db.tickets.find({
        "status": {"$in": [TicketStatus.ASSIGNED.value, TicketStatus.IN_PROGRESS.value, TicketStatus.REOPENED.value]},
        "assigned_to": {"$ne": None},
        "sla_deadline": {"$ne": None},
        "sla_warning_issued": {"$ne": True}
    }).to_list(200)

    issued_warnings = []

    for ticket in active_tickets:
        try:
            assigned_to = ticket.get("assigned_to") or {}
            staff_id = assigned_to.get("id")
            if not staff_id:
                continue

            deadline_str = ticket.get("sla_deadline")
            if not deadline_str:
                continue

            try:
                deadline_dt = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
            except Exception:
                continue

            priority = (ticket.get("priority") or "medium").lower()
            grace_hours = GRACE_PERIOD_HOURS.get(priority, 6)

            # Compute effective deadline with grace period
            effective_deadline_dt = deadline_dt + timedelta(hours=grace_hours)

            # Fairness guard: calculate cumulative on-hold duration if any
            hold_minutes = 0
            for ev in ticket.get("timeline", []):
                if ev.get("action") == "status_changed" and "on_hold" in ev.get("details", "").lower():
                    # If recorded hold duration exists
                    hold_minutes += ev.get("hold_duration_minutes", 0)

            if hold_minutes > 0:
                effective_deadline_dt += timedelta(minutes=hold_minutes)

            # Check if breached
            if now_dt <= effective_deadline_dt:
                continue

            # Deduplication guard: check if warning already exists in staff_warnings
            existing = await db.staff_warnings.find_one({
                "ticket_id": str(ticket["_id"]),
                "staff_id": staff_id
            })
            if existing:
                continue

            # Issue Warning Document
            warning_id = f"WARN-{uuid.uuid4().hex[:10].upper()}"
            institution_id = ticket.get("institution_id")
            ticket_number = ticket.get("ticket_id") or str(ticket["_id"])

            warning_doc = {
                "_id": warning_id,
                "institution_id": institution_id,
                "staff_id": staff_id,
                "ticket_id": str(ticket["_id"]),
                "ticket_number": ticket_number,
                "ticket_title": ticket.get("title"),
                "priority": priority,
                "sla_deadline": deadline_str,
                "grace_hours": grace_hours,
                "issued_at": now_iso,
                "pardoned": False,
                "pardoned_by": None,
                "pardoned_at": None,
                "pardon_reason": None,
                "strike_id": None
            }
            await db.staff_warnings.insert_one(warning_doc)

            # Mark ticket as warned
            timeline_event = {
                "action": "SLA_WARNING_ISSUED",
                "actor_id": "SYSTEM",
                "actor_name": "FixIt SLA Monitor",
                "actor_role": "system",
                "timestamp": now_iso,
                "note": f"SLA breach warning issued to {assigned_to.get('name')} (Grace period of {grace_hours}h expired)",
                "details": f"SLA breach warning issued to {assigned_to.get('name')} (Grace period of {grace_hours}h expired)"
            }
            await db.tickets.update_one(
                {"_id": ticket["_id"]},
                {
                    "$set": {"sla_warning_issued": True},
                    "$push": {"timeline": timeline_event}
                }
            )

            # Retrieve staff user details
            staff_user = await db.users.find_one({"_id": staff_id})
            if staff_user:
                await send_warning_notification(staff_user, warning_doc, ticket)

                # Check if this warning triggers a Strike (3 warnings within 30 days)
                window_start = (now_dt - timedelta(days=WARNING_ROLLING_WINDOW_DAYS)).isoformat()
                unbundled_warnings = await db.staff_warnings.find({
                    "staff_id": staff_id,
                    "pardoned": False,
                    "strike_id": None,
                    "issued_at": {"$gte": window_start}
                }).sort("issued_at", 1).to_list(100)

                if len(unbundled_warnings) >= 3:
                    # Form a Strike from the 3 oldest unbundled warnings in the window
                    strike_warnings = unbundled_warnings[:3]
                    current_strikes_count = await db.staff_strikes.count_documents({"staff_id": staff_id})
                    new_strike_num = current_strikes_count + 1

                    strike_id = f"STRK-{uuid.uuid4().hex[:10].upper()}"
                    strike_doc = {
                        "_id": strike_id,
                        "institution_id": institution_id,
                        "staff_id": staff_id,
                        "warning_ids": [w["_id"] for w in strike_warnings],
                        "issued_at": now_iso,
                        "strike_number": new_strike_num
                    }
                    await db.staff_strikes.insert_one(strike_doc)

                    # Mark warnings as linked to this strike
                    await db.staff_warnings.update_many(
                        {"_id": {"$in": [w["_id"] for w in strike_warnings]}},
                        {"$set": {"strike_id": strike_id}}
                    )

                    await send_strike_notification(staff_user, new_strike_num, strike_warnings)

                    # If staff has reached 3 strikes, flag as Review Required and alert admins
                    if new_strike_num >= MAX_STRIKES_BEFORE_REVIEW:
                        await db.users.update_one(
                            {"_id": staff_id},
                            {"$set": {"review_required": True, "review_flagged_at": now_iso}}
                        )
                        await send_review_required_notification_to_admins(staff_user, institution_id)

            issued_warnings.append(warning_doc)

        except Exception as e:
            logger.exception(f"Error checking SLA breach on ticket {ticket.get('_id')}: {e}")

    return issued_warnings


async def pardon_warning(
    warning_id: str,
    admin_id: str,
    admin_name: str,
    reason: str
) -> Dict[str, Any]:
    """
    Administrative pardon of an SLA warning ticket.
    If the warning contributed to a strike, adjusts strikes and re-checks 'review_required' flag.
    """
    db = get_database()
    warning = await db.staff_warnings.find_one({"_id": warning_id})
    if not warning:
        raise ValueError("Warning ticket not found")

    if warning.get("pardoned"):
        return warning

    now_iso = datetime.now(timezone.utc).isoformat()
    staff_id = warning["staff_id"]
    strike_id = warning.get("strike_id")

    # Mark warning as pardoned
    await db.staff_warnings.update_one(
        {"_id": warning_id},
        {"$set": {
            "pardoned": True,
            "pardoned_by": {"id": admin_id, "name": admin_name},
            "pardoned_at": now_iso,
            "pardon_reason": reason
        }}
    )

    # If this warning belonged to a strike, check if strike is still valid (needs 3 valid warnings)
    if strike_id:
        active_in_strike = await db.staff_warnings.count_documents({
            "strike_id": strike_id,
            "pardoned": False
        })
        if active_in_strike < 3:
            # Dissolve this strike
            await db.staff_strikes.delete_one({"_id": strike_id})
            # Unlink remaining warnings so they can re-accumulate if appropriate
            await db.staff_warnings.update_many(
                {"strike_id": strike_id},
                {"$set": {"strike_id": None}}
            )

    # Re-evaluate Review Required status for staff
    remaining_strikes = await db.staff_strikes.count_documents({"staff_id": staff_id})
    if remaining_strikes < MAX_STRIKES_BEFORE_REVIEW:
        await db.users.update_one(
            {"_id": staff_id},
            {"$set": {"review_required": False}}
        )

    updated_warning = await db.staff_warnings.find_one({"_id": warning_id})
    return updated_warning


async def get_staff_accountability_summary(
    staff_id: str,
    institution_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes real-time accountability metrics for a staff member:
    - active capacity (X/3 slots)
    - 30-day non-pardoned warnings count
    - total strikes count
    - review_required status
    - SLA compliance percentage
    - warning history list
    """
    db = get_database()
    now_dt = datetime.now(timezone.utc)
    window_start = (now_dt - timedelta(days=WARNING_ROLLING_WINDOW_DAYS)).isoformat()

    staff_user = await db.users.find_one({"_id": staff_id})
    if not staff_user:
        return {}

    # Active ticket count
    active_count = await db.tickets.count_documents({
        "assigned_to.id": staff_id,
        "status": {"$in": [
            TicketStatus.ASSIGNED.value,
            TicketStatus.IN_PROGRESS.value,
            TicketStatus.ON_HOLD.value,
            TicketStatus.REOPENED.value
        ]}
    })

    # Resolved count
    resolved_count = await db.tickets.count_documents({
        "assigned_to.id": staff_id,
        "status": {"$in": [TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]}
    })

    # Warnings in rolling 30-day window
    warnings_30d = await db.staff_warnings.find({
        "staff_id": staff_id,
        "pardoned": False,
        "issued_at": {"$gte": window_start}
    }).sort("issued_at", -1).to_list(50)

    # All warnings for history
    all_warnings = await db.staff_warnings.find({
        "staff_id": staff_id
    }).sort("issued_at", -1).to_list(100)

    # Strikes
    strikes = await db.staff_strikes.find({
        "staff_id": staff_id
    }).sort("issued_at", -1).to_list(10)

    # SLA Compliance rate
    total_assigned_ever = active_count + resolved_count
    total_breaches = len([w for w in all_warnings if not w.get("pardoned")])
    if total_assigned_ever > 0:
        compliance_pct = max(0, round(((total_assigned_ever - total_breaches) / total_assigned_ever) * 100, 1))
    else:
        compliance_pct = 100.0

    return {
        "staff_id": staff_id,
        "staff_name": staff_user.get("name"),
        "staff_email": staff_user.get("email"),
        "specialization": staff_user.get("specialization") or [],
        "active_tickets": active_count,
        "capacity_limit": 3,
        "resolved_tickets": resolved_count,
        "warnings_30d_count": len(warnings_30d),
        "total_warnings_count": len(all_warnings),
        "strikes_count": len(strikes),
        "review_required": staff_user.get("review_required", False),
        "sla_compliance_rate": compliance_pct,
        "warnings": all_warnings,
        "strikes": strikes
    }
