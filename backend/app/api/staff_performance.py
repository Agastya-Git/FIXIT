from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.core.security import get_current_user, require_roles
from app.core.database import get_database
from app.core.tenancy import institution_id_for, scoped_filter
from app.services.warning_service import (
    get_staff_accountability_summary,
    pardon_warning,
    check_sla_breaches_and_issue_warnings,
    WARNING_ROLLING_WINDOW_DAYS
)
from app.services.assignment_service import get_staff_workload, STAFF_CAPACITY_LIMIT

router = APIRouter(prefix="/staff-performance", tags=["Staff Performance & Accountability"])


class PardonRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500, description="Administrative justification for pardoning warning")


@router.get("/my-warnings")
async def get_my_warnings(current_user: dict = Depends(get_current_user)):
    """Retrieve accountability summary and active warnings for the authenticated staff user."""
    if current_user.get("role") not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Only staff members and administrators can access accountability metrics.")

    summary = await get_staff_accountability_summary(
        staff_id=current_user["id"],
        institution_id=institution_id_for(current_user)
    )
    return summary


@router.get("/overview")
async def get_staff_performance_overview(current_user: dict = Depends(require_roles("admin"))):
    """Administrator overview of all staff members: capacity, warnings, strikes, SLA compliance."""
    db = get_database()
    inst_id = institution_id_for(current_user)
    
    staff_query = {"role": "staff"}
    if inst_id:
        staff_query["institution_id"] = inst_id

    staff_members = await db.users.find(staff_query).to_list(100)
    summaries = []

    for staff in staff_members:
        summary = await get_staff_accountability_summary(
            staff_id=str(staff["_id"]),
            institution_id=inst_id
        )
        summaries.append(summary)

    # Sort so that staff flagged with review_required or higher strikes appear at the top
    summaries.sort(
        key=lambda s: (s.get("review_required", False), s.get("strikes_count", 0), s.get("warnings_30d_count", 0)),
        reverse=True
    )

    return {
        "staff_count": len(summaries),
        "capacity_limit": STAFF_CAPACITY_LIMIT,
        "rolling_window_days": WARNING_ROLLING_WINDOW_DAYS,
        "staff": summaries
    }


@router.post("/warnings/{warning_id}/pardon")
async def pardon_staff_warning(
    warning_id: str,
    payload: PardonRequest,
    current_user: dict = Depends(require_roles("admin"))
):
    """Administrator pardons an SLA breach warning ticket."""
    try:
        updated = await pardon_warning(
            warning_id=warning_id,
            admin_id=current_user["id"],
            admin_name=current_user.get("name", "Administrator"),
            reason=payload.reason
        )
        return {"status": "success", "message": "Warning successfully pardoned", "warning": updated}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pardon warning: {e}")


@router.post("/check-sla")
async def trigger_sla_check(current_user: dict = Depends(require_roles("admin"))):
    """Trigger manual SLA breach evaluation and warning issuance."""
    warnings_issued = await check_sla_breaches_and_issue_warnings()
    return {
        "status": "success",
        "warnings_issued_count": len(warnings_issued),
        "warnings": warnings_issued
    }
