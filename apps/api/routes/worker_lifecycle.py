"""Authenticated Cloud Scheduler entry point for the external worker controller."""

from __future__ import annotations

import jwt
import logging
from fastapi import APIRouter, Header, HTTPException

from services.platform.config import get_settings
from services.platform.worker_lifecycle import reconcile_worker_pool

router = APIRouter(prefix="/api/v1/internal/worker-lifecycle", tags=["platform"])
_google_keys = jwt.PyJWKClient("https://www.googleapis.com/oauth2/v3/certs", cache_keys=True)
_logger = logging.getLogger(__name__)


def _verify_scheduler(authorization: str | None) -> None:
    settings = get_settings()
    if not settings.worker_lifecycle_enabled:
        raise HTTPException(status_code=404)
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401)
    token = authorization.removeprefix("Bearer ")
    try:
        key = _google_keys.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            audience=settings.worker_lifecycle_scheduler_audience,
            issuer=["https://accounts.google.com", "accounts.google.com"],
        )
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=401) from None
    verified = claims.get("email_verified")
    if claims.get("email") != settings.worker_lifecycle_scheduler_email or (verified is not True and verified != "true"):
        raise HTTPException(status_code=403)


@router.post("/tick")
def tick_worker_lifecycle(authorization: str | None = Header(default=None)) -> dict[str, str]:
    _verify_scheduler(authorization)
    result = reconcile_worker_pool()
    _logger.info("Scheduled worker lifecycle tick: %s", result)
    if result in {"operation_failed", "unhealthy"}:
        raise HTTPException(status_code=503, detail="Worker pool needs operator attention.")
    return {"status": result}
