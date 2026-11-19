from pymongo import MongoClient

c = MongoClient("mongodb://localhost:27017")
db = c["fixit_db"]
res = db.institutions.update_one(
    {"_id": "INST-NIE"},
    {"$addToSet": {
        "email_domains": "gmail.com",
        "student_email_domains": "gmail.com",
        "faculty_email_domains": "gmail.com"
    }}
)
print("Updated INST-NIE:", res.modified_count)
inst = db.institutions.find_one({"_id": "INST-NIE"})
print("Domains:", inst.get("email_domains"))
print("Student domains:", inst.get("student_email_domains"))
c.close()
