from fastapi import APIRouter, Depends, HTTPException
from prisma.models import (
    AccessLevel as DbAccessLevel,
)

from app import sync
from app.sync.siding import translate as siding_translate
from app.user.auth import (
    AccessLevelOverview,
    AdminKey,
    require_admin_auth,
)
from app.user.key import Rut

router = APIRouter(prefix="/admin")


@router.post("/sync")
async def sync_database(
    courses: bool,
    curriculums: bool,
    packedcourses: bool,
    admin: AdminKey = Depends(require_admin_auth),
):
    """
    Initiate a synchronization of the internal database from external sources.

    NOTE: This endpoint is currently broken: a server restart is necessary after syncing
    the database in order for the changes to reach all workers.
    """
    await sync.run_upstream_sync(
        courses=courses,
        curriculums=curriculums,
        packedcourses=packedcourses,
    )
    return {
        "message": "Synchronized",
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
            data = await siding_translate.fetch_student_info(Rut(mod.user_rut))
            named_mods[-1].name = data.full_name
        except ValueError as err:
            # TODO: Refactor ValueError to use a custom exception
            if "Not a valid" in str(err):
                # Error: "User is not a valid engineering student."
                # Ignore if couldn't get the name to at least show the RUT, which
                # is more important.
                pass
    return named_mods


@router.post("/mod")
async def add_mod(rut: Rut, user: AdminKey = Depends(require_admin_auth)):
    """
    Give mod access to a user with the specified RUT.
    """
    if not rut.validate_dv():
        raise HTTPException(status_code=400, detail="RUT chileno no válido")

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
async def remove_mod(rut: Rut, user: AdminKey = Depends(require_admin_auth)):
    """
    Remove mod access from a user with the specified RUT.
    """
    mod_record = await DbAccessLevel.prisma().find_unique(where={"user_rut": rut})

    if not mod_record:
        raise HTTPException(status_code=404, detail="Mod not found")
    return await DbAccessLevel.prisma().delete(where={"user_rut": rut})
