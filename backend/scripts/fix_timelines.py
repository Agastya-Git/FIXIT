import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection, get_database

async def fix_existing_timelines():
    await connect_to_mongo()
    db = get_database()
    tickets = await db.tickets.find({"timeline": {"$exists": True}}).to_list(100)
    fixed_count = 0
    for t in tickets:
        timeline = t.get("timeline") or []
        updated = False
        new_timeline = []
        for ev in timeline:
            e = dict(ev)
            if "actor" in e and isinstance(e["actor"], dict):
                actor = e["actor"]
                e.setdefault("actor_name", actor.get("name", "System"))
                e.setdefault("actor_role", actor.get("role", "system"))
                e.setdefault("actor_id", actor.get("id", "system"))
                updated = True
            if "actor_name" not in e:
                e["actor_name"] = "System"
                updated = True
            if "actor_role" not in e:
                e["actor_role"] = "system"
                updated = True
            if "actor_id" not in e:
                e["actor_id"] = "system"
                updated = True
            if "details" in e and "note" not in e:
                e["note"] = e["details"]
                updated = True
            new_timeline.append(e)
        if updated:
            await db.tickets.update_one({"_id": t["_id"]}, {"$set": {"timeline": new_timeline}})
            fixed_count += 1
            print(f"Fixed timeline on ticket {t.get('ticket_id', t['_id'])}")
    print(f"Total tickets updated: {fixed_count}")
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(fix_existing_timelines())
