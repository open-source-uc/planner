from fastapi import APIRouter, Depends

from .. import sync
from ..user.auth import (
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
