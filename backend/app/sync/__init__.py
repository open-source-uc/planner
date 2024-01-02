"""
Update local database with an official but ugly source.
Currently using unofficial sources until we get better API access.
"""

import logging
from datetime import timedelta

from fastapi import HTTPException

from app.plan.validation.curriculum.tree import (
    Curriculum,
    CurriculumSpec,
)
from app.redis import get_redis
from app.settings import settings
from app.sync.database import curriculum_storage
from app.sync.siding import translate as siding_translate
from app.user.auth import UserKey, allow_force_login
from app.user.info import StudentInfo

log = logging.getLogger("sync")


async def get_curriculum(spec: CurriculumSpec) -> Curriculum:
    """
    Get the full curriculum definition for a particular curriculum spec.

    NOTE: Some users of this function, in particular `app.plan.generation`, modify the
    returned `Curriculum`.
    Therefore, each call to `get_curriculum` should result in a fresh curriculum.
    """

    storage = await curriculum_storage()
    out = Curriculum.empty(spec)

    # Fetch major (or common plan)
    curr = storage.get_major(spec)
    if curr is not None:
        out.extend(curr)

    # Fetch minor
    if spec.has_minor():
        curr = storage.get_minor(spec)
        if curr is not None:
            out.extend(curr)

    # Fetch title
    if spec.has_title():
        curr = storage.get_title(spec)
        if curr is not None:
            out.extend(curr)

    return out


async def get_student_info(user: UserKey) -> StudentInfo:
    lock_key = f"student-lock:{user.rut}"
    data_key = f"student-data:{user.rut}"

    async with get_redis() as redis:
        lock = redis.lock(
            lock_key,
            # Just for safety
            # If the machine crashes while the lock is held, we don't want the user to
            # be permanently locked out of Planner
            timeout=60,
        )
        async with lock:
            # Use the data in redis if available
            data = await redis.get(data_key)
            if data is not None:
                return StudentInfo.parse_raw(data)

            # Data not in cache, fetch it while we hold the lock
            info = await _fetch_student_data(user)

            # Store the info in the redis db, with an expiry time
            await redis.set(
                data_key,
                info.json(),
                ex=timedelta(seconds=settings.student_info_expire),
            )

            return info


async def _fetch_student_data(user: UserKey) -> StudentInfo:
    """
    Fetch the student info for a user.
    Always hits the SIDING service.
    Handles the special case of mods without SIDING info trying to log in.
    """

    log.info("fetching user data for student %s from SIDING", user.rut)
    try:
        return await siding_translate.fetch_student_info(user.rut)
    except siding_translate.InvalidStudentError as err:
        if await allow_force_login(user):
            # Allow moderators and admins to login anyway, even with incomplete
            # info
            return StudentInfo(
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
