"""Protected role-specific API surfaces."""

from fastapi import APIRouter, Depends

from services.platform.auth import (
    AuthenticatedPrincipal,
    UserRole,
    get_current_principal,
    require_role,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me")
async def current_user(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> dict[str, str | None]:
    """Return only the verified identity context needed by the web shell."""

    return {
        "subject": principal.subject,
        "role": principal.role.value,
        "email": principal.email,
    }


@router.get("/student/shell")
async def student_shell(
    principal: AuthenticatedPrincipal = Depends(
        require_role(UserRole.STUDENT),
    ),
) -> dict[str, str]:
    """Student-only surface; parent analytics never belong here."""

    return {
        "surface": "student",
        "role": principal.role.value,
        "message": "Learning space ready.",
    }


@router.get("/parent/admin-shell")
async def parent_admin_shell(
    principal: AuthenticatedPrincipal = Depends(
        require_role(UserRole.PARENT_ADMIN),
    ),
) -> dict[str, str]:
    """Parent/admin-only surface for oversight and controls."""

    return {
        "surface": "parent-admin",
        "role": principal.role.value,
        "message": "Parent control surface ready.",
    }