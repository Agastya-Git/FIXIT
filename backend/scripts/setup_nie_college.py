"""
Setup National Institute of Engineering (NIE), its primary College Administrator,
and its complete campus hierarchy (campus, buildings, floors, rooms).

Run from backend directory:
    python scripts/setup_nie_college.py
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings
from app.core.security import get_password_hash

INST_ID = "INST-NIE"
ADMIN_ID = "USR-NIE-ADMIN-001"
ADMIN_EMAIL = "admin@nie.ac.in"
ADMIN_PASS = "NieAdmin@2024!"
CAMPUS_ID = "CAMPUS-NIE-MAIN"


async def main():
    print(f"Connecting to MongoDB at {settings.MONGODB_URI} (db: {settings.DATABASE_NAME})...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    await client.admin.command("ping")
    now = datetime.now(timezone.utc).isoformat()

    # 1. Institution
    print("1. Provisioning Institution: National Institute of Engineering...")
    await db.institutions.update_one(
        {"_id": INST_ID},
        {
            "$set": {
                "name": "National Institute of Engineering",
                "slug": "nie",
                "email_domains": ["nie.ac.in", "students.nie.ac.in", "faculty.nie.ac.in"],
                "student_email_domains": ["nie.ac.in", "students.nie.ac.in"],
                "faculty_email_domains": ["nie.ac.in", "faculty.nie.ac.in"],
                "status": "active",
            },
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )

    # 2. Categories & SLA templates
    print("2. Provisioning default categories and SLA policies for NIE...")
    existing_cats = await db.categories.count_documents({"institution_id": INST_ID})
    if existing_cats == 0:
        default_cats = await db.categories.find({"institution_id": "INST-DEFAULT"}).to_list(None)
        if default_cats:
            await db.categories.insert_many([
                {**{k: v for k, v in c.items() if k != "_id"}, "_id": f"CAT-{uuid.uuid4().hex[:8].upper()}", "institution_id": INST_ID}
                for c in default_cats
            ])

    existing_slas = await db.sla_policies.count_documents({"institution_id": INST_ID})
    if existing_slas == 0:
        default_slas = await db.sla_policies.find({"institution_id": "INST-DEFAULT"}).to_list(None)
        if default_slas:
            await db.sla_policies.insert_many([
                {**{k: v for k, v in s.items() if k != "_id"}, "_id": f"SLA-{uuid.uuid4().hex[:8].upper()}", "institution_id": INST_ID}
                for s in default_slas
            ])

    # 3. College Administrator User
    print(f"3. Provisioning Primary College Administrator: {ADMIN_EMAIL}...")
    await db.users.update_one(
        {"email": ADMIN_EMAIL},
        {
            "$set": {
                "name": "NIE Administrator",
                "email": ADMIN_EMAIL,
                "password_hash": get_password_hash(ADMIN_PASS),
                "role": "admin",
                "admin_level": "primary",
                "institution_id": INST_ID,
                "department": "Administration",
                "specialization": [],
                "is_active": True,
                "email_verified": True,
                "token_version": 0,
            },
            "$setOnInsert": {
                "_id": ADMIN_ID,
                "created_at": now,
            },
        },
        upsert=True,
    )

    # 4. Campus
    print("4. Provisioning Campus: National Institute of Engineering - Main Campus (NIE-MAIN)...")
    await db.campuses.update_one(
        {"_id": CAMPUS_ID},
        {
            "$set": {
                "name": "National Institute of Engineering - Main Campus",
                "code": "NIE-MAIN",
                "institution_id": INST_ID,
                "is_active": True,
            },
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )

    # 5. Buildings
    print("5. Provisioning Buildings...")
    buildings_data = [
        {"_id": "BLD-NIE-ACB", "name": "Academic Block", "code": "ACB", "total_floors": 4, "order": 1},
        {"_id": "BLD-NIE-ADM", "name": "Administrative Block", "code": "ADM", "total_floors": 2, "order": 2},
        {"_id": "BLD-NIE-LIB", "name": "Library Block", "code": "LIB", "total_floors": 3, "order": 3},
        {"_id": "BLD-NIE-CSE", "name": "Computer Science Block", "code": "CSE", "total_floors": 4, "order": 4},
    ]
    for b in buildings_data:
        await db.buildings.update_one(
            {"_id": b["_id"]},
            {
                "$set": {
                    "campus_id": CAMPUS_ID,
                    "name": b["name"],
                    "code": b["code"],
                    "total_floors": b["total_floors"],
                    "order": b["order"],
                    "institution_id": INST_ID,
                    "is_active": True,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    # 6. Floors (under Academic Block ACB)
    print("6. Provisioning Floors for Academic Block...")
    floors_data = [
        {"_id": "FLR-NIE-ACB-0", "floor_number": 0, "floor_name": "Ground Floor", "order": 0},
        {"_id": "FLR-NIE-ACB-1", "floor_number": 1, "floor_name": "First Floor", "order": 1},
        {"_id": "FLR-NIE-ACB-2", "floor_number": 2, "floor_name": "Second Floor", "order": 2},
        {"_id": "FLR-NIE-ACB-3", "floor_number": 3, "floor_name": "Third Floor", "order": 3},
    ]
    for f in floors_data:
        await db.floors.update_one(
            {"_id": f["_id"]},
            {
                "$set": {
                    "building_id": "BLD-NIE-ACB",
                    "floor_number": f["floor_number"],
                    "floor_name": f["floor_name"],
                    "order": f["order"],
                    "institution_id": INST_ID,
                    "is_active": True,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    # 7. Rooms (under Academic Block ACB)
    print("7. Provisioning Rooms and Departments for Academic Block...")
    rooms_data = [
        {"_id": "RM-NIE-ACB-G01", "room_number": "G01", "room_name": "Computer Laboratories", "floor_id": "FLR-NIE-ACB-0", "department": "Computer Science & Engineering", "order": 1},
        {"_id": "RM-NIE-ACB-G02", "room_number": "G02", "room_name": "Administrative Office", "floor_id": "FLR-NIE-ACB-0", "department": "Administration", "order": 2},
        {"_id": "RM-NIE-ACB-101", "room_number": "101", "room_name": "CSE Department", "floor_id": "FLR-NIE-ACB-1", "department": "Computer Science & Engineering", "order": 3},
        {"_id": "RM-NIE-ACB-201", "room_number": "201", "room_name": "Faculty Rooms", "floor_id": "FLR-NIE-ACB-2", "department": "Faculty", "order": 4},
        {"_id": "RM-NIE-ACB-301", "room_number": "301", "room_name": "Seminar Hall", "floor_id": "FLR-NIE-ACB-3", "department": "Academics", "order": 5},
    ]
    for r in rooms_data:
        await db.rooms.update_one(
            {"_id": r["_id"]},
            {
                "$set": {
                    "building_id": "BLD-NIE-ACB",
                    "floor_id": r["floor_id"],
                    "room_number": r["room_number"],
                    "room_name": r["room_name"],
                    "department": r["department"],
                    "order": r["order"],
                    "institution_id": INST_ID,
                    "is_active": True,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    client.close()
    print("\nSUCCESS! NIE College configuration completed successfully.")
    print(f"College Admin Login:")
    print(f"  Email:    {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASS}")
    print(f"  Role:     admin (Primary College Administrator)")
    print(f"  Campus:   National Institute of Engineering - Main Campus (NIE-MAIN)")
    print(f"  Buildings: 4 (ACB, ADM, LIB, CSE)")
    print(f"  Floors:    4 (Ground, 1st, 2nd, 3rd)")
    print(f"  Rooms:     5 (Computer Labs, Admin Office, CSE Dept, Faculty Rooms, Seminar Hall)")


if __name__ == "__main__":
    asyncio.run(main())
