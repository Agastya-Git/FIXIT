from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, db_manager

# Import all API routers
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.tickets import router as tickets_router
from app.api.assignments import router as assignments_router
from app.api.comments import router as comments_router
from app.api.uploads import router as uploads_router
from app.api.notifications import router as notifications_router
from app.api.categories import router as categories_router
from app.api.campus import router as campus_router
from app.api.sla import router as sla_router
from app.api.knowledge_base import router as kb_router
from app.api.feedback import router as feedback_router
from app.api.analytics import router as analytics_router
from app.api.reports import router as reports_router
from app.api.audit_logs import router as audit_logs_router
from app.api.incidents import router as incidents_router
from app.api.feature_requests import router as feature_requests_router
from app.api.institutions import router as institutions_router
from app.api.registration import router as registration_router
from app.api.admin_governance import router as admin_governance_router
from app.api.staff_performance import router as staff_performance_router
import asyncio
import logging

logger = logging.getLogger(__name__)

async def sla_breach_monitor_loop():
    """Periodic background runner checking SLA breach warnings every 15 minutes."""
    from app.services.warning_service import check_sla_breaches_and_issue_warnings
    while True:
        try:
            await check_sla_breaches_and_issue_warnings()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Error in background SLA breach monitor: {e}")
        try:
            await asyncio.sleep(900)  # 15 minutes
        except asyncio.CancelledError:
            break

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to DB
    await connect_to_mongo()
    # Preserve all existing single-college records under a dedicated default tenant.
    # Missing tenant IDs are migrated once; subsequent startup runs are idempotent.
    db = db_manager.db
    await db.institutions.update_one(
        {"_id": "INST-DEFAULT"},
        {"$setOnInsert": {"name": "Default Institution", "slug": "default", "status": "active", "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}},
        upsert=True,
    )
    await db.institutions.update_one(
        {"_id": "INST-PLATFORM"},
        {"$setOnInsert": {"name": "FixIt Platform Operations", "slug": "platform", "status": "active", "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}},
        upsert=True,
    )
    for collection_name in ("users", "tickets", "campuses", "buildings", "floors", "rooms", "blocks", "campus_locations", "incidents", "knowledge_base", "categories", "departments", "sla_policies"):
        await db[collection_name].update_many({"institution_id": {"$exists": False}}, {"$set": {"institution_id": "INST-DEFAULT"}})

    # If database is fresh/empty, automatically populate from backend/seeds
    user_count = await db.users.count_documents({})
    if user_count == 0:
        from pathlib import Path
        from bson import json_util
        seeds_dir = Path(__file__).resolve().parent.parent / "seeds"
        if seeds_dir.exists():
            logger.info("Fresh database detected; restoring full data snapshot from seeds directory...")
            for seed_file in sorted(seeds_dir.glob("*.json")):
                col_name = seed_file.stem
                try:
                    with open(seed_file, "r", encoding="utf-8") as f:
                        docs = json_util.loads(f.read())
                    if docs:
                        for doc in docs:
                            doc_id = doc.get("_id")
                            if doc_id:
                                await db[col_name].replace_one({"_id": doc_id}, doc, upsert=True)
                            else:
                                await db[col_name].insert_one(doc)
                except Exception as seed_err:
                    logger.warning(f"Failed to auto-seed {col_name}: {seed_err}")

    if settings.is_production:
        # Provision only generic categories and SLA defaults; never insert demo users/tickets.
        from app.seed_reference_data import seed_reference_data
        await seed_reference_data()
    elif settings.SEED_DEMO_DATA and user_count == 0:
        from app.seed import seed_data
        await seed_data()

    # Give legacy institutions a deterministic Primary College Admin if none exists.
    # This is a one-time, idempotent migration; an existing primary is never overwritten.
    institutions = await db.institutions.find({"status": "active"}).to_list(None)
    for institution in institutions:
        institution_id = str(institution["_id"])
        existing_primary = await db.users.find_one({
            "institution_id": institution_id, "role": "admin",
            "admin_level": "primary", "is_active": True
        })
        if not existing_primary:
            first_admin = await db.users.find({
                "institution_id": institution_id, "role": "admin",
                "$or": [{"is_active": True}, {"is_active": {"$exists": False}}]
            }).sort("created_at", 1).to_list(1)
            if first_admin:
                await db.users.update_one(
                    {"_id": first_admin[0]["_id"], "institution_id": institution_id, "role": "admin"},
                    {"$set": {"admin_level": "primary"}}
                )

    # Seed routines can create reference documents; attach any newly created legacy records too.
    for collection_name in ("users", "tickets", "campuses", "buildings", "floors", "rooms", "blocks", "campus_locations", "incidents", "knowledge_base", "categories", "departments", "sla_policies", "comments", "feedback", "audit_logs", "feature_requests", "uploads", "notifications", "user_preferences", "knowledge_base_votes"):
        await db[collection_name].update_many({"institution_id": {"$exists": False}}, {"$set": {"institution_id": "INST-DEFAULT"}})

    # Train or initialize ML models
    try:
        from app.services.ml_service import train_models_from_db
        await train_models_from_db()
    except Exception as ml_err:
        logger.warning(f"ML models initialization note: {ml_err}")

    # Launch background SLA breach monitor
    sla_task = asyncio.create_task(sla_breach_monitor_loop())

    yield

    sla_task.cancel()
    try:
        await sla_task
    except asyncio.CancelledError:
        pass

    # Shutdown: Close DB
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Flexible campus support, problem reporting, and issue resolution platform REST API",
    version="1.0.0",
    docs_url="/api/docs" if settings.DOCS_ENABLED and not settings.is_production else None,
    redoc_url="/api/redoc" if settings.DOCS_ENABLED and not settings.is_production else None,
    openapi_url="/api/openapi.json" if settings.DOCS_ENABLED and not settings.is_production else None,
    lifespan=lifespan
)

# Reject unexpected Host headers (helps prevent Host-header based attacks).
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$" if not settings.is_production else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Global health check
@app.get("/health", tags=["Health"])
async def health_check():
    if db_manager.is_mock:
        ready = not settings.is_production
        database_status = "mock_in_memory"
    elif db_manager.client is not None and db_manager.db is not None:
        try:
            await db_manager.client.admin.command("ping")
            ready = True
            database_status = "mongodb_connected"
        except Exception:
            ready = False
            database_status = "unavailable"
    else:
        ready = False
        database_status = "unavailable"

    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "healthy" if ready else "not_ready",
            "service": settings.PROJECT_NAME,
            "database": database_status,
        },
    )

# Register all Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(tickets_router, prefix=settings.API_V1_STR)
app.include_router(assignments_router, prefix=settings.API_V1_STR)
app.include_router(comments_router, prefix=settings.API_V1_STR)
app.include_router(uploads_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router, prefix=settings.API_V1_STR)
app.include_router(categories_router, prefix=settings.API_V1_STR)
app.include_router(campus_router, prefix=settings.API_V1_STR)
app.include_router(sla_router, prefix=settings.API_V1_STR)
app.include_router(kb_router, prefix=settings.API_V1_STR)
app.include_router(feedback_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(audit_logs_router, prefix=settings.API_V1_STR)
app.include_router(incidents_router, prefix=settings.API_V1_STR)
app.include_router(feature_requests_router, prefix=settings.API_V1_STR)
app.include_router(institutions_router, prefix=settings.API_V1_STR)
app.include_router(registration_router, prefix=settings.API_V1_STR)
app.include_router(admin_governance_router, prefix=settings.API_V1_STR)
app.include_router(staff_performance_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
