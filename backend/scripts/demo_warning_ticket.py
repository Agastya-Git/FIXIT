import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from datetime import datetime, timezone, timedelta
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.services.warning_service import (
    check_sla_breaches_and_issue_warnings,
    get_staff_accountability_summary,
    pardon_warning,
    GRACE_PERIOD_HOURS
)

async def demo():
    await connect_to_mongo()
    db = get_database()

    print("=" * 60)
    print("FixIt SLA Breach Warning & Staff Accountability Demo")
    print("=" * 60)

    # 1. Inspect active assigned tickets
    active_ticket = await db.tickets.find_one({
        "status": {"$in": ["assigned", "in_progress"]},
        "assigned_to": {"$ne": None}
    })

    if not active_ticket:
        print("No active assigned tickets found. Please create or assign a ticket first.")
        await close_mongo_connection()
        return

    ticket_id = active_ticket.get("ticket_id") or str(active_ticket["_id"])
    staff = active_ticket.get("assigned_to", {})
    staff_id = staff.get("id")
    staff_name = staff.get("name")
    priority = (active_ticket.get("priority") or "medium").lower()
    grace = GRACE_PERIOD_HOURS.get(priority, 6)

    print(f"\n1. Target Ticket: {ticket_id}")
    print(f"   Title:    {active_ticket.get('title')}")
    print(f"   Priority: {priority.upper()} (Grace period: {grace} hours)")
    print(f"   Assigned: {staff_name} ({staff_id})")

    # 2. Check current accountability summary before breach
    summary_before = await get_staff_accountability_summary(staff_id, active_ticket.get("institution_id"))
    print(f"\n2. Accountability Record BEFORE Warning:")
    print(f"   Active Workload:   {summary_before.get('active_tickets')} / 3")
    print(f"   30-Day Warnings:   {summary_before.get('warnings_30d_count')}")
    print(f"   Strikes:           {summary_before.get('strikes_count')} / 3")
    print(f"   SLA Compliance:    {summary_before.get('sla_compliance_rate')}%")
    print(f"   Review Required:   {summary_before.get('review_required')}")

    # 3. Simulate an SLA breach: backdate sla_deadline past the grace period
    past_deadline = (datetime.now(timezone.utc) - timedelta(hours=grace + 3)).isoformat()
    await db.tickets.update_one(
        {"_id": active_ticket["_id"]},
        {"$set": {
            "sla_deadline": past_deadline,
            "sla_warning_issued": False
        }}
    )
    # Clear any previous warning for this specific test ticket
    await db.staff_warnings.delete_many({
        "ticket_id": str(active_ticket["_id"]),
        "staff_id": staff_id
    })

    print(f"\n3. Simulating SLA breach...")
    print(f"   Backdated SLA deadline to: {past_deadline} (exceeded deadline + {grace}h grace)")

    # 4. Trigger SLA evaluation
    print(f"\n4. Running SLA Breach Check...")
    issued = await check_sla_breaches_and_issue_warnings()
    print(f"   SLA check completed. Total warnings issued: {len(issued)}")
    for w in issued:
        print(f"   -> Warning ID: {w.get('_id')} for Ticket: {w.get('ticket_number')}")

    # 5. Check accountability summary AFTER warning
    summary_after = await get_staff_accountability_summary(staff_id, active_ticket.get("institution_id"))
    print(f"\n5. Accountability Record AFTER Warning:")
    print(f"   Active Workload:   {summary_after.get('active_tickets')} / 3")
    print(f"   30-Day Warnings:   {summary_after.get('warnings_30d_count')}")
    print(f"   Strikes:           {summary_after.get('strikes_count')} / 3")
    print(f"   SLA Compliance:    {summary_after.get('sla_compliance_rate')}%")
    print(f"   Review Required:   {summary_after.get('review_required')}")

    # 6. Display the latest warning details
    latest_warning = await db.staff_warnings.find_one({"staff_id": staff_id}, sort=[("issued_at", -1)])
    if latest_warning:
        print(f"\n6. Warning Document Created:")
        print(f"   ID:         {latest_warning.get('_id')}")
        print(f"   Issued At:  {latest_warning.get('issued_at')}")
        print(f"   Pardoned:   {latest_warning.get('pardoned')}")

    print("\n" + "=" * 60)
    print("Demo complete! Now refresh the Staff Dashboard or Admin Dashboard")
    print("to see the warning reflected in real-time.")
    print("=" * 60)

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(demo())
