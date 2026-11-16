import re
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from app.core.database import get_database
from app.core.audit import record_audit_log
from app.models.ticket import TicketStatus
from app.services.notification_service import (
    notify_admins,
    send_assignment_email,
    send_notification,
)

logger = logging.getLogger(__name__)

# Hard capacity limit: a staff member can hold at most 3 active tickets simultaneously.
STAFF_CAPACITY_LIMIT = 3

# Active statuses that count against the staff's 3-ticket capacity limit
ACTIVE_TICKET_STATUSES = [
    TicketStatus.ASSIGNED.value,
    TicketStatus.IN_PROGRESS.value,
    TicketStatus.ON_HOLD.value,
    TicketStatus.REOPENED.value,
]

DOMAIN_KEYWORDS = {
    "technical": [
        "network", "wifi", "wi-fi", "hardware", "software", "computer", "pc",
        "laptop", "server", "lan", "printer", "scanner", "ide", "compiler",
        "portal", "email", "switch", "router", "cctv", "it", "code", "dev"
    ],
    "facilities": [
        "ac", "cooling", "fan", "light", "electrical", "power", "switchboard",
        "socket", "ups", "restroom", "plumbing", "water", "sanitation", "bench",
        "desk", "chair", "furniture", "door", "window", "lock", "elevator", "lift",
        "whiteboard", "cafeteria", "hostel", "sports", "gym"
    ],
    "administrative": [
        "portal", "marks", "fee", "admission", "id card", "certificate", "exam",
        "library", "rfid", "accounts", "admin", "office"
    ]
}


def _tokenize(text: str) -> set:
    """Extract lowercase alpha tokens of length >= 3."""
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def calculate_staff_ticket_score(
    staff: Dict[str, Any],
    category: str,
    problem_domain: Optional[str] = None
) -> Tuple[int, Dict[str, int]]:
    """
    Transparent weighted scoring out of 100 points:
    1. Specialization Match (40 pts)
       - Token overlap between category and staff specializations
    2. Workload Capacity (30 pts)
       - 0 active tickets = 30 pts
       - 1 active ticket  = 20 pts
       - 2 active tickets = 10 pts
       - 3+ active tickets = 0 pts (ineligible)
    3. Experience / Resolved Count (20 pts)
       - min(20, resolved_tickets * 2)
    4. Domain Routing (10 pts)
       - Match between problem domain and staff keywords
    """
    specializations = staff.get("specialization") or []
    cat_tokens = _tokenize(category)

    # 1. Specialization Match (up to 40 pts)
    spec_score = 0
    if specializations:
        combined_spec = " ".join(specializations).lower()
        spec_tokens = _tokenize(combined_spec)

        # Direct substring match
        has_direct = any(
            s.lower() in category.lower() or category.lower() in s.lower()
            for s in specializations
        )
        if has_direct:
            spec_score = 40
        else:
            overlap = cat_tokens.intersection(spec_tokens)
            if overlap:
                spec_score = min(40, len(overlap) * 15)
            else:
                spec_score = 5  # Small fallback if general staff
    else:
        spec_score = 5

    # 2. Workload Capacity (up to 30 pts)
    active_cnt = staff.get("active_tickets", 0)
    if active_cnt >= STAFF_CAPACITY_LIMIT:
        workload_score = 0
    else:
        workload_score = max(0, 30 - (active_cnt * 10))

    # 3. Experience / Resolved Count (up to 20 pts)
    resolved_cnt = staff.get("resolved_tickets", 0)
    exp_score = min(20, resolved_cnt * 2)

    # 4. Domain Routing (up to 10 pts)
    domain_score = 0
    if problem_domain:
        p_domain = problem_domain.lower()
        domain_kw = DOMAIN_KEYWORDS.get(p_domain, [])
        combined_spec = " ".join(specializations).lower()
        if any(kw in combined_spec for kw in domain_kw):
            domain_score = 10
        elif p_domain == "technical" and any("it" in s.lower() or "tech" in s.lower() for s in specializations):
            domain_score = 10
        elif p_domain == "facilities" and any("facility" in s.lower() or "maintenance" in s.lower() for s in specializations):
            domain_score = 10

    total_score = spec_score + workload_score + exp_score + domain_score

    breakdown = {
        "specialization": spec_score,
        "workload_capacity": workload_score,
        "experience": exp_score,
        "domain_routing": domain_score,
        "total": total_score
    }
    return total_score, breakdown


async def get_staff_workload(institution_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all active staff with their current workload metrics."""
    db = get_database()
    staff_query = {"role": "staff", "is_active": True}
    if institution_id:
        staff_query["institution_id"] = institution_id
    staff_members = await db.users.find(staff_query).to_list(None)

    workload_list = []
    for staff in staff_members:
        staff_id = str(staff["_id"])
        active_count = await db.tickets.count_documents({
            "assigned_to.id": staff_id,
            **({"institution_id": institution_id} if institution_id else {}),
            "status": {"$in": ACTIVE_TICKET_STATUSES}
        })
        resolved_count = await db.tickets.count_documents({
            "assigned_to.id": staff_id,
            **({"institution_id": institution_id} if institution_id else {}),
            "status": {"$in": [TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]}
        })

        workload_list.append({
            "staff_id": staff_id,
            "name": staff.get("name"),
            "email": staff.get("email"),
            "specialization": staff.get("specialization") or [],
            "active_tickets": active_count,
            "capacity_limit": STAFF_CAPACITY_LIMIT,
            "has_capacity": active_count < STAFF_CAPACITY_LIMIT,
            "resolved_tickets": resolved_count,
            "is_active": staff.get("is_active", True)
        })

    return workload_list


async def find_best_staff_for_ticket(
    category: str,
    institution_id: Optional[str] = None,
    problem_domain: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Automatic assignment with transparent weighted scoring and hard capacity cap (max 3 tickets).
    If all eligible staff are at capacity (active_tickets >= 3) or no staff found:
    Returns None (ticket stays queued as unassigned).
    """
    workload_list = await get_staff_workload(institution_id)
    if not workload_list:
        await notify_admins(
            title="Auto-Assignment Alert: No Staff Available",
            message=f"Ticket under category '{category}' could not be assigned. No active staff found in institution.",
            notif_type="system_alert",
            institution_id=institution_id
        )
        return None

    # Filter only staff that currently have capacity (< 3 active tickets)
    available_candidates = [s for s in workload_list if s["has_capacity"]]

    if not available_candidates:
        logger.info(f"All {len(workload_list)} staff members are at maximum capacity (3 tickets). Ticket queued.")
        return None

    scored_candidates = []
    for s in available_candidates:
        score, breakdown = calculate_staff_ticket_score(s, category, problem_domain)
        scored_candidates.append({
            **s,
            "score": score,
            "scoring_breakdown": breakdown
        })

    # Sort descending by score, tie-break by fewest active tickets, then most resolved
    scored_candidates.sort(
        key=lambda x: (x["score"], -x["active_tickets"], x["resolved_tickets"]),
        reverse=True
    )

    best = scored_candidates[0]

    db = get_database()
    staff_query = {"_id": best["staff_id"]}
    if institution_id:
        staff_query["institution_id"] = institution_id
    staff_user = await db.users.find_one(staff_query)
    if staff_user:
        return {
            "id": str(staff_user["_id"]),
            "name": staff_user["name"],
            "email": staff_user["email"],
            "role": staff_user["role"],
            "specialization": staff_user.get("specialization", []),
            "active_tickets": best["active_tickets"],
            "capacity_limit": STAFF_CAPACITY_LIMIT,
            "scoring_breakdown": best["scoring_breakdown"]
        }
    return None


async def check_queue_and_assign(staff_id: str, institution_id: Optional[str] = None) -> List[str]:
    """
    Triggered when a staff member resolves or closes a ticket.
    Checks remaining capacity for this staff member (max 3 active tickets).
    If capacity opens up, automatically pulls the oldest unassigned matching tickets from the queue,
    assigns them to the staff member, and triggers the rich assignment email!
    """
    db = get_database()
    staff_user = await db.users.find_one({"_id": staff_id, "is_active": True})
    if not staff_user:
        return []

    active_count = await db.tickets.count_documents({
        "assigned_to.id": staff_id,
        **({"institution_id": institution_id} if institution_id else {}),
        "status": {"$in": ACTIVE_TICKET_STATUSES}
    })

    slots_available = STAFF_CAPACITY_LIMIT - active_count
    if slots_available <= 0:
        return []

    # Find unassigned open tickets in queue
    queue_filter = {
        "status": TicketStatus.OPEN.value,
        "$or": [
            {"assigned_to": None},
            {"assigned_to": {"$exists": False}}
        ]
    }
    if institution_id:
        queue_filter["institution_id"] = institution_id

    # Get candidate tickets sorted by creation date (oldest first)
    queued_tickets = await db.tickets.find(queue_filter).sort("created_at", 1).to_list(50)
    if not queued_tickets:
        return []

    assigned_ticket_ids = []
    now = datetime.now(timezone.utc).isoformat()

    staff_data_for_scoring = {
        "specialization": staff_user.get("specialization") or [],
        "active_tickets": active_count,
        "resolved_tickets": await db.tickets.count_documents({
            "assigned_to.id": staff_id,
            "status": {"$in": [TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]}
        })
    }

    # Score queued tickets against this staff's specializations
    scored_queue = []
    for ticket in queued_tickets:
        score, breakdown = calculate_staff_ticket_score(
            staff_data_for_scoring,
            ticket.get("category", ""),
            ticket.get("problem_domain")
        )
        scored_queue.append((score, ticket))

    # Highest score first
    scored_queue.sort(key=lambda item: item[0], reverse=True)

    for score, ticket in scored_queue[:slots_available]:
        ticket_id = ticket["_id"]
        assigned_obj = {
            "id": str(staff_user["_id"]),
            "name": staff_user["name"],
            "email": staff_user["email"],
            "role": staff_user["role"],
            "assigned_at": now
        }

        # Calculate SLA deadline from assignment time if not already active
        sla_hours = ticket.get("sla_target_hours") or 24
        from datetime import timedelta
        deadline_dt = datetime.now(timezone.utc) + timedelta(hours=sla_hours)

        update_fields = {
            "assigned_to": assigned_obj,
            "status": TicketStatus.ASSIGNED.value,
            "assigned_at": now,
            "sla_deadline": deadline_dt.isoformat(),
            "updated_at": now
        }

        timeline_event = {
            "action": "auto_assigned_from_queue",
            "actor": {
                "id": "SYSTEM",
                "name": "FixIt Auto-Assignment Queue",
                "role": "system"
            },
            "timestamp": now,
            "details": f"Automatically assigned to {staff_user['name']} upon capacity availability (Score: {score}/100)"
        }

        await db.tickets.update_one(
            {"_id": ticket_id},
            {
                "$set": update_fields,
                "$push": {"timeline": timeline_event}
            }
        )

        # Notify staff with full assignment email
        updated_ticket = await db.tickets.find_one({"_id": ticket_id})
        await send_assignment_email(staff_user, updated_ticket)
        assigned_ticket_ids.append(str(ticket_id))

    return assigned_ticket_ids


async def reevaluate_assignments_for_new_staff(
    new_staff_user: Dict[str, Any],
    institution_id: Optional[str] = None
) -> int:
    """
    Triggered when a new staff member is activated or added.
    Re-scores unassigned and pending 'assigned' (strictly NOT in_progress) tickets.
    If the new staff member is a better match and has capacity, reassigns the ticket
    and notifies both the previous assignee and the new staff member.
    """
    db = get_database()
    new_staff_id = str(new_staff_user["_id"])

    # Check capacity of new staff
    active_count = await db.tickets.count_documents({
        "assigned_to.id": new_staff_id,
        "status": {"$in": ACTIVE_TICKET_STATUSES}
    })
    slots_left = STAFF_CAPACITY_LIMIT - active_count
    if slots_left <= 0:
        return 0

    # 1. First, check unassigned queued tickets
    assigned_from_queue = await check_queue_and_assign(new_staff_id, institution_id)
    slots_left -= len(assigned_from_queue)
    if slots_left <= 0:
        return len(assigned_from_queue)

    # 2. Next, check 'assigned' tickets that have not yet been started (NOT in_progress)
    reassign_query = {
        "status": TicketStatus.ASSIGNED.value,
        "assigned_to.id": {"$ne": new_staff_id}
    }
    if institution_id:
        reassign_query["institution_id"] = institution_id

    candidate_tickets = await db.tickets.find(reassign_query).to_list(30)
    reassigned_count = 0
    now = datetime.now(timezone.utc).isoformat()

    new_staff_data = {
        "specialization": new_staff_user.get("specialization") or [],
        "active_tickets": active_count,
        "resolved_tickets": 0
    }

    for ticket in candidate_tickets:
        if slots_left <= 0:
            break

        new_score, _ = calculate_staff_ticket_score(
            new_staff_data,
            ticket.get("category", ""),
            ticket.get("problem_domain")
        )

        old_assignee = ticket.get("assigned_to") or {}
        old_staff_id = old_assignee.get("id")

        # Get old staff's current score
        old_staff_user = await db.users.find_one({"_id": old_staff_id}) if old_staff_id else None
        old_score = 0
        if old_staff_user:
            old_active = await db.tickets.count_documents({
                "assigned_to.id": old_staff_id,
                "status": {"$in": ACTIVE_TICKET_STATUSES}
            })
            old_score, _ = calculate_staff_ticket_score(
                {
                    "specialization": old_staff_user.get("specialization") or [],
                    "active_tickets": old_active,
                    "resolved_tickets": 0
                },
                ticket.get("category", ""),
                ticket.get("problem_domain")
            )

        # Reassign only if the new staff has a clearly better match (+15 points higher)
        if new_score >= old_score + 15:
            ticket_id = ticket["_id"]
            new_assigned_obj = {
                "id": new_staff_id,
                "name": new_staff_user["name"],
                "email": new_staff_user["email"],
                "role": new_staff_user["role"],
                "assigned_at": now
            }

            timeline_event = {
                "action": "reassigned_optimized",
                "actor": {
                    "id": "SYSTEM",
                    "name": "FixIt Auto-Assignment Optimizer",
                    "role": "system"
                },
                "timestamp": now,
                "details": f"Optimized assignment transferred from {old_assignee.get('name')} to {new_staff_user['name']} (Score improved: {old_score} -> {new_score})"
            }

            await db.tickets.update_one(
                {"_id": ticket_id},
                {
                    "$set": {
                        "assigned_to": new_assigned_obj,
                        "assigned_at": now,
                        "updated_at": now
                    },
                    "$push": {"timeline": timeline_event}
                }
            )

            # Notify old staff about reassignment
            if old_staff_id:
                await send_notification(
                    user_id=old_staff_id,
                    title="Task Reassigned to Domain Specialist",
                    message=f"Ticket {ticket.get('ticket_id')} has been reassigned to {new_staff_user['name']} to balance workload with domain specialization.",
                    link=f"/tickets/{ticket_id}",
                    notif_type="ticket_reassigned"
                )

            # Send rich assignment email to new staff
            updated_ticket = await db.tickets.find_one({"_id": ticket_id})
            await send_assignment_email(new_staff_user, updated_ticket)

            slots_left -= 1
            reassigned_count += 1

    return len(assigned_from_queue) + reassigned_count
