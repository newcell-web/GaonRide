from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import AI_AVAILABLE
from backend.database import engine, init_db
from backend.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="GaonRide AI", version="0.1.0", lifespan=lifespan)

# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------
from backend.routers import voice as voice_module
from backend.routers import requests as requests_module
from backend.routers import groups as groups_module
from backend.routers import drivers as drivers_module
from backend.routers import geo as geo_module
from backend.routers import seed as seed_module

app.include_router(voice_module.router, prefix="/api")
app.include_router(requests_module.router, prefix="/api")
app.include_router(groups_module.router, prefix="/api")
app.include_router(drivers_module.router, prefix="/api")
app.include_router(geo_module.router, prefix="/api")
app.include_router(seed_module.router, prefix="/api")


# ---------------------------------------------------------------------------
# 404 handler for unmatched /api/ routes
# ---------------------------------------------------------------------------

@app.exception_handler(404)
async def not_found_handler(request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "API endpoint not found"}, status_code=404)
    # For non-API routes, let StaticFiles handle it
    raise exc


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """Return service health: AI availability and DB connectivity."""
    db_ok = False
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    if AI_AVAILABLE:
        message = "GaonRide AI is fully operational."
    else:
        message = "GaonRide AI is running (AI features disabled — set GROQ_API_KEY to enable)."

    return HealthResponse(ai_available=AI_AVAILABLE, db_ok=db_ok, message=message)


# ---------------------------------------------------------------------------
# Static file mount — MUST be last, after all API routes
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
