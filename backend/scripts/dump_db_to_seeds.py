"""
Export all current MongoDB collections and documents into backend/seeds/*.json.
Uses bson.json_util so ObjectIds, datetimes, and types are 100% preserved.
"""
import os
import sys
from pathlib import Path
import pymongo
from bson import json_util

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings

SEEDS_DIR = BACKEND_DIR / "seeds"

COLLECTIONS_TO_EXPORT = [
    "users",
    "tickets",
    "categories",
    "campuses",
    "buildings",
    "floors",
    "rooms",
    "departments",
    "institutions",
    "sla_policies",
    "knowledge_base",
    "staff_warnings",
    "user_preferences",
    "feedback",
    "comments",
    "notifications",
    "counters",
    "audit_logs",
]

def dump_db():
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)
    client = pymongo.MongoClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]

    print(f"Connecting to MongoDB database '{settings.DATABASE_NAME}'...")
    total_docs = 0

    for col_name in COLLECTIONS_TO_EXPORT:
        col = db[col_name]
        docs = list(col.find({}))
        file_path = SEEDS_DIR / f"{col_name}.json"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_util.dumps(docs, indent=2))
        
        print(f"  [+] Exported {len(docs):>3} documents from '{col_name}' -> {file_path.name}")
        total_docs += len(docs)

    print(f"\nSuccessfully dumped {total_docs} documents across {len(COLLECTIONS_TO_EXPORT)} collections to {SEEDS_DIR}")

if __name__ == "__main__":
    dump_db()
