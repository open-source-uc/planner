from fastapi import APIRouter, Depends, HTTPException
from prisma.models import (
    AccessLevel as DbAccessLevel,
)

from .. import sync
from ..sync.siding import translate as siding_translate
from ..user.auth import (
    AccessLevelOverview,
    login_cas,
    require_admin_auth,
    require_authentication,
    require_mod_auth,
)
from ..user.info import StudentContext
from ..user.key import AdminKey, ModKey, UserKey

router = APIRouter(prefix="/user")


@router.get("/login")
async def authenticate(
    next: str | None = None,
    ticket: str | None = None,
):
    """
    Redirect the browser to this page to initiate authentication.
    """
    return await login_cas(next, ticket)


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


@router.get("/info", response_model=StudentContext)
async def get_student_info(user: UserKey = Depends(require_authentication)):
    """
    Get the student info for the currently logged in user.
    Requires authentication (!)
    This forwards a request to the SIDING service.
    """
    return await sync.get_student_data(user)


@router.get("/mod", response_model=list[AccessLevelOverview])
async def view_mods(user: AdminKey = Depends(require_admin_auth)):
    """
    Show a list of all current mods with username and RUT. Up to 50 records.
    """
    mods = await DbAccessLevel.prisma().find_many(take=50)

    named_mods: list[AccessLevelOverview] = []
    for mod in mods:
        named_mods.append(AccessLevelOverview(**dict(mod)))
        try:
            print(f"fetching user data for user {mod.user_rut} from SIDING...")
            # TODO: check if this function works for non-students
            data = await siding_translate.fetch_student_info(mod.user_rut)
            named_mods[-1].name = data.full_name
        finally:
            # Ignore if couldn't get the name by any reason to at least show
            # the RUT, which is more important.
            pass
    return named_mods


@router.post("/mod")
async def add_mod(rut: str, user: AdminKey = Depends(require_admin_auth)):
    """
    Give mod access to a user with the specified RUT.
    """
    return await DbAccessLevel.prisma().upsert(
        where={
            "user_rut": rut,
        },
        data={
            "create": {
                "user_rut": rut,
                "is_mod": True,
            },
            "update": {
                "is_mod": True,
            },
        },
    )


@router.delete("/mod")
async def remove_mod(rut: str, user: AdminKey = Depends(require_admin_auth)):
    """
    Remove mod access from a user with the specified RUT.
    """
    mod_record = await DbAccessLevel.prisma().find_unique(where={"user_rut": rut})

    if not mod_record:
        raise HTTPException(status_code=404, detail="Mod not found")
    return await DbAccessLevel.prisma().delete(where={"user_rut": rut})
