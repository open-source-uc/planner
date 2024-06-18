from fastapi import APIRouter, Depends

from app import sync
from app.user.auth import (
    login_cas,
    require_admin_auth,
    require_authentication,
    require_mod_auth,
)
from app.user.info import StudentInfo
from app.user.key import AdminKey, ModKey, Rut, UserKey

router = APIRouter(prefix="/user")


@router.get("/login")
async def authenticate(
    next: str | None = None,
    ticket: str | None = None,
    impersonate_rut: Rut | None = None,
):
    """
    Redirect the browser to this page to initiate authentication.
    """
    return await login_cas(next, ticket, impersonate_rut)


@router.get("/check")
async def check_auth(user: UserKey = Depends(require_authentication)):
    """
    Request succeeds if user authentication was successful.
    Otherwise, the request fails with 401 Unauthorized.
    """
    return {"message": "Authenticated"}


@router.get("/check/mod")
async def check_mod(user: ModKey = Depends(require_mod_auth)):
    """
    Request succeeds if user authentication and mod authorization were successful.
    Otherwise, the request fails with 401 Unauthorized or 403 Forbidden.
    """
    return {"message": "Authenticated with mod access"}


@router.get("/check/admin")
async def check_admin(user: AdminKey = Depends(require_admin_auth)):
    """
    Request succeeds if user authentication and admin authorization were successful.
    Otherwise, the request fails with 401 Unauthorized or 403 Forbidden.
    """
    return {"message": "Authenticated with admin access"}


@router.get("/info", response_model=StudentInfo)
async def get_student_info(user: UserKey = Depends(require_authentication)):
    """
    Get the student info for the currently logged in user.
    Requires authentication (!)
    This forwards a request to the SIDING service.
    """
    return await sync.get_student_info(user)


@router.get("/info_for_any_user", response_model=StudentInfo)
async def get_student_info_for_any_user(
    user_rut: Rut,
    mod: ModKey = Depends(require_mod_auth),
):
    """
    Same functionality as `get_student_info`, but works for any user identified by
    their RUT with `user_rut`.
    Moderator access is required.
    """
    return await sync.get_student_info(mod.as_any_user(user_rut))
