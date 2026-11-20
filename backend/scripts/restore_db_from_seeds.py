"""
Restore MongoDB database from backend/seeds/*.json.
Preserves ObjectIds, datetimes, and all schema structures exactly.
Can be run anytime with:
    python backend/scripts/restore_db_from_seeds.py [--wipe]
"""
import sys
import argparse
from pathlib import Path
import pymongo
from bson import json_util

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings

SEEDS_DIR = BACKEND_DIR / "seeds"

def restore_db(wipe=False):
    if not SEEDS_DIR.exists():
        print(f"Error: Seeds directory {SEEDS_DIR} does not exist!")
        sys.exit(1)

    client = pymongo.MongoClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]

    print(f"Connecting to MongoDB database '{settings.DATABASE_NAME}'...")
    seed_files = sorted(list(SEEDS_DIR.glob("*.json")))

    if not seed_files:
        print(f"No seed JSON files found in {SEEDS_DIR}")
        return

    total_restored = 0

    for json_file in seed_files:
        col_name = json_file.stem
        col = db[col_name]

        with open(json_file, "r", encoding="utf-8") as f:
            docs = json_util.loads(f.read())

        if not docs:
            continue

        if wipe:
            col.delete_many({})

        count = 0
        for doc in docs:
            doc_id = doc.get("_id")
            if doc_id:
                col.replace_one({"_id": doc_id}, doc, upsert=True)
            else:
                col.insert_one(doc)
            count += 1

        print(f"  [+] Restored {count:>3} documents into '{col_name}'")
        total_restored += count

    print(f"\nSuccessfully restored {total_restored} documents across {len(seed_files)} collections from seeds.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore MongoDB from seeds")
    parser.add_argument("--wipe", action="store_true", help="Wipe existing collections before restoring")
    args = parser.parse_args()
    restore_db(wipe=args.wipe)
