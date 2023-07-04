from fastapi import APIRouter, Depends, HTTPException
from prisma.models import (
    AccessLevel as DbAccessLevel,
)

from .. import sync
from ..sync.siding import translate as siding_translate
from ..user.auth import (
    AccessLevelOverview,
    AdminKey,
    require_admin_auth,
)

router = APIRouter(prefix="/admin")


@router.post("/sync")
async def sync_database(
    courses: bool = False,
    offer: bool = False,
    admin: AdminKey = Depends(require_admin_auth),
):
    """
    Initiate a synchronization of the internal database from external sources.
    """
    await sync.run_upstream_sync(courses, offer)
    return {
        "message": "Database updated from external sources",
    }


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
