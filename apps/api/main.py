from fastapi import FastAPI

from apps.api.routes.auth import router as auth_router
from apps.api.routes.content import router as content_router
from services.platform.config import get_settings


settings = get_settings()

app = FastAPI(
    title="Lina Learning API",
    version="0.1.0",
    description=f"Phase 0 API shell for Lina Personal Learning System ({settings.app_env}).",
)
app.state.settings = settings
app.include_router(auth_router)
app.include_router(content_router)


@app.get("/health", tags=["platform"])
def health() -> dict[str, str]:
    """Return a lightweight process health response."""

    return {"status": "ok", "service": "lina-learning-api"}


@app.get("/api/v1/status", tags=["platform"])
def status() -> dict[str, str]:
    """Expose foundation status without implying product feature readiness."""

    return {"phase": "phase-0", "status": "foundation-ready"}
