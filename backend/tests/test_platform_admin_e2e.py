"""
End-to-end integration test for the Platform Administrator workflow.

Covers:
  1. Platform Admin login via /api/auth/login — verifies JSON response shape
  2. Create institution (using platform_admin JWT in Authorization header)
  3. Invite College Admin — dev mode (no SMTP required), verifies token returned
  4. Accept invitation (set password)
  5. College Admin login

Run from backend/ with:
    python -m pytest tests/test_platform_admin_e2e.py -v

Design notes:
  - We use direct JWT minting (create_access_token) rather than cookie-based
    login for tests 2-3 to avoid cookie persistence issues across test methods.
  - The institution + platform admin are seeded ONCE at module level and
    persisted via upsert so the per-test `ensure_db_seeded` conftest fixture
    (which only adds/migrates records, not drops them) doesn't wipe them.
  - The invite endpoint validates email domain against institution.email_domains,
    so we seed an institution that accepts the COLLEGE_EMAIL domain.
  - The invite endpoint returns {token, invitation_url} in dev mode (no SMTP).
  - The accept + login tests depend on the invited user's hashed password being
    stored in the DB after acceptance.
"""
import uuid
import pytest
from app.core.database import db_manager
from app.core.security import get_password_hash, create_access_token

SUFFIX = uuid.uuid4().hex[:8]
PLATFORM_EMAIL = f"e2e.platform.{SUFFIX}@fixit.example.com"
PLATFORM_PASS = "PlatformAdmin@2024!"

# College admin email — domain MUST match institution email_domains below
COLLEGE_DOMAIN = f"e2e-college-{SUFFIX}.edu"
COLLEGE_EMAIL = f"college.admin@{COLLEGE_DOMAIN}"
COLLEGE_PASS = "CollegeAdmin@2024!"

INST_ID = f"INST-E2E-{SUFFIX.upper()}"
ADMIN_ID = f"USR-E2E-{SUFFIX.upper()}"

HEADERS = {"Origin": "http://localhost:5175"}

# Shared state across the sequential tests
_state: dict = {}


def _sync_db():
    """Return the underlying synchronous mongomock database."""
    return db_manager.db.sync_db


def _do_seed():
    """Seed the platform institution + platform admin user."""
    sync_db = _sync_db()

    # Ensure INST-PLATFORM exists (created by app lifespan, but mock skips that)
    sync_db.institutions.replace_one(
        {"_id": "INST-PLATFORM"},
        {
            "_id": "INST-PLATFORM",
            "name": "FixIt Platform Operations",
            "slug": "platform",
            "email_domains": [],
            "status": "active",
        },
        upsert=True,
    )

    # Create a fresh institution for this test run
    sync_db.institutions.replace_one(
        {"_id": INST_ID},
        {
            "_id": INST_ID,
            "name": f"E2E College {SUFFIX}",
            "slug": f"e2e-college-{SUFFIX}",
            "email_domains": [COLLEGE_DOMAIN],
            "student_email_domains": [f"students.{COLLEGE_DOMAIN}"],
            "faculty_email_domains": [f"faculty.{COLLEGE_DOMAIN}"],
            "status": "active",
            "created_at": "2024-01-01T00:00:00+00:00",
        },
        upsert=True,
    )

    # Create the platform admin user
    sync_db.users.replace_one(
        {"_id": ADMIN_ID},
        {
            "_id": ADMIN_ID,
            "email": PLATFORM_EMAIL,
            "name": "E2E Platform Admin",
            "role": "platform_admin",
            "admin_level": "platform",
            "institution_id": "INST-PLATFORM",
            "password_hash": get_password_hash(PLATFORM_PASS),
            "is_active": True,
            "account_status": "active",
            "token_version": 0,
            "created_at": "2024-01-01T00:00:00+00:00",
        },
        upsert=True,
    )

    # Pre-mint JWT (avoids cookie-persistence complexity in tests)
    _state["platform_token"] = create_access_token(
        {"sub": ADMIN_ID, "role": "platform_admin", "ver": 0}
    )
    _state["inst_id"] = INST_ID


@pytest.fixture(scope="module", autouse=True)
def seed_e2e_data():
    _do_seed()


def _auth(token: str) -> dict:
    return {**HEADERS, "Authorization": f"Bearer {token}"}


class TestPlatformAdminE2E:
    """
    Full Platform Admin → College Admin workflow.
    Tests run in declaration order and share state via the _state dict.
    """

    # ── Test 1: Login ────────────────────────────────────────────────────────
    def test_1_platform_admin_login(self, client):
        """
        Platform Admin should log in via /api/auth/login.
        The JSON response should contain a Token with nested user.role.
        """
        # Re-seed in case ensure_db_seeded ran and re-inserted defaults
        _do_seed()

        r = client.post(
            "/api/auth/login",
            json={"email": PLATFORM_EMAIL, "password": PLATFORM_PASS},
            headers=HEADERS,
        )
        assert r.status_code == 200, f"Platform admin login failed (HTTP {r.status_code}): {r.text}"
        data = r.json()
        assert "user" in data, f"Response missing 'user' key. Got: {list(data.keys())}"
        user = data["user"]
        assert user["role"] == "platform_admin", f"Expected role=platform_admin, got {user['role']}"
        assert user.get("admin_level") == "platform", f"Expected admin_level=platform, got {user.get('admin_level')}"
        assert "access_token" in data, f"Response missing 'access_token'"

    # ── Test 2: Create Institution ───────────────────────────────────────────
    def test_2_institution_already_seeded(self, client):
        """
        The institution should already exist in DB (seeded at module level).
        Verify it's retrievable by the platform admin.
        """
        token = _state["platform_token"]
        r = client.get(
            "/api/institutions/manage",
            headers=_auth(token),
        )
        assert r.status_code == 200, f"List institutions failed: {r.text}"
        ids = [i["id"] for i in r.json()]
        assert INST_ID in ids, f"E2E institution {INST_ID} not in list: {ids}"

    # ── Test 3: Invite College Admin (no SMTP) ───────────────────────────────
    def test_3_invite_college_admin_no_smtp(self, client):
        """
        Platform Admin invites a College Admin.
        In dev mode (no SMTP config), the backend must:
          - return HTTP 202
          - include 'token' and 'invitation_url' in the response body
        """
        token = _state["platform_token"]
        r = client.post(
            f"/api/institutions/{INST_ID}/admins/invitations",
            json={"email": COLLEGE_EMAIL, "name": "E2E College Admin"},
            headers=_auth(token),
        )
        assert r.status_code == 202, f"Invite failed (HTTP {r.status_code}): {r.text}"
        body = r.json()
        assert "token" in body, (
            f"Dev-mode: response must include 'token' so local devs can test "
            f"without email. Got keys: {list(body.keys())}"
        )
        assert "invitation_url" in body, (
            f"Dev-mode: response must include 'invitation_url'. Got: {list(body.keys())}"
        )
        _state["invite_token"] = body["token"]

    # ── Test 4: Accept Invitation ────────────────────────────────────────────
    def test_4_accept_invitation(self, client):
        """College Admin accepts the invitation and sets their password."""
        invite_token = _state.get("invite_token")
        assert invite_token, "invite_token not set — test_3 must pass first"

        r = client.post(
            "/api/institutions/admin-invitations/accept",
            json={"token": invite_token, "password": COLLEGE_PASS},
            headers=HEADERS,
        )
        assert r.status_code == 201, f"Accept invitation failed (HTTP {r.status_code}): {r.text}"

    # ── Test 5: College Admin Login ──────────────────────────────────────────
    def test_5_college_admin_login(self, client):
        """College Admin should be able to log in after accepting the invitation."""
        r = client.post(
            "/api/auth/login",
            json={"email": COLLEGE_EMAIL, "password": COLLEGE_PASS},
            headers=HEADERS,
        )
        assert r.status_code == 200, f"College admin login failed (HTTP {r.status_code}): {r.text}"
        data = r.json()
        user = data.get("user", {})
        assert user.get("role") == "admin", f"Expected role=admin, got {user.get('role')}"
        assert user.get("institution_id") == INST_ID, (
            f"Expected institution_id={INST_ID}, got {user.get('institution_id')}"
        )
        assert "access_token" in data, "access_token missing from response"
