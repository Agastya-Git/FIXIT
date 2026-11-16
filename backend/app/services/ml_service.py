"""
ML Service for FixIt — Priority Classifier and Field Classifier.

Uses scikit-learn Random Forest + TF-IDF when enough training data exists,
falls back to keyword-based heuristics when data is insufficient.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional scikit-learn import (graceful degradation if not installed)
# ---------------------------------------------------------------------------
try:
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import RandomForestClassifier
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed — ML service will use heuristic fallback only.")

# ---------------------------------------------------------------------------
# Global model state
# ---------------------------------------------------------------------------
_priority_model: Optional[object] = None   # sklearn Pipeline or None
_field_model: Optional[object] = None      # sklearn Pipeline or None
_models_trained: bool = False


# ---------------------------------------------------------------------------
# Heuristic helpers
# ---------------------------------------------------------------------------

def _lower(text: str) -> str:
    return text.lower() if text else ""


def _contains(text: str, keywords: list) -> bool:
    t = _lower(text)
    return any(kw in t for kw in keywords)


_PRIORITY_RULES = [
    ("critical", ["fire", "flood", "emergency", "server down", "complete outage", "power failure",
                  "total blackout", "building evacuation", "life threatening"]),
    ("high",     ["not working", "broken", "failed", "failure", "down", "cannot access",
                  "no access", "doesn't work", "doesn't start", "won't start"]),
    ("low",      ["request", "suggestion", "minor", "cosmetic", "enhancement", "would be nice",
                  "nice to have", "low priority"]),
    # medium is the default
]

_CATEGORY_RULES = [
    ("Wi-Fi & Wireless Connectivity",             ["wifi", "wi-fi", "wireless", "hotspot", "signal", "bandwidth"]),
    ("LAN, Ethernet & Network Cables",            ["lan", "ethernet", "network cable", "rj45", "patch cord"]),
    ("Network Switches, Routers & Firewalls",     ["router", "switch", "firewall", "gateway", "access point", "dns"]),
    ("Classroom Projectors & Screens",            ["projector", "projection screen", "hdmi", "vga", "display unit"]),
    ("Interactive Smart Boards & Digital Displays", ["smart board", "smartboard", "digital podium", "touch display"]),
    ("Audio Systems, Microphones & Speakers",     ["audio", "speaker", "microphone", "mic", "sound system", "amplifier"]),
    ("Desktop Computers & Lab Workstations",      ["desktop", "computer", "pc", "workstation", "cpu", "ram", "hard disk", "ssd"]),
    ("Monitors, Screens & Displays",              ["monitor", "screen", "flickering display", "black screen"]),
    ("Keyboards, Mice & Input Peripherals",       ["keyboard", "mouse", "webcam", "usb"]),
    ("Power Sockets & Electrical Outlets",        ["socket", "power socket", "plug", "extension box", "electrical outlet"]),
    ("Air Conditioning (AC) & Cooling",           ["ac", "air conditioner", "cooling", "ac remote", "cooling fan"]),
    ("Ceiling Fans & Regulators",                 ["fan", "ceiling fan", "regulator"]),
    ("Lighting, Tube Lights & Bulbs",             ["light", "tube light", "bulb", "flickering light", "lighting"]),
    ("Electrical Switchboards, MCB & Breakers",   ["switchboard", "mcb", "circuit breaker", "tripped breaker", "sparking"]),
    ("UPS & Power Backup Battery",                ["ups", "inverter", "backup battery", "power backup"]),
    ("Operating System & Boot Errors",            ["boot", "bios", "windows crash", "blue screen", "bsod", "os not found"]),
    ("Software Installation & Applications",      ["software", "app", "application", "install", "installation", "setup"]),
    ("Compiler, IDE & Development Tools",         ["python", "matlab", "visual studio", "vscode", "compiler", "gcc", "java", "eclipse"]),
    ("Campus ERP, Student Portal & Marks Entry",  ["portal", "erp", "login issue", "marks entry", "attendance portal", "lms"]),
    ("Printers, Scanners & Copiers",              ["printer", "scanner", "photocopier", "cartridge", "paper jam"]),
    ("Drinking Water Coolers & Purifiers",        ["water cooler", "drinking water", "purifier", "water tap", "water dispenser"]),
    ("Restrooms, Plumbing & Sanitation",          ["restroom", "washroom", "plumbing", "toilet", "drainage", "leakage"]),
    ("Student Benches, Desks & Classroom Seating", ["bench", "desk", "classroom chair", "student chair", "broken desk"]),
    ("Faculty Desks, Chairs & Office Furniture",  ["faculty chair", "office desk", "table", "cupboard", "bookshelf"]),
    ("Doors, Windows, Glass & Locks",             ["door", "window", "glass pane", "door lock", "latch", "handle"]),
    ("Elevators, Lifts & Accessibility",          ["elevator", "lift", "ramp"]),
    ("CCTV Cameras & Campus Surveillance",        ["cctv", "camera", "surveillance", "security camera"]),
    ("General Campus Facilities & Maintenance",   ["cleaning", "garbage", "waste", "infrastructure", "corridor", "hallway"]),
]

_DOMAIN_RULES = [
    ("technical",   ["wifi", "internet", "network", "computer", "laptop", "software",
                     "app", "hardware", "server", "database", "code", "programming",
                     "bug", "crash", "monitor", "cpu", "ram"]),
    ("facilities",  ["power", "electricity", "lights", "fan", "ac", "projector",
                     "chair", "table", "door", "window", "ceiling", "bathroom",
                     "elevator", "parking", "infrastructure"]),
    ("academic",    ["exam", "assignment", "course", "faculty", "lecture", "marks",
                     "grade", "syllabus", "curriculum", "timetable", "hall ticket",
                     "result", "attendance"]),
]


def _heuristic_priority(title: str, description: str, affected_users: int, category: str) -> str:
    combined = f"{title} {description} {category}"
    if affected_users >= 50 or _contains(combined, _PRIORITY_RULES[0][1]):
        return "critical"
    if affected_users >= 10 or _contains(combined, _PRIORITY_RULES[1][1]):
        return "high"
    if _contains(combined, _PRIORITY_RULES[2][1]):
        return "low"
    if _contains(combined, ["slow", "intermittent", "sometimes", "occasional"]):
        return "medium"
    return "medium"


def _heuristic_category(title: str, description: str) -> str:
    combined = f"{title} {description}"
    for cat, keywords in _CATEGORY_RULES:
        if _contains(combined, keywords):
            return cat
    return "General IT Support"


def _heuristic_domain(title: str, description: str) -> str:
    combined = f"{title} {description}"
    for domain, keywords in _DOMAIN_RULES:
        if _contains(combined, keywords):
            return domain
    return "technical"


# ---------------------------------------------------------------------------
# Public scoring helper (used by the public endpoint)
# ---------------------------------------------------------------------------

def priority_score(priority: str) -> int:
    """Return a numeric score for sorting (higher = more urgent)."""
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(priority, 2)


def compute_priority_score(priority: str, upvotes_count: int = 0, affected_users: int = 1) -> float:
    """Return a composite numeric score combining priority, upvotes, and scale."""
    base_scores = {"critical": 100.0, "high": 70.0, "medium": 40.0, "low": 10.0}
    base = base_scores.get(str(priority).lower(), 40.0)
    upvote_pts = min(float(upvotes_count) * 5.0, 100.0)
    users_pts = min(float(affected_users) * 0.5, 20.0)
    return base + upvote_pts + users_pts


# ---------------------------------------------------------------------------
# scikit-learn training
# ---------------------------------------------------------------------------

def _build_priority_features(tickets: list) -> tuple:
    """Build (X_text, y) for the priority model."""
    X, y = [], []
    for t in tickets:
        combined = f"{t.get('title', '')} {t.get('description', '')} {t.get('category', '')}"
        X.append(combined)
        y.append(t.get("priority", "medium"))
    return X, y


def _build_field_features(tickets: list) -> tuple:
    """Build (X_text, y_category) for the field model."""
    X, y = [], []
    for t in tickets:
        combined = f"{t.get('title', '')} {t.get('description', '')}"
        X.append(combined)
        y.append(t.get("category", "General IT Support"))
    return X, y


def train_models(tickets_list: list) -> None:
    """Train both ML models from a list of ticket dicts.

    Each dict should have: title, description, affected_users, category, priority.
    Requires at least 10 samples per class to be meaningful.
    Falls back silently if scikit-learn is not available.
    """
    global _priority_model, _field_model, _models_trained

    if not _SKLEARN_AVAILABLE:
        logger.warning("train_models called but scikit-learn is not available.")
        return

    if len(tickets_list) < 20:
        logger.info("Not enough tickets to train ML models (%d). Using heuristics.", len(tickets_list))
        return

    try:
        # --- Priority model ---
        X_p, y_p = _build_priority_features(tickets_list)
        priority_pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=5000, sublinear_tf=True)),
            ("clf",   RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                             random_state=42, n_jobs=-1)),
        ])
        priority_pipeline.fit(X_p, y_p)
        _priority_model = priority_pipeline

        # --- Field (category) model ---
        X_f, y_f = _build_field_features(tickets_list)
        field_pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=5000, sublinear_tf=True)),
            ("clf",   RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                             random_state=42, n_jobs=-1)),
        ])
        field_pipeline.fit(X_f, y_f)
        _field_model = field_pipeline

        _models_trained = True
        logger.info("ML models trained successfully on %d tickets.", len(tickets_list))

    except Exception as exc:
        logger.error("ML model training failed: %s", exc)
        _models_trained = False


# ---------------------------------------------------------------------------
# Async trainer from DB (called at startup)
# ---------------------------------------------------------------------------

async def train_models_from_db() -> None:
    """Train ML models from existing tickets in DB.

    Falls back to heuristics if insufficient data.
    """
    from app.core.database import get_database
    db = get_database()
    tickets = await db.tickets.find({"priority": {"$exists": True}}).to_list(1000)
    if len(tickets) < 20:
        logger.info("Insufficient training data (%d tickets), using heuristic fallback", len(tickets))
        return
    train_models([{
        "title": t.get("title", ""),
        "description": t.get("description", ""),
        "affected_users": t.get("affected_users", 1),
        "category": t.get("category", ""),
        "priority": t.get("priority", "medium"),
    } for t in tickets])


# ---------------------------------------------------------------------------
# Public classification API
# ---------------------------------------------------------------------------

def classify_priority(title: str, description: str, affected_users: int = 1, category: str = "") -> str:
    """Predict ticket priority (critical/high/medium/low).

    Uses trained ML model when available, heuristics otherwise.
    """
    if _models_trained and _priority_model is not None:
        try:
            combined = f"{title} {description} {category}"
            prediction = _priority_model.predict([combined])[0]
            return str(prediction)
        except Exception as exc:
            logger.warning("Priority model prediction failed: %s — falling back to heuristics", exc)

    return _heuristic_priority(title, description, affected_users, category)


def predict_fields(title: str, description: str) -> dict:
    """Predict ticket fields: category and problem_domain.

    Returns a dict with 'category', 'problem_domain', and optionally 'subcategory'.
    Uses trained ML model when available, heuristics otherwise.
    """
    if _models_trained and _field_model is not None:
        try:
            combined = f"{title} {description}"
            category_pred = _field_model.predict([combined])[0]
            domain = _heuristic_domain(title, description)
            return {"category": str(category_pred), "problem_domain": domain, "subcategory": None}
        except Exception as exc:
            logger.warning("Field model prediction failed: %s — falling back to heuristics", exc)

    category = _heuristic_category(title, description)
    domain = _heuristic_domain(title, description)
    return {"category": category, "problem_domain": domain, "subcategory": None}
