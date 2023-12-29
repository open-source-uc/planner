"""
Update local database with an official but ugly source.
Currently using unofficial sources until we get better API access.
"""

import time
from collections import OrderedDict

from fastapi import HTTPException

from app.plan.validation.curriculum.tree import (
    Curriculum,
    CurriculumSpec,
)
from app.settings import settings
from app.sync.database import curriculum_storage
from app.sync.siding import translate as siding_translate
from app.user.auth import UserKey, allow_force_login
from app.user.info import StudentInfo
from app.user.key import Rut


async def get_curriculum(spec: CurriculumSpec) -> Curriculum:
    """
    Get the full curriculum definition for a particular curriculum spec.

    NOTE: Some users of this function, in particular `app.plan.generation`, modify the
    returned `Curriculum`.
    Therefore, each call to `get_curriculum` should result in a fresh curriculum.
    """

    storage = await curriculum_storage()
    out = Curriculum.empty()

    # Fetch major (or common plan)
    curr = storage.get_major(spec)
    if curr is None:
        raise HTTPException(404, "major not found")
    out.extend(curr)

    # Fetch minor
    if spec.has_minor():
        curr = storage.get_minor(spec)
        if curr is None:
            raise HTTPException(404, "minor not found")
        out.extend(curr)

    # Fetch title
    if spec.has_title():
        curr = storage.get_title(spec)
        if curr is None:
            raise HTTPException(404, "title not found")
        out.extend(curr)

    return out


# TODO: Move this to redis
_student_context_cache: OrderedDict[Rut, tuple[StudentInfo, float]] = OrderedDict()


async def get_student_data(user: UserKey) -> StudentInfo:
    # Use entries in cache
    if user.rut in _student_context_cache:
        return _student_context_cache[user.rut][0]

    # Delete old entries from cache
    now = time.monotonic()
    while _student_context_cache:
        rut, (_ctx, expiration) = next(iter(_student_context_cache.items()))
        if now <= expiration:
            break
        _student_context_cache.pop(rut)

    # Request user context from SIDING
    print(f"fetching user data for student {user.rut} from SIDING...")
    try:
        info = await siding_translate.fetch_student_info(user.rut)
    except siding_translate.InvalidStudentError as err:
        if await allow_force_login(user):
            # Allow moderators and admins to login anyway, even with incomplete info
            info = StudentInfo(
                full_name=str(user.rut),
                cyear="?",
                is_cyear_supported=False,
                reported_major=None,
                reported_minor=None,
                reported_title=None,
                passed_courses=[],
                current_semester=0,
                next_semester=0,
                admission=(1900, 1),
            )
        else:
            raise HTTPException(
                403,
                "User is not a valid engineering student.",
            ) from err

    # Add to cache and return
    _student_context_cache[user.rut] = (
        info,
        time.monotonic() + settings.student_info_expire,
    )
    return info
