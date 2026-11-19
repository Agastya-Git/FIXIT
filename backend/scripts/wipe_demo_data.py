"""
Wipe all demo/seed data from MongoDB.
Keeps: INST-PLATFORM, INST-NIE, and all users belonging to those institutions.
Removes: INST-DEFAULT and everything tied to it (users, tickets, categories, etc.)
"""
from pymongo import MongoClient

KEEP_INSTITUTIONS = {"INST-PLATFORM", "INST-NIE"}
DEMO_INSTITUTION  = "INST-DEFAULT"

c  = MongoClient("mongodb://localhost:27017")
db = c["fixit_db"]

# ── 1. Remove INST-DEFAULT institution document ────────────────────────────────
r = db.institutions.delete_many({"_id": {"$nin": list(KEEP_INSTITUTIONS)}})
print(f"Institutions removed : {r.deleted_count}")

# ── 2. Remove users that belong to demo institution ───────────────────────────
r = db.users.delete_many({"institution_id": DEMO_INSTITUTION})
print(f"Demo users removed   : {r.deleted_count}")

# ── 3. Remove tickets ──────────────────────────────────────────────────────────
r = db.tickets.delete_many({"institution_id": DEMO_INSTITUTION})
print(f"Tickets removed      : {r.deleted_count}")

# Also remove any stray tickets not tied to a real institution
real_inst_ids = [d["_id"] for d in db.institutions.find({}, {"_id": 1})]
r = db.tickets.delete_many({"institution_id": {"$nin": real_inst_ids}})
print(f"Orphan tickets removed: {r.deleted_count}")

# ── 4. Categories ──────────────────────────────────────────────────────────────
r = db.categories.delete_many({"institution_id": DEMO_INSTITUTION})
print(f"Categories removed   : {r.deleted_count}")

# ── 5. SLA policies ───────────────────────────────────────────────────────────
r = db.sla_policies.delete_many({"institution_id": DEMO_INSTITUTION})
print(f"SLA policies removed : {r.deleted_count}")

# ── 6. Notifications ──────────────────────────────────────────────────────────
r = db.notifications.delete_many({"institution_id": DEMO_INSTITUTION})
print(f"Notifications removed: {r.deleted_count}")

# ── 7. Audit logs tied to demo ────────────────────────────────────────────────
r = db.audit_logs.delete_many({"institution_id": DEMO_INSTITUTION})
print(f"Audit logs removed   : {r.deleted_count}")

# ── 8. Pending registrations for demo ─────────────────────────────────────────
r = db.pending_registrations.delete_many({"institution_id": DEMO_INSTITUTION})
print(f"Pending regs removed : {r.deleted_count}")

# ── 9. Stale password reset / refresh tokens for deleted users ────────────────
real_user_ids = [str(d["_id"]) for d in db.users.find({}, {"_id": 1})]
r = db.password_reset_tokens.delete_many({"user_id": {"$nin": real_user_ids}})
print(f"Stale reset tokens   : {r.deleted_count}")
r = db.refresh_tokens.delete_many({"user_id": {"$nin": real_user_ids}})
print(f"Stale refresh tokens : {r.deleted_count}")

# ── 10. Rate-limit buckets (clear all — harmless) ─────────────────────────────
r = db.rate_limit_counters.delete_many({})
print(f"Rate-limit buckets   : {r.deleted_count}")

c.close()

print("\n✅ Done. Remaining institutions:")
c2 = MongoClient("mongodb://localhost:27017")
db2 = c2["fixit_db"]
for inst in db2.institutions.find():
    print(f"  {inst['_id']} | {inst.get('name')} | {inst.get('status')}")
print("\nRemaining users:")
for u in db2.users.find({}, {"email": 1, "role": 1, "institution_id": 1}):
    print(f"  {u['email']} | {u['role']} | inst={u.get('institution_id')}")
c2.close()
