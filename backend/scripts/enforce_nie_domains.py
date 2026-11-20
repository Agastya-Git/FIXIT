from pymongo import MongoClient

c = MongoClient("mongodb://localhost:27017")
db = c["fixit_db"]
res = db.institutions.update_one(
    {"_id": "INST-NIE"},
    {"$set": {
        "email_domains": ["nie.ac.in", "students.nie.ac.in", "faculty.nie.ac.in"],
        "student_email_domains": ["nie.ac.in", "students.nie.ac.in"],
        "faculty_email_domains": ["nie.ac.in", "faculty.nie.ac.in"]
    }}
)
print("Enforced NIE email domains:", res.modified_count)
inst = db.institutions.find_one({"_id": "INST-NIE"})
print("Approved domains:", inst.get("email_domains"))
print("Student domains:", inst.get("student_email_domains"))
print("Faculty domains:", inst.get("faculty_email_domains"))
c.close()
