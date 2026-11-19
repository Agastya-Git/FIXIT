import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection, get_database

async def main():
    await connect_to_mongo()
    db = get_database()
    tickets = await db.tickets.find({"status": {"$in": ["assigned", "in_progress"]}}).to_list(20)
    print(f"Total assigned/in_progress tickets: {len(tickets)}")
    for t in tickets:
        assigned = t.get("assigned_to") or {}
        print(f"Ticket ID: {t.get('ticket_id')} | Title: {t.get('title')} | Priority: {t.get('priority')} | Assigned: {assigned.get('name')} ({assigned.get('id')}) | Deadline: {t.get('sla_deadline')} | SLA Warning Issued: {t.get('sla_warning_issued')}")

    warnings = await db.staff_warnings.find().to_list(20)
    print(f"\nTotal staff warnings in DB: {len(warnings)}")
    for w in warnings:
        print(f"Warning: {w.get('_id')} | Staff: {w.get('staff_id')} | Ticket: {w.get('ticket_number')} | Pardoned: {w.get('pardoned')}")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
