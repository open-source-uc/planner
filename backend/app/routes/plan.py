from fastapi import APIRouter, Depends

from app import sync
from app.limiting import ratelimit_guest, ratelimit_user
from app.plan.course import PseudoCourse
from app.plan.generation import generate_empty_plan, generate_recommended_plan
from app.plan.plan import ValidatablePlan
from app.plan.storage import (
    LowDetailPlanView,
    PlanView,
    get_plan_details,
    get_user_plans,
    modify_plan_metadata,
    modify_validatable_plan,
    remove_plan,
    store_plan,
)
from app.plan.validation.curriculum.solve import solve_curriculum
from app.plan.validation.diagnostic import ValidationResult
from app.plan.validation.validate import diagnose_plan, list_swapouts
from app.sync.database import course_info
from app.user.auth import (
    ModKey,
    UserKey,
    require_authentication,
    require_mod_auth,
)
from app.user.key import Rut

router = APIRouter(prefix="/plan")


@router.get("/empty_for", response_model=ValidatablePlan)
async def empty_plan_for_user(user: UserKey = Depends(require_authentication)):
    """
    Generate an empty plan using the current user as context.
    For example, the created plan includes all passed courses, uses the curriculum
    version for the given user and selects the student's official choice of
    major/minor/title if available.

    (Currently this is equivalent to `empty_guest_plan()` until we get user data)
    """
    return await generate_empty_plan(user)


@router.get("/empty_for_any", response_model=ValidatablePlan)
async def empty_plan_for_any_user(
    user_rut: Rut,
    mod: ModKey = Depends(require_mod_auth),
):
    """
    Same functionality as `empty_plan_for_user`, but works for any user identified by
    their RUT with `user_rut`.
    Moderator access is required.
    """
    return await generate_empty_plan(mod.as_any_user(user_rut))


@router.get("/empty_guest", response_model=ValidatablePlan)
async def empty_guest_plan() -> ValidatablePlan:
    """
    Generates a generic empty plan with no user context, using the latest curriculum
    version.
    """
    return await generate_empty_plan(None)


@router.post("/validate", response_model=ValidationResult)
async def validate_guest_plan(
    plan: ValidatablePlan,
    _limited: None = Depends(ratelimit_guest("8/5second")),
) -> ValidationResult:
    """
    Validate a plan, generating diagnostics.
    """
    return await diagnose_plan(plan, user_ctx=None)


@router.post("/validate_for", response_model=ValidationResult)
async def validate_plan_for_user(
    plan: ValidatablePlan,
    user: UserKey = Depends(ratelimit_user("7/5second")),
) -> ValidationResult:
    """
    Validate a plan, generating diagnostics.
    Includes diagnostics tailored for the given user and skips diagnostics that do not
    apply to the particular student.
    """
    user_ctx = await sync.get_student_info(user)
    return await diagnose_plan(plan, user_ctx)


@router.post("/validate_for_any", response_model=ValidationResult)
async def validate_plan_for_any_user(
    plan: ValidatablePlan,
    user_rut: Rut,
    mod: ModKey = Depends(require_mod_auth),
) -> ValidationResult:
    """
    Same functionality as `validate_plan_for_user`, but works for any user identified by
    their RUT with `user_rut`.
    Moderator access is required.
    """
    user_ctx = await sync.get_student_info(mod.as_any_user(user_rut))
    return await diagnose_plan(plan, user_ctx)


@router.post("/swapouts", response_model=list[list[PseudoCourse]])
async def list_swapouts_guest(
    plan: ValidatablePlan,
    semester_idx: int,
    class_idx: int,
    _limited: None = Depends(ratelimit_guest("8/5second")),
):
    return await list_swapouts(plan, semester_idx, class_idx)


@router.post("/swapouts_for", response_model=list[list[PseudoCourse]])
async def list_swapouts_for(
    plan: ValidatablePlan,
    semester_idx: int,
    class_idx: int,
    _limited: UserKey = Depends(ratelimit_user("7/5second")),
):
    return await list_swapouts(plan, semester_idx, class_idx)


@router.post("/curriculum_graph")
async def get_curriculum_validation_graph(
    plan: ValidatablePlan,
    mode: str,
    _limited: None = Depends(ratelimit_guest("8/5second")),
) -> str:
    """
    Get the curriculum validation graph for a certain plan, in Graphviz DOT format.
    Useful for debugging and kind of a bonus easter egg.
    """
    courseinfo = await course_info()
    curriculum = await sync.get_curriculum(plan.curriculum)
    g = solve_curriculum(courseinfo, plan.curriculum, curriculum, plan.classes)
    if mode == "debug":
        return g.dump_graphviz_debug(curriculum)
    return g.dump_graphviz_pretty(curriculum)


@router.post("/generate", response_model=ValidatablePlan)
async def generate_plan(
    passed: ValidatablePlan,
    reference: ValidatablePlan | None = None,
    _limited: UserKey = Depends(ratelimit_guest("15/minute")),
):
    """
    From a base plan, generate a new plan that should lead the user to earn their title
    of choice.
    """
    return await generate_recommended_plan(passed, reference)


@router.post("/storage", response_model=PlanView)
async def save_plan(
    name: str,
    plan: ValidatablePlan,
    user: UserKey = Depends(require_authentication),
) -> PlanView:
    """
    Save a plan with the given name in the storage of the current user.
    Fails if the user is not logged in.
    """
    return await store_plan(plan_name=name, user=user, plan=plan)


@router.post("/storage/any", response_model=PlanView)
async def save_any_plan(
    name: str,
    plan: ValidatablePlan,
    user_rut: Rut,
    mod: ModKey = Depends(require_mod_auth),
) -> PlanView:
    """
    Same functionality as `save_plan`, but works for any user identified by
    their RUT with `user_rut`.
    Moderator access is required.
    All `/storage/any` endpoints (and sub-resources) should require
    moderator access.
    """
    return await store_plan(plan_name=name, user=mod.as_any_user(user_rut), plan=plan)


@router.get("/storage", response_model=list[LowDetailPlanView])
async def read_plans(
    user: UserKey = Depends(require_authentication),
) -> list[LowDetailPlanView]:
    """
    Fetches an overview of all the plans in the storage of the current user.
    Fails if the user is not logged in.
    Does not return the courses in each plan, only the plan metadata required
    to show the users their list of plans (e.g. the plan id).
    """
    return await get_user_plans(user)


@router.get("/storage/any", response_model=list[LowDetailPlanView])
async def read_any_plans(
    user_rut: Rut,
    mod: ModKey = Depends(require_mod_auth),
) -> list[LowDetailPlanView]:
    """
    Same functionality as `read_plans`, but works for any user identified by
    their RUT with `user_rut`.
    Moderator access is required.
    """
    return await get_user_plans(mod.as_any_user(user_rut))


@router.get("/storage/details", response_model=PlanView)
async def read_plan(
    plan_id: str,
    user: UserKey = Depends(require_authentication),
) -> PlanView:
    """
    Fetch the plan details for a given plan id.
    Requires the current user to be the plan owner.
    """
    return await get_plan_details(user=user, plan_id=plan_id)


@router.get("/storage/any/details", response_model=PlanView)
async def read_any_plan(
    plan_id: str,
    user: ModKey = Depends(require_mod_auth),
) -> PlanView:
    """
    Same functionality as `read_plan`, but works for any plan of any user
    identified by their RUT.
    Moderator access is required.
    """
    return await get_plan_details(user=user, plan_id=plan_id, mod_access=True)


@router.put("/storage", response_model=PlanView)
async def update_plan(
    plan_id: str,
    new_plan: ValidatablePlan,
    user: UserKey = Depends(require_authentication),
) -> PlanView:
    """
    Modifies the courses of a plan by id.
    Requires the current user to be the owner of this plan.
    Returns the updated plan.
    """
    return await modify_validatable_plan(user=user, plan_id=plan_id, new_plan=new_plan)


@router.put("/storage/any", response_model=PlanView)
async def update_any_plan(
    plan_id: str,
    new_plan: ValidatablePlan,
    user: ModKey = Depends(require_mod_auth),
) -> PlanView:
    """
    Same functionality as `update_plan`, but works for any plan of any user
    identified by their RUT.
    Moderator access is required.
    """
    return await modify_validatable_plan(
        user=user,
        plan_id=plan_id,
        new_plan=new_plan,
        mod_access=True,
    )


@router.put("/storage/metadata", response_model=PlanView)
async def update_plan_metadata(
    plan_id: str,
    set_name: str | None = None,
    set_favorite: bool | None = None,
    user: UserKey = Depends(require_authentication),
) -> PlanView:
    """
    Modifies the metadata of a plan (currently only `name` or `is_favorite`).
    Modify one attribute per request.
    Requires the current user to be the owner of this plan.
    Returns the updated plan.
    """

    return await modify_plan_metadata(
        user=user,
        plan_id=plan_id,
        set_name=set_name,
        set_favorite=set_favorite,
    )


@router.put("/storage/any/metadata", response_model=PlanView)
async def update_any_plan_metadata(
    plan_id: str,
    set_name: str | None = None,
    set_favorite: bool | None = None,
    mod: ModKey = Depends(require_mod_auth),
) -> PlanView:
    """
    Same functionality as `update_plan_metadata`, but works for any plan of any user
    identified by their RUT.
    Moderator access is required.
    """

    return await modify_plan_metadata(
        user=mod,
        plan_id=plan_id,
        set_name=set_name,
        set_favorite=set_favorite,
        mod_access=True,
    )


@router.delete("/storage", response_model=PlanView)
async def delete_plan(
    plan_id: str,
    user: UserKey = Depends(require_authentication),
) -> PlanView:
    """
    Deletes a plan by ID.
    Requires the current user to be the owner of this plan.
    Returns the removed plan.
    """
    return await remove_plan(user=user, plan_id=plan_id)


@router.delete("/storage/any", response_model=PlanView)
async def delete_any_plan(
    plan_id: str,
    mod: ModKey = Depends(require_mod_auth),
) -> PlanView:
    """
    Same functionality as `delete_plan`, but works for any plan of any user
    identified by their RUT.
    Moderator access is required.
    """
    return await remove_plan(user=mod, plan_id=plan_id, mod_access=True)
