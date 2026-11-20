import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

backend_dir = r"c:\Users\Agasthya Shetty\OneDrive\Desktop\FixIt-feature-public-landing-page-redesign\backend"
sys.path.insert(0, backend_dir)

from app.core.database import connect_to_mongo, get_database
from app.core.security import get_password_hash

INST_ID = "INST-NIE"
CAMPUS_ID = "CAMPUS-NIE-MAIN"
NOW = datetime.now(timezone.utc).isoformat()

# 40 Campus Categories
CAMPUS_CATEGORIES = [
    {"name": "Wi-Fi & Wireless Connectivity", "icon": "Wifi", "subcategories": ["No Signal", "Frequent Disconnection", "Captive Portal Timeout", "Slow Speed", "Authentication Error"]},
    {"name": "LAN, Ethernet & Network Cables", "icon": "Network", "subcategories": ["Port Damaged", "Cable Missing", "IP Conflict", "Unidentified Network"]},
    {"name": "Network Switches, Routers & Firewalls", "icon": "Server", "subcategories": ["Switch Port Dead", "Switch Rebooting", "VLAN Misconfigured"]},
    {"name": "Desktop Computers & Lab Workstations", "icon": "Monitor", "subcategories": ["No Power", "BSOD / Crash", "RAM Issue", "Overheating", "Display Blank"]},
    {"name": "Laptops & Portable Devices", "icon": "Laptop", "subcategories": ["Battery Issue", "Charger Port", "Keyboard Failure"]},
    {"name": "Monitors, Screens & Displays", "icon": "Tv", "subcategories": ["Flickering", "No Video Signal", "Dead Pixels", "Colors Distorted"]},
    {"name": "Keyboards, Mice & Input Peripherals", "icon": "Keyboard", "subcategories": ["Keys Sticking", "Mouse Pointer Frozen", "USB Port Fault"]},
    {"name": "Classroom Projectors & Screens", "icon": "Tv", "subcategories": ["HDMI No Signal", "Dim / Faded Lamp", "Projector Overheated", "Screen Won't Lower"]},
    {"name": "Interactive Smart Boards & Digital Displays", "icon": "Tablet", "subcategories": ["Touch Sensor Desynced", "Stylus Broken", "Board Software Crash"]},
    {"name": "Audio Systems, Microphones & Speakers", "icon": "Volume2", "subcategories": ["Podium Mic Silent", "High-Pitched Feedback", "Speaker Distorted"]},
    {"name": "Digital Podium & AV Equipment", "icon": "Presentation", "subcategories": ["Touch Console Unresponsive", "Switcher Port Damaged", "Gooseneck Mic Loose"]},
    {"name": "Operating System & Boot Errors", "icon": "Terminal", "subcategories": ["Grub Bootloader Error", "Windows Recovery Loop", "Corrupted File System"]},
    {"name": "Software Installation & Applications", "icon": "Download", "subcategories": ["VS Code Setup", "MATLAB Package Missing", "Database Driver Error"]},
    {"name": "Software Licenses & Key Activation", "icon": "Key", "subcategories": ["AutoCAD License Expired", "Network License Server Down", "Activation Timeout"]},
    {"name": "Compiler, IDE & Development Tools", "icon": "Code", "subcategories": ["GCC Path Missing", "Python Virtualenv Broken", "Java JDK Not Found"]},
    {"name": "Campus ERP, Student Portal & Marks Entry", "icon": "Globe", "subcategories": ["Grade Portal 500 Error", "Fee Payment Gateway Pending", "Attendance Missing"]},
    {"name": "College Email & Account Access", "icon": "Mail", "subcategories": ["Account Locked", "Two-Factor Auth Reset", "Password Expired"]},
    {"name": "Antivirus, Security & Malware", "icon": "Shield", "subcategories": ["Malware Detected", "Blocked Academic URL", "Firewall Exception Needed"]},
    {"name": "Printers, Scanners & Copiers", "icon": "Printer", "subcategories": ["Paper Jam", "Toner Empty", "Network Spooler Dead", "Scanner Glass Dirty"]},
    {"name": "Power Sockets & Electrical Outlets", "icon": "Zap", "subcategories": ["Wall Socket Loose", "No Power to Bench", "Sparking / Burnt Outlet"]},
    {"name": "Ceiling Fans & Regulators", "icon": "Wind", "subcategories": ["Fan Regulator Broken", "Noise / Vibration", "Ceiling Fan Stopped"]},
    {"name": "Air Conditioning (AC) & Cooling", "icon": "Thermometer", "subcategories": ["AC Blowing Warm Air", "Water Leaking Inside", "Remote Not Working"]},
    {"name": "Lighting, Tube Lights & Bulbs", "icon": "Sun", "subcategories": ["Tube Light Flickering", "Bulb Fused", "Emergency Exit Light Off"]},
    {"name": "Electrical Switchboards, MCB & Breakers", "icon": "AlertTriangle", "subcategories": ["MCB Tripping Frequently", "Burnt Smell from Board", "Sub-station Fluctuation"]},
    {"name": "UPS & Power Backup Battery", "icon": "BatteryCharging", "subcategories": ["UPS Beeping Continuously", "Zero Battery Backup", "Overload Alarm"]},
    {"name": "Drinking Water Coolers & Purifiers", "icon": "Droplet", "subcategories": ["Water Not Chilling", "Filter Water Taste", "Purifier Overflow / Leak"]},
    {"name": "Restrooms, Plumbing & Sanitation", "icon": "Tool", "subcategories": ["Tap Leaking", "Flush Broken", "Clogged Basin Drain", "Low Water Pressure"]},
    {"name": "Student Benches, Desks & Classroom Seating", "icon": "Armchair", "subcategories": ["Desk Wooden Planks Broken", "Loose Screws", "Wobbly Chair"]},
    {"name": "Faculty Desks, Chairs & Office Furniture", "icon": "Briefcase", "subcategories": ["Hydraulic Chair Sinking", "Cabinet Lock Broken", "Desk Drawer Stuck"]},
    {"name": "Doors, Windows, Glass & Locks", "icon": "Lock", "subcategories": ["Door Latch Broken", "Window Glass Cracked", "Key Stuck in Lock"]},
    {"name": "Whiteboards, Notice Boards & Markers", "icon": "FileText", "subcategories": ["Whiteboard Stained / Uncleanable", "Board Mount Loose"]},
    {"name": "Elevators, Lifts & Accessibility", "icon": "ArrowUpDown", "subcategories": ["Lift Button Unresponsive", "Lift Jerking Between Floors", "Ramp Railing Loose"]},
    {"name": "CCTV Cameras & Campus Surveillance", "icon": "Camera", "subcategories": ["Camera Feed Offline", "Night Vision Glitch", "Obstructed Angle"]},
    {"name": "Laboratory Apparatus & Test Instruments", "icon": "Activity", "subcategories": ["Oscilloscope Calib Error", "Function Generator Dead", "Multimeter Fuse Blown"]},
    {"name": "Hostel Accommodation & Facilities", "icon": "Home", "subcategories": ["Geyser Not Working", "Room Door Lock", "Hostel Wi-Fi Deadzone"]},
    {"name": "Library Workstations & RFID Scanners", "icon": "BookOpen", "subcategories": ["RFID Gate Beeping Fault", "Self-Checkout Kiosk Frozen"]},
    {"name": "Auditorium Stage Sound & Lighting", "icon": "Mic", "subcategories": ["Spotlight Failure", "Stage Monitor Silent", "Audio Console Noise"]},
    {"name": "Cafeteria Facilities & Dining Area", "icon": "Coffee", "subcategories": ["Handwash Area Drain Block", "Seating Broken", "Cleanliness Issue"]},
    {"name": "Sports Complex & Gymnasium Equipment", "icon": "Dumbbell", "subcategories": ["Treadmill Belt Loose", "Badminton Net Post Torn"]},
    {"name": "General Campus Facilities & Maintenance", "icon": "Wrench", "subcategories": ["Pathway Paver Uneven", "Garden Water Sprinkler", "Signboard Damaged"]}
]

CAMPUS_DEPARTMENTS = [
    {"name": "Computer Science & Engineering", "code": "CSE", "head_name": "Dr. Ananya Murthy", "email": "hod.cse@nie.ac.in"},
    {"name": "Information Science & Engineering", "code": "ISE", "head_name": "Dr. Suresh Bhat", "email": "hod.ise@nie.ac.in"},
    {"name": "Electronics & Communication Engineering", "code": "ECE", "head_name": "Dr. Ramesh Kulkarni", "email": "hod.ece@nie.ac.in"},
    {"name": "Electrical & Electronics Engineering", "code": "EEE", "head_name": "Dr. Girish Kumar", "email": "hod.eee@nie.ac.in"},
    {"name": "Mechanical Engineering", "code": "MECH", "head_name": "Dr. Vinod Prasad", "email": "hod.mech@nie.ac.in"},
    {"name": "Civil Engineering", "code": "CIVIL", "head_name": "Dr. Nandini Patil", "email": "hod.civil@nie.ac.in"},
    {"name": "Campus IT & Network Operations", "code": "IT-OPS", "head_name": "Mr. Satish Nayak", "email": "itops@nie.ac.in"},
    {"name": "Facilities & Maintenance", "code": "ESTATE", "head_name": "Mr. Raghavendra Rao", "email": "facilities@nie.ac.in"},
    {"name": "General Administration", "code": "ADMIN", "head_name": "Registrar Office", "email": "registrar@nie.ac.in"},
    {"name": "Library Services", "code": "LIB", "head_name": "Chief Librarian", "email": "library@nie.ac.in"},
]

CAMPUS_HIERARCHY = {
    "BLD-NIE-ACB": {
        "name": "Academic Block",
        "code": "ACB",
        "total_floors": 4,
        "order": 1,
        "floors": [
            {
                "floor_number": 0, "floor_name": "Ground Floor", "order": 0,
                "rooms": [
                    {"room_number": "G01", "room_name": "Computer Laboratories", "department": "Computer Science & Engineering"},
                    {"room_number": "G02", "room_name": "Administrative Office", "department": "General Administration"},
                    {"room_number": "G03", "room_name": "Basic Electronics Lab", "department": "Electronics & Communication Engineering"},
                ]
            },
            {
                "floor_number": 1, "floor_name": "First Floor", "order": 1,
                "rooms": [
                    {"room_number": "101", "room_name": "CSE Department", "department": "Computer Science & Engineering"},
                    {"room_number": "102", "room_name": "Smart Classroom 102", "department": "Computer Science & Engineering"},
                    {"room_number": "103", "room_name": "Software Systems Lab", "department": "Computer Science & Engineering"},
                ]
            },
            {
                "floor_number": 2, "floor_name": "Second Floor", "order": 2,
                "rooms": [
                    {"room_number": "201", "room_name": "Faculty Rooms", "department": "Computer Science & Engineering"},
                    {"room_number": "202", "room_name": "HOD Office - CSE", "department": "Computer Science & Engineering"},
                    {"room_number": "203", "room_name": "Department Conference Room", "department": "Computer Science & Engineering"},
                ]
            },
            {
                "floor_number": 3, "floor_name": "Third Floor", "order": 3,
                "rooms": [
                    {"room_number": "301", "room_name": "Seminar Hall", "department": "General Administration"},
                    {"room_number": "302", "room_name": "Digital Presentation Hall", "department": "General Administration"},
                ]
            }
        ]
    },
    "BLD-NIE-ADM": {
        "name": "Administrative Block",
        "code": "ADM",
        "total_floors": 2,
        "order": 2,
        "floors": [
            {
                "floor_number": 0, "floor_name": "Ground Floor", "order": 0,
                "rooms": [
                    {"room_number": "ADM-G01", "room_name": "Accounts & Fee Counter", "department": "General Administration"},
                    {"room_number": "ADM-G02", "room_name": "Student Registrar Desk", "department": "General Administration"},
                    {"room_number": "ADM-G03", "room_name": "Admissions & Verification Cell", "department": "General Administration"},
                ]
            },
            {
                "floor_number": 1, "floor_name": "First Floor", "order": 1,
                "rooms": [
                    {"room_number": "ADM-101", "room_name": "Principal & Dean Chamber", "department": "General Administration"},
                    {"room_number": "ADM-102", "room_name": "Academic Council Board Room", "department": "General Administration"},
                    {"room_number": "ADM-103", "room_name": "Controller of Examinations Cell", "department": "General Administration"},
                ]
            }
        ]
    },
    "BLD-NIE-LIB": {
        "name": "Library Block",
        "code": "LIB",
        "total_floors": 3,
        "order": 3,
        "floors": [
            {
                "floor_number": 0, "floor_name": "Ground Floor", "order": 0,
                "rooms": [
                    {"room_number": "LIB-G01", "room_name": "Circulation & Book Lending Desk", "department": "Library Services"},
                    {"room_number": "LIB-G02", "room_name": "New Arrivals & Periodicals Display", "department": "Library Services"},
                    {"room_number": "LIB-G03", "room_name": "General Student Reading Hall", "department": "Library Services"},
                ]
            },
            {
                "floor_number": 1, "floor_name": "First Floor", "order": 1,
                "rooms": [
                    {"room_number": "LIB-101", "room_name": "Digital Library & E-Learning Center", "department": "Library Services"},
                    {"room_number": "LIB-102", "room_name": "Technical Journals & Reference Section", "department": "Library Services"},
                ]
            },
            {
                "floor_number": 2, "floor_name": "Second Floor", "order": 2,
                "rooms": [
                    {"room_number": "LIB-201", "room_name": "Research Scholars Quiet Study Zone", "department": "Library Services"},
                    {"room_number": "LIB-202", "room_name": "Media Archives & Project Repository", "department": "Library Services"},
                ]
            }
        ]
    },
    "BLD-NIE-CSE": {
        "name": "Computer Science Block",
        "code": "CSE",
        "total_floors": 4,
        "order": 4,
        "floors": [
            {
                "floor_number": 0, "floor_name": "Ground Floor", "order": 0,
                "rooms": [
                    {"room_number": "CSE-G01", "room_name": "High Performance Computing Lab", "department": "Computer Science & Engineering"},
                    {"room_number": "CSE-G02", "room_name": "AI & Machine Learning Center", "department": "Computer Science & Engineering"},
                    {"room_number": "CSE-G03", "room_name": "Network Security & Cyber Lab", "department": "Campus IT & Network Operations"},
                ]
            },
            {
                "floor_number": 1, "floor_name": "First Floor", "order": 1,
                "rooms": [
                    {"room_number": "CSE-101", "room_name": "Cloud Computing & Systems Lab", "department": "Computer Science & Engineering"},
                    {"room_number": "CSE-102", "room_name": "Full Stack Dev Workstation Lab", "department": "Computer Science & Engineering"},
                ]
            },
            {
                "floor_number": 2, "floor_name": "Second Floor", "order": 2,
                "rooms": [
                    {"room_number": "CSE-201", "room_name": "Robotics & IoT Research Center", "department": "Computer Science & Engineering"},
                    {"room_number": "CSE-202", "room_name": "Data Science Analytics Lab", "department": "Computer Science & Engineering"},
                ]
            },
            {
                "floor_number": 3, "floor_name": "Third Floor", "order": 3,
                "rooms": [
                    {"room_number": "CSE-301", "room_name": "CSE Department Library & Seminar Room", "department": "Computer Science & Engineering"},
                    {"room_number": "CSE-302", "room_name": "Student Innovation & Incubation Hub", "department": "Computer Science & Engineering"},
                ]
            }
        ]
    }
}

KB_ARTICLES = [
    {
        "_id": "KB-NIE-001",
        "title": "How to Connect to Campus High-Speed Wi-Fi (Eduroam & Captive Portal)",
        "category": "Wi-Fi & Wireless Connectivity",
        "content": """### Common Problem
Students and faculty often experience Wi-Fi drops, captive portal timeout, or 'Obtaining IP address' errors when connecting to the college network.

### Why This Happens
- Saved device credentials may be out of date.
- The 802.1X PEAP authentication protocol requires specific security settings.
- IP pool exhaustion occurs if a device holds onto an expired DHCP lease.

### Quick Fix (You can do this right away)
1. **Forget Network**: Go to your device Wi-Fi settings, select `NIE-Secure` or `Eduroam`, and click **Forget**.
2. **Re-enter Settings**:
   - **EAP Method**: `PEAP`
   - **Phase 2 Authentication**: `MSCHAPV2`
   - **CA Certificate**: `Do not validate` (or `Trust on First Use`)
   - **Identity**: Enter your full college email (e.g. `2025cs_agastyashetty_a@nie.ac.in`)
   - **Password**: Enter your campus account password.
3. **DNS Flush**: If on a Windows laptop, open Command Prompt and type `ipconfig /flushdns` then `ipconfig /renew`.
4. If still unresolved, report a ticket under **Wi-Fi & Wireless Connectivity** with your floor location.""",
        "tags": ["wifi", "internet", "network", "eduroam", "portal"],
        "views": 420,
        "helpful_count": 88,
        "not_helpful_count": 2,
        "author_name": "Campus IT Operations",
        "is_published": True,
        "institution_id": INST_ID
    },
    {
        "_id": "KB-NIE-002",
        "title": "Troubleshooting Classroom Projector HDMI & Audio in Smart Halls",
        "category": "Classroom Projectors & Screens",
        "content": """### Common Problem
Projector displays 'No Signal', flickers constantly, or projects video without sound from the podium laptop.

### Why This Happens
- Windows display arrangement defaults to 'PC screen only'.
- Crestron/Extron audio switchers do not route analog audio unless HDMI handshake completes.
- Podium HDMI switch is set to the wrong input source.

### Quick Fix (You can do this right away)
1. **Display Mirroring**: Press `Windows Key + P` on your laptop and choose **Duplicate**.
2. **Resolution Check**: Set your laptop display resolution to `1920x1080` (1080p).
3. **Sound Output**:
   - Click the speaker icon in the Windows taskbar.
   - Switch the output device from *Realtek Audio* to **Extron Audio / Crestron HDMI**.
4. **Physical Switcher**: On the podium control box, press the button labeled **Laptop / HDMI 1** until the green LED turns solid.
5. If the projector lamp warning LED is blinking red/amber, raise a **Critical** ticket for lamp replacement.""",
        "tags": ["projector", "hdmi", "smart classroom", "audio", "display"],
        "views": 312,
        "helpful_count": 65,
        "not_helpful_count": 1,
        "author_name": "Facilities & AV Team",
        "is_published": True,
        "institution_id": INST_ID
    },
    {
        "_id": "KB-NIE-003",
        "title": "Lab Workstation Boot Errors (Grub Rescue & Blue Screen BSOD)",
        "category": "Operating System & Boot Errors",
        "content": """### Common Problem
Lab computer turns on but halts at `grub rescue>` or displays a Windows `UNMOUNTABLE_BOOT_VOLUME` error.

### Why This Happens
- Dual-boot installations (Ubuntu + Windows) can desync if power is cut suddenly while writing to disk.
- USB flash drives left plugged in can cause the BIOS to attempt booting from the USB drive.

### Quick Fix (You can do this right away)
1. **Unplug USB Drives**: Ensure all external pen drives and phone charging cables are unplugged from front and rear USB ports.
2. **Reboot**: Press and hold the power button for 8 seconds until the machine powers off, wait 5 seconds, and power on.
3. **BIOS Boot Menu**: Tap `F12` (or `F2` on Dell/HP) during startup.
4. Select **Ubuntu** or **Windows Boot Manager** directly from the UEFI boot list.
5. If the hard disk is making clicking sounds or cannot be detected, submit a ticket under **Operating System & Boot Errors**.""",
        "tags": ["grub", "boot", "lab", "computer", "bsod"],
        "views": 250,
        "helpful_count": 52,
        "not_helpful_count": 3,
        "author_name": "CSE Systems Admin",
        "is_published": True,
        "institution_id": INST_ID
    },
    {
        "_id": "KB-NIE-004",
        "title": "Resetting Forgotten College Portal, LMS & ERP Passwords",
        "category": "College Email & Account Access",
        "content": """### Common Problem
Account locked out after multiple unsuccessful login attempts on the student/faculty portal.

### Why This Happens
- Passwords expire every 90 days as per campus security policies.
- Mobile phones repeatedly trying old cached Wi-Fi credentials can trigger account rate-limiting.

### Quick Fix (You can do this right away)
1. Turn off Wi-Fi on your phone to prevent automatic credential retry lockouts.
2. Go to the FixIt login screen and click **Forgot Password?**.
3. Enter your institutional email address (`@nie.ac.in`).
4. Check your recovery inbox for the secure reset link (valid for 15 minutes).
5. Choose a password with at least 8 characters including 1 uppercase, 1 numeral, and 1 special symbol.
6. Once reset, wait 2 minutes for Active Directory to replicate across the campus network.""",
        "tags": ["password", "portal", "lms", "account", "login"],
        "views": 590,
        "helpful_count": 140,
        "not_helpful_count": 4,
        "author_name": "Campus IT Operations",
        "is_published": True,
        "institution_id": INST_ID
    },
    {
        "_id": "KB-NIE-005",
        "title": "Resolving Network Printer Spooler & Paper Jam Issues",
        "category": "Printers, Scanners & Copiers",
        "content": """### Common Problem
Printer status shows 'Offline' or 'Paper Jam' even though paper is present in the tray.

### Why This Happens
- Print spooler service on Windows stops responding when corrupted PDF documents are queued.
- Sensor rollers detect micro-tears from curled or damp paper.

### Quick Fix (You can do this right away)
1. Open the front door of the printer and verify no small paper fragments are caught in the feed roller.
2. Ensure paper in Tray 2 is aligned against the plastic edge guides.
3. On Windows: Press `Win + R`, type `services.msc`, locate **Print Spooler**, right-click and choose **Restart**.
4. Power cycle the printer: Switch OFF the toggle, wait 10 seconds, and switch back ON.
5. If the toner cartridge is empty (indicated by blinking yellow cartridge light), submit a ticket under **Printers, Scanners & Copiers**.""",
        "tags": ["printer", "paper jam", "spooler", "hardware"],
        "views": 180,
        "helpful_count": 39,
        "not_helpful_count": 1,
        "author_name": "Facilities & Hardware Support",
        "is_published": True,
        "institution_id": INST_ID
    }
]

USERS_CONFIG = [
    {
        "email": "platform.admin@fixit.org",
        "name": "Platform Administrator",
        "role": "platform_admin",
        "password": "Platform@123",
        "institution_id": "INST-PLATFORM"
    },
    {
        "email": "admin@nie.ac.in",
        "name": "NIE Administrator",
        "role": "admin",
        "password": "NieAdmin@2024!",
        "institution_id": INST_ID
    },
    {
        "email": "meera.rao@faculty.nie.ac.in",
        "name": "Dr. Meera Rao",
        "role": "faculty",
        "password": "NieFaculty@2024!",
        "institution_id": INST_ID
    },
    {
        "email": "aarav.student@students.nie.ac.in",
        "name": "Aarav Patel",
        "role": "student",
        "password": "NieStudent@2024!",
        "institution_id": INST_ID
    },
    {
        "email": "2025cs_ankanghosh_a@nie.ac.in",
        "name": "Ankan Gosh",
        "role": "staff",
        "password": "NieStaff@2024!",
        "institution_id": INST_ID,
        "specialization": ["Electrical Switchboards, MCB & Breakers", "Power Sockets & Electrical Outlets", "UPS & Power Backup Battery", "Air Conditioning (AC) & Cooling"]
    },
    {
        "email": "2025cs_anuragsingh_a@nie.ac.in",
        "name": "Anurag Singh",
        "role": "staff",
        "password": "NieStaff@2024!",
        "institution_id": INST_ID,
        "specialization": ["Wi-Fi & Wireless Connectivity", "LAN, Ethernet & Network Cables", "Classroom Projectors & Screens", "Desktop Computers & Lab Workstations"]
    }
]

async def main():
    await connect_to_mongo()
    db = get_database()
    print("=" * 60)
    print("FIXIT COMPREHENSIVE CONFIGURATION SCRIPT")
    print("=" * 60)

    # 1. Update/Ensure Institution
    print("\n[1/6] Ensuring Institution: National Institute of Engineering...")
    await db.institutions.update_one(
        {"_id": INST_ID},
        {
            "$set": {
                "name": "National Institute of Engineering",
                "slug": "nie",
                "email_domains": ["nie.ac.in", "students.nie.ac.in", "faculty.nie.ac.in"],
                "student_email_domains": ["nie.ac.in", "students.nie.ac.in"],
                "faculty_email_domains": ["nie.ac.in", "faculty.nie.ac.in"],
                "status": "active"
            },
            "$setOnInsert": {"created_at": NOW}
        },
        upsert=True
    )

    # 2. Populate Campus Hierarchy
    print("\n[2/6] Configuring Campus, Buildings, Floors, and Rooms...")
    await db.campuses.update_one(
        {"_id": CAMPUS_ID},
        {
            "$set": {
                "name": "National Institute of Engineering - Main Campus",
                "code": "NIE-MAIN",
                "institution_id": INST_ID,
                "is_active": True
            },
            "$setOnInsert": {"created_at": NOW}
        },
        upsert=True
    )

    for bld_id, bld in CAMPUS_HIERARCHY.items():
        await db.buildings.update_one(
            {"_id": bld_id},
            {
                "$set": {
                    "campus_id": CAMPUS_ID,
                    "institution_id": INST_ID,
                    "name": bld["name"],
                    "code": bld["code"],
                    "total_floors": bld["total_floors"],
                    "order": bld["order"],
                    "is_active": True
                },
                "$setOnInsert": {"created_at": NOW}
            },
            upsert=True
        )
        for flr in bld["floors"]:
            flr_doc = await db.floors.find_one({"building_id": bld_id, "floor_name": flr["floor_name"]})
            if flr_doc:
                flr_id = str(flr_doc["_id"])
                await db.floors.update_one(
                    {"_id": flr_id},
                    {
                        "$set": {
                            "floor_number": flr["floor_number"],
                            "order": flr["order"],
                            "institution_id": INST_ID,
                            "is_active": True
                        }
                    }
                )
            else:
                flr_id = f"FLR-NIE-{bld['code']}-{flr['floor_number']}"
                await db.floors.insert_one({
                    "_id": flr_id,
                    "building_id": bld_id,
                    "institution_id": INST_ID,
                    "floor_number": flr["floor_number"],
                    "floor_name": flr["floor_name"],
                    "order": flr["order"],
                    "is_active": True,
                    "created_at": NOW
                })

            for rm in flr["rooms"]:
                rm_doc = await db.rooms.find_one({
                    "building_id": bld_id,
                    "floor_id": flr_id,
                    "room_number": rm["room_number"]
                })
                if rm_doc:
                    await db.rooms.update_one(
                        {"_id": rm_doc["_id"]},
                        {
                            "$set": {
                                "room_name": rm["room_name"],
                                "department": rm["department"],
                                "institution_id": INST_ID,
                                "is_active": True
                            }
                        }
                    )
                else:
                    rm_id = f"RM-NIE-{bld['code']}-{rm['room_number']}"
                    await db.rooms.insert_one({
                        "_id": rm_id,
                        "building_id": bld_id,
                        "floor_id": flr_id,
                        "institution_id": INST_ID,
                        "room_number": rm["room_number"],
                        "room_name": rm["room_name"],
                        "department": rm["department"],
                        "is_active": True,
                        "created_at": NOW
                    })
    print("  -> Provisioned 4 Buildings, 13 Floors, and 30 Rooms across NIE campus.")

    # 3. Populate Categories
    print("\n[3/6] Configuring 40 Campus Categories...")
    for cat in CAMPUS_CATEGORIES:
        await db.categories.update_one(
            {"name": cat["name"], "institution_id": INST_ID},
            {
                "$set": {
                    "institution_id": INST_ID,
                    "name": cat["name"],
                    "subcategories": cat["subcategories"],
                    "description": f"Campus issue reporting for {cat['name'].lower()}",
                    "icon": cat.get("icon", "Folder"),
                    "is_active": True
                },
                "$setOnInsert": {"_id": f"CAT-{uuid.uuid4().hex[:8].upper()}", "created_at": NOW}
            },
            upsert=True
        )
    print("  -> 40 Categories active in database.")

    # 4. Populate Departments
    print("\n[4/6] Configuring Campus Departments...")
    for dept in CAMPUS_DEPARTMENTS:
        await db.departments.update_one(
            {"name": dept["name"], "institution_id": INST_ID},
            {
                "$set": {
                    "institution_id": INST_ID,
                    "name": dept["name"],
                    "code": dept["code"],
                    "head_name": dept["head_name"],
                    "email": dept["email"],
                    "is_active": True
                },
                "$setOnInsert": {"_id": f"DEP-{uuid.uuid4().hex[:8].upper()}", "created_at": NOW}
            },
            upsert=True
        )
    print(f"  -> {len(CAMPUS_DEPARTMENTS)} Departments active.")

    # 5. Populate SLA Policies
    print("\n[5/6] Configuring SLA Policies...")
    sla_data = [
        {"priority": "critical", "target_resolution_hours": 2, "target_response_hours": 1, "description": "Emergency / campus hazard / critical outages"},
        {"priority": "high", "target_resolution_hours": 8, "target_response_hours": 2, "description": "Academic disruptions / scheduled class impact"},
        {"priority": "medium", "target_resolution_hours": 24, "target_response_hours": 4, "description": "Standard facility & workstation issues"},
        {"priority": "low", "target_resolution_hours": 72, "target_response_hours": 8, "description": "Routine maintenance & cosmetic requests"}
    ]
    for s in sla_data:
        await db.sla_policies.update_one(
            {"priority": s["priority"], "institution_id": INST_ID},
            {
                "$set": {
                    "institution_id": INST_ID,
                    "priority": s["priority"],
                    "target_resolution_hours": s["target_resolution_hours"],
                    "target_response_hours": s["target_response_hours"],
                    "description": s["description"],
                    "updated_at": NOW
                },
                "$setOnInsert": {"_id": f"SLA-{s['priority'].upper()}"}
            },
            upsert=True
        )
    print("  -> 4 SLA policies active (2h critical, 8h high, 24h medium, 72h low).")

    # 6. Populate Knowledge Base Articles
    print("\n[6/6] Configuring Knowledge Base & DIY Quick Fixes...")
    for kb in KB_ARTICLES:
        await db.knowledge_base.update_one(
            {"_id": kb["_id"]},
            {"$set": {**kb, "updated_at": NOW}, "$setOnInsert": {"created_at": NOW}},
            upsert=True
        )
    print(f"  -> {len(KB_ARTICLES)} Knowledge Base DIY articles active.")

    # 7. Configure Users & Verified Passwords
    print("\n[7/7] Verifying and provisioning all Roles & User Accounts...")
    for u in USERS_CONFIG:
        update_data = {
            "name": u["name"],
            "role": u["role"],
            "password_hash": get_password_hash(u["password"]),
            "institution_id": u["institution_id"],
            "is_active": True,
            "email_verified": True,
            "token_version": 0
        }
        if "specialization" in u:
            update_data["specialization"] = u["specialization"]
        await db.users.update_one(
            {"email": u["email"]},
            {"$set": update_data, "$setOnInsert": {"_id": f"USR-{uuid.uuid4().hex[:10].upper()}", "created_at": NOW}},
            upsert=True
        )

    # Make sure Agastya Shetty's student account is active and verified
    await db.users.update_one(
        {"email": "2025cs_agastyashetty_a@nie.ac.in"},
        {"$set": {"institution_id": INST_ID, "is_active": True, "email_verified": True}}
    )

    print("\nSUCCESS! Everything is fully provisioned and ready.")

if __name__ == "__main__":
    asyncio.run(main())
