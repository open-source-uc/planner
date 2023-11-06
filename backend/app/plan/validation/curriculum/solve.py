"""
Fill the slots of a curriculum with courses, making sure that there is no overlap
within a block and respecting exclusivity rules.

Overview of the flow when solving a curriculum:
1. A curriculum tree is built from external sources such as SIDING, scrapes and
    hardcoded rules (see `sync.collate`).
2. The result is a curriculum tree, as defined in `plan.validation.curriculum.tree`.
    Along with a course database, this tree completely defines the curriculum.
3. When a plan needs to be validated, `solve_curriculum` is called with the taken
    courses and the curriculum tree as arguments.
4. Now, we build a flow network (see https://en.wikipedia.org/wiki/Flow_network), where
    taken courses act as flow sources, and a single sink consumes this flow.
    The flow network is based on the curriculum tree.
    In particular, a source node is created for each taken course, and it is connected
    to the leaves of the curriculum tree that accept this course.
    The root of the curriculum tree becomes the sink.
5. A variation of min-cost-max-flow (see
    https://en.wikipedia.org/wiki/Minimum-cost_flow_problem) is run on the tree.
    In particular, we add virtual "filler courses" that are able to supply enough flow
    to fill the network, but with a high cost.
    Taken courses, on the other hand, have a low cost.
    Therefore, running min-cost-max-flow tries to fill the network with flow with
    the least cost. That is, the least amount of virtual courses.
6. Once `solve_curriculum` returns, other modules like
    `plan.validation.curriculum.diagnose` analyze which edges have flow in them.
    The courses that supply flow are "active".
    If a filler course is active, it means the solver could not find a way to fill the
    network with flow with only taken courses, so some courses need to be added to the
    plan to make it complete.
    This is interpreted as the solver suggesting to add the filler course to the plan.

Some extra details:
- Courses have limited multiplicity. This means that taking the course twice may not
    contribute more flow to the network.
    Most courses can be taken only once (and still contribute), but some have stranger
    restrictions.
    For example, abstract courses (like "any OFG") can be taken multiple times.
    Some are even stranger, like sports selection team courses, which can count up to 2
    times.
    Some courses share their flow budget. For example, courses ICS1113 and ICS113H are
    equivalent, and therefore even if the two are taken together, only 1 can provide
    flow.
    To model all of these situations, courses may share a common source node, with
    limited flow capacity.
- Sometimes there are several options to choose fillers.
    This represents that there are several valid ways to fill the plan, for example
    choosing an OPI or a different minor optative.
    This choice is ultimately up to the user, so the solver should report all of the
    available options.
    To achieve this, the solver checks each potential filler to see which gaps can it
    fill.
- For optimization purposes, some nodes that exist in the curriculum tree may not exist
    in the actually optimized flow network.
    For example, if node A connected to node B, B connected to node C, and there were no
    other connections to B, node B could be completely eliminated and replaced by a
    direct connection from A to C.

Some interesting combinations in terms of solving:
M233-N207-40095
M175-N207-40095
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from ortools.linear_solver import pywraplp as lmip

from app.plan.course import (
    ConcreteId,
    EquivalenceId,
    PseudoCourse,
    pseudocourse_with_credits,
)
from app.plan.courseinfo import CourseInfo
from app.plan.plan import ClassId
from app.plan.validation.curriculum.tree import (
    Block,
    Curriculum,
    CurriculumSpec,
    FillerCourse,
    Leaf,
    Multiplicity,
)

# Infinite placeholder.
# A huge value that still fits in a 64-bit integer.
INFINITY: int = 10**18

# Cost of using a single credit of a filler course.
# Filler courses are courses that the student has not taken, but that they could take.
# The cost of filler courses is higher than taken courses so that the solver prefers
# already-taken courses before adding new courses.
FILLER_COST = 10**4
# Cost of using a single credit of an already-assigned course.
# The idea behind assigning a cost to using courses is that the solve prefers to leave
# as many courses as possible blank. This way the user can notice that some courses are
# unnecessary.
TAKEN_COST = 10**3
# Cost of recoloring a single credit.
# Recoloring is assigning a course to a different block than what it's currently
# assigned to.
# This value should be smaller than `TAKEN_COST` so that the solver prefers to recolor
# before taking more courses.
# However, it should be large enough that custom cost offsets are smaller do not
# overcome the recoloring cost.
RECOLOR_COST = 10**1


IntExpr = int | lmip.LinearExpr


@dataclass
class BlockEdgeInfo:
    """
    Represents an edge from a course instance to a block in the curriculum graph.

    If the edge has flow going through it, it means that the course was assigned to the
    blocks in `block_path`.

    - block_path: The curriculum block that is connected to receive the flow through
        this edge.
        The first element is the root, the last element is the leaf and there is any
        number of elements in between.
    - needs_recolor: Indicates whether putting flow through this edge requires changing
        the course-block assignment.
    - flow: The amount of credits assigned from this course to the given block.
        This might be smaller than the amount of credits corresponding to the course, if
        the block is already almost full.
    - active_var: Internal boolean variable indicating whether the edge is active or
        not.
    - flow_var: Internal variable indicating how many credits are flowing through this
        edge. May only be non-zero if the edge is active.
    """

    block_path: tuple[Block, ...]
    needs_recolor: bool
    flow: int

    active_var: lmip.Variable
    flow_var: lmip.Variable


@dataclass
class InstanceEdges:
    """
    Represents an instance of a course associated to a layer.

    Contains variables that indicate which block this instance is connected to.

    - active_edge: The edge that is currently receiving flow from this course.
        There should only be zero or one edges, otherwise it's an error.
    - block_edges: All the blocks that are able to receive flow from this course.
        Only up to one course can actually receive flow, though.
    """

    active_edge: BlockEdgeInfo | None = None
    block_edges: list[BlockEdgeInfo] = field(default_factory=list)


@dataclass
class UsableInstance:
    """
    Represents an instance of a course within the plan.

    - code: The code associated with this course instance.
    - credits: How many credits does this course stand for.
    - filler: If this course is a filler course, this is the filler data.
    - instance_idx: The instance index of this course.
        Instance indices start from zero, and go up for each course with the same code.
        Instance indices for filler courses continue from the taken instance indices.
    - flat_order: The order of this course within the plan.
        Used for prioritization.
        The `flat_order` values of filler courses continues after taken courses.
    - original_pseudocourse: The original `PseudoCourse` instance that gave birth to
        this `UsableInstance`.
        Should not be used to identify the instance.
        In particular, do not use `original_pseudocourse.code`, since this would ignore
        all course equivalencies!
    """

    code: str
    credits: int
    filler: FillerCourse | None
    instance_idx: int
    flat_order: int
    original_pseudocourse: PseudoCourse

    flow: int
    flow_var: lmip.Variable
    layers: defaultdict[str, InstanceEdges] = field(
        default_factory=lambda: defaultdict(InstanceEdges),
    )


@dataclass
class UsableCourse:
    """
    Contains information about the instances of a particular course code that the user
    coursed or is able to course.
    """

    # The multiplicity of this course.
    # This is the maximum amount of credits that can flow through all instances.
    # If `None`, there is no limit on the amount of credits that can count.
    multiplicity: Multiplicity
    # The total amount of credits in usable courses (taken + filler credits).
    total: int
    # Each course instance belonging to this course code.
    instances: list[UsableInstance]


class SolvedCurriculum:
    """
    Context necessary to solve a curriculum.
    Also holds the results of the solving process (hence the name).
    """

    # The CP-SAT model that models this curriculum.
    model: lmip.Solver
    # Taken courses (and filler courses).
    usable: dict[str, UsableCourse]
    # Taken course codes.
    # The keys of `usable`.
    usable_keys: set[str]
    # Indicates the main superblock that each course counts towards.
    superblocks: dict[str, list[str]]

    def __init__(self) -> None:
        # OPTIMIZE: Use a pool for solver objects
        self.model = lmip.Solver.CreateSolver("SCIP")
        self.usable = {}
        self.usable_keys = set()
        self.superblocks = {}
        self.mapping = {}

    def find_swapouts(self, inst: UsableInstance) -> list[list[PseudoCourse]]:
        """
        Given an active course (ie. a course that has flow through it in the current
        optimal solution), compute all of the equivalent fillers that could take its
        place (possibly including itself).
        """

        assert inst.flow > 0
        return _explore_options_for(self, inst)

    def forbid_recolor(self) -> bool:
        """
        Resolve the curriculum, this time respecting previous course-block assignments.
        Returns `True` if forbidding recolor required adding a course.
        """

        return _resolve_with_fixed_colors(self)

    def find_recolors(self) -> list[tuple[ClassId, EquivalenceId]]:
        """
        Reassign the equivalences attached to courses in `plan` in order to match the
        block assignments in `self`.
        """
        return _find_recolors(self)

    def dump_graphviz_pretty(self, curriculum: Curriculum) -> str:
        from app.plan.validation.curriculum.dump import GraphDumper

        return GraphDumper(self, curriculum, "pretty").dump()

    def dump_graphviz_debug(self, curriculum: Curriculum) -> str:
        from app.plan.validation.curriculum.dump import GraphDumper

        return GraphDumper(self, curriculum, "debug").dump()


def _connect_course_instance(
    courseinfo: CourseInfo,
    g: SolvedCurriculum,
    layer_id: str,
    block_order: int,
    block_path: tuple[Block, ...],
    inst: UsableInstance,
    needs_recolor: bool,
) -> lmip.Variable:
    """
    Connect the course instance `inst` to the graph node `connect_to`.
    Creates a minimal amount of nodes and edges to model the connection in the graph.
    """

    # TODO: Per-edge cost

    # Indicates whether the course counts towards the block
    active_var = g.model.BoolVar("")

    # The flow through this edge
    flow_var = g.model.NumVar(0, inst.credits, "")

    # The flow through this edge must be smaller than the course flow
    g.model.Add(flow_var <= inst.flow_var)

    # There can only be flow if this edge is active
    g.model.Add(flow_var <= active_var * inst.credits)

    layer = inst.layers[layer_id]
    layer.block_edges.append(
        BlockEdgeInfo(
            block_path=block_path,
            needs_recolor=needs_recolor,
            flow=0,
            active_var=active_var,
            flow_var=flow_var,
        ),
    )

    return flow_var


@dataclass
class VisitState:
    stack: list[Block] = field(default_factory=list)
    flat_order: int = 0


def _build_visit(
    courseinfo: CourseInfo,
    g: SolvedCurriculum,
    visit_state: VisitState,
    block: Block,
) -> list[lmip.LinearExpr]:
    """
    Recursively visit a block of the curriculum tree, building it as we go.
    Connect all of the children, and then connect this node to `connect_to`.
    """
    visit_state.stack.append(block)

    in_flows: list[lmip.LinearExpr] = []
    max_in_flow = 0
    if isinstance(block, Leaf):
        # A list of courses
        visit_state.flat_order += 1
        block_path = tuple(visit_state.stack)

        # Determine which codes can count towards this block
        usable_codes = block.codes.intersection(g.usable_keys)
        if block.list_code in g.usable_keys:
            usable_codes.add(block.list_code)

        # Visit the usable codes
        for code in usable_codes:
            for inst in g.usable[code].instances:
                # Courses with an assigned equivalence can just connect to the
                # corresponding block at no extra cost
                # However, connecting a course with no equivalence, or connecting a
                # course to a block that does not correspond to their equivalence, has
                # some small extra cost and requires permission from the user
                needs_recolor = (
                    block.layer == ""
                    and isinstance(inst.original_pseudocourse, ConcreteId)
                    and (
                        inst.original_pseudocourse.equivalence is None
                        or inst.original_pseudocourse.equivalence.code
                        != block.list_code
                    )
                )
                child_flow = _connect_course_instance(
                    courseinfo,
                    g,
                    block.layer,
                    visit_state.flat_order,
                    block_path,
                    inst,
                    needs_recolor,
                )
                in_flows.append(child_flow)
                max_in_flow += inst.credits
    else:
        # A combination of blocks
        for c in block.children:
            child_flow = _build_visit(courseinfo, g, visit_state, c)
            in_flows.extend(child_flow)
            max_in_flow += c.cap

    visit_state.stack.pop()

    out_flows: list[lmip.LinearExpr] = in_flows
    if max_in_flow > block.cap:
        out_flow = g.model.NumVar(0, block.cap, "")
        # out_flow <= in_flow
        g.model.Add(
            out_flow <= g.model.Sum(in_flows),
        )
        out_flows = [out_flow]

    return out_flows


def _add_usable_course(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    g: SolvedCurriculum,
    flat_order: int,
    credit_cap: int,
    to_add: PseudoCourse | FillerCourse,
):
    """
    Add a course to the usable courses pool (after doing the appropiate conversions).
    """
    og_course = to_add.course if isinstance(to_add, FillerCourse) else to_add
    code = og_course.code

    if code in g.usable:
        usable = g.usable[code]
    else:
        usable = UsableCourse(
            multiplicity=curriculum.multiplicity_of(courseinfo, code),
            total=0,
            instances=[],
        )
        g.usable[code] = usable
        g.usable_keys.add(code)

    if (
        usable.multiplicity.credits is not None
        and usable.multiplicity.credits < credit_cap
    ):
        credit_cap = usable.multiplicity.credits
    if usable.total >= credit_cap:  # noqa: SIM102 (for clarity)
        # This course is already full
        # If the course we are adding is equivalent to some previous course, just skip
        # it
        # For this to work correctly, fillers must be added after taken courses!
        # (This is an optimization)
        if any(
            previous.original_pseudocourse == og_course
            or (
                isinstance(previous.original_pseudocourse, ConcreteId)
                and previous.original_pseudocourse.equivalence is None
            )
            for previous in usable.instances
        ):
            return

    # Assign 1 ghost credit to 0-credit courses
    # Kind of a hack, but works pretty well
    # The curriculum definition must correspondingly also consider
    # 0-credit courses to have 1 ghost credit
    info = courseinfo.try_course(code)
    if info is not None:
        credits = info.credits or 1
    elif isinstance(og_course, EquivalenceId):
        credits = og_course.credits
    else:
        return

    filler = to_add if isinstance(to_add, FillerCourse) else None
    inst_idx = len(usable.instances)
    usable.instances.append(
        UsableInstance(
            code=code,
            credits=credits,
            filler=filler,
            instance_idx=inst_idx,
            flat_order=flat_order,
            original_pseudocourse=og_course,
            flow=0,
            flow_var=g.model.NumVar(0, credits, ""),
        ),
    )
    usable.total += credits


def _fill_usable(
    courseinfo: CourseInfo,
    taken: list[list[PseudoCourse]],
    curriculum: Curriculum,
    g: SolvedCurriculum,
):
    """
    Iterate through all taken courses and filler courses, and populate `g.usable`.
    Basically, recognize which courses can be used to fill the curriculum slots.
    """

    flat_order = 0
    filler_cap: dict[str, int] = {
        code: sum(courseinfo.get_credits(filler.course) or 0 for filler in fillers)
        for code, fillers in curriculum.fillers.items()
    }
    for sem in taken:
        for c in sorted(sem, key=lambda c: c.code):
            if courseinfo.try_any(c) is None:
                continue
            _add_usable_course(
                courseinfo,
                curriculum,
                g,
                flat_order,
                filler_cap[c.code] if c.code in filler_cap else INFINITY,
                c,
            )
            flat_order += 1
    for code, fillers in curriculum.fillers.items():
        for filler in fillers:
            _add_usable_course(
                courseinfo,
                curriculum,
                g,
                flat_order,
                filler_cap[code],
                filler,
            )
            flat_order += 1


def _build_problem(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    taken_semesters: list[list[PseudoCourse]],
    *,
    tolerance: int = 0,
) -> SolvedCurriculum:
    """
    Take a curriculum prototype and a specific set of taken courses, and build a
    solvable graph that represents this curriculum.
    """

    g = SolvedCurriculum()

    # Fill in credit pool from approved courses and filler credits
    _fill_usable(courseinfo, taken_semesters, curriculum, g)

    # Build curriculum graph from the curriculum tree
    root_flow = _build_visit(courseinfo, g, VisitState(), curriculum.root)

    # Ensure the maximum amount of flow reaches the root
    g.model.Add(
        lmip.LinearConstraint(
            g.model.Sum(root_flow),
            curriculum.root.cap - tolerance,
            curriculum.root.cap,
        ),
    )

    # Apply multiplicity limits
    _enforce_multiplicity(g)

    # Each course instance can only feed one block per layer
    for usable in g.usable.values():
        for inst in usable.instances:
            for layer in inst.layers.values():
                if len(layer.block_edges) <= 1:
                    continue
                g.model.Add(
                    g.model.Sum([edge.active_var for edge in layer.block_edges]) <= 1,
                )

    # Minimize the amount of used course flow
    _minimize_cost(g)

    return g


def _enforce_multiplicity(g: SolvedCurriculum):
    """
    Ensure that each course can only be taken once (or a certain amount of times
    depending on the course).
    """
    seen: set[str] = set()
    for code, usable in g.usable.items():
        if code in seen:
            continue
        seen.add(code)
        max_creds = usable.multiplicity.credits
        group = usable.multiplicity.group

        total_credits = 0
        for ecode in group:
            if ecode in g.usable:
                total_credits += g.usable[ecode].total
        if max_creds is None or total_credits <= max_creds:
            continue
        vars: list[lmip.LinearExpr] = []
        for ecode in group:
            if ecode not in g.usable:
                continue
            for inst in g.usable[ecode].instances:
                vars.append(inst.flow_var)
        g.model.Add(
            g.model.Sum(vars) <= max_creds,
        )


def _minimize_cost(g: SolvedCurriculum):
    """
    Minimize the amount of used credits.
    Not all credits are equal though, some credits represent more cost than others.
    """

    costs: list[lmip.LinearExpr] = []
    for usable in g.usable.values():
        for inst in usable.instances:
            # Consider the cost of using this instance
            # The cost is higher if it is a filler, because it means adding an extra
            # course
            cost_per_credit = (
                TAKEN_COST
                if inst.filler is None
                else FILLER_COST + inst.filler.cost_offset
            )
            costs.append(cost_per_credit * inst.flow_var)
            # Add extra cost for taking recolor-edges
            for edges in inst.layers.values():
                for edge in edges.block_edges:
                    if edge.needs_recolor:
                        costs.append(RECOLOR_COST * edge.flow_var)

    g.model.Minimize(g.model.Sum(costs))


def _tag_edge_flow(g: SolvedCurriculum):
    """
    Update the `used` and `active` flags of all course instances and edges.
    """
    for usable in g.usable.values():
        for inst in usable.instances:
            inst.flow = round(inst.flow_var.SolutionValue())
            for layer in inst.layers.values():
                for edge in layer.block_edges:
                    edge.flow = round(edge.flow_var.SolutionValue())
                    if edge.flow > 0:
                        layer.active_edge = edge


def _get_superblock(
    g: SolvedCurriculum,
    inst: UsableInstance,
) -> str:
    for _layer_id, layer in sorted(inst.layers.items(), key=lambda pair: pair[0]):
        if layer.active_edge is not None:
            # This block edge is active!
            # Use the superblock of the leaf (the last block in the path)
            leaf = layer.active_edge.block_path[-1]
            assert isinstance(leaf, Leaf)
            return leaf.superblock

    # No superblock found
    return ""


def _tag_superblocks(g: SolvedCurriculum):
    # Find superblocks for all codes
    g.superblocks = {}
    for code, usable in g.usable.items():
        # Find the superblock for all course instances with this code
        g.superblocks[code] = [_get_superblock(g, inst) for inst in usable.instances]


_solver_status_to_name: dict[int, str] = {
    lmip.Solver.OPTIMAL: "OPTIMAL",
    lmip.Solver.FEASIBLE: "FEASIBLE",
    lmip.Solver.INFEASIBLE: "INFEASIBLE",
    lmip.Solver.UNBOUNDED: "UNBOUNDED",
    lmip.Solver.ABNORMAL: "ABNORMAL",
    lmip.Solver.MODEL_INVALID: "MODEL_INVALID",
    lmip.Solver.NOT_SOLVED: "NOT_SOLVED",
}


SOLVE_PARAMETERS = lmip.MPSolverParameters()
SOLVE_PARAMETERS.SetDoubleParam(lmip.MPSolverParameters.PRIMAL_TOLERANCE, 1e-3)


def solve_curriculum(
    courseinfo: CourseInfo,
    spec: CurriculumSpec,
    curriculum: Curriculum,
    taken: list[list[PseudoCourse]],
) -> SolvedCurriculum:
    # Take the curriculum blueprint, and produce a graph for this student
    g = _build_problem(courseinfo, curriculum, taken)
    # Solve the integer optimization problem
    solve_status = g.model.Solve(SOLVE_PARAMETERS)
    if not (
        solve_status == lmip.Solver.OPTIMAL or solve_status == lmip.Solver.FEASIBLE
    ):
        if logging.getLogger().getEffectiveLevel() <= logging.DEBUG:
            logging.debug(
                f"solving failed for {spec}: {_solver_status_to_name[solve_status]}",
            )
            logging.debug(f"original graph:\n{g.dump_graphviz_debug(curriculum)}")
            logging.debug("searching for minimum relaxation to make it feasible...")
            tol = "infinite"
            for i in range(1, curriculum.root.cap + 1):
                g = _build_problem(courseinfo, curriculum, taken, tolerance=i)
                solve_status_2 = g.model.Solve(SOLVE_PARAMETERS)
                if (
                    solve_status_2 == lmip.Solver.OPTIMAL
                    or solve_status_2 == lmip.Solver.FEASIBLE
                ):
                    tol = i
                    _tag_edge_flow(g)
                    break
            logging.debug(
                f"solvable with tolerance {tol}:\n{g.dump_graphviz_debug(curriculum)}",
            )
        raise Exception(
            f"failed to solve {spec}: {_solver_status_to_name[solve_status]}",
        )
    # Extract solution from solver
    _tag_edge_flow(g)
    # Determine course superblocks
    _tag_superblocks(g)

    return g


def _find_recolors(g: SolvedCurriculum) -> list[tuple[ClassId, EquivalenceId]]:
    """
    Find the concrete courses that need to be recolored according to `g`.
    """

    recolors: list[tuple[ClassId, EquivalenceId]] = []
    for usable in g.usable.values():
        for inst in usable.instances:
            course = inst.original_pseudocourse
            if not isinstance(course, ConcreteId):
                continue
            if "" in inst.layers:
                edges = inst.layers[""]
                if edges.active_edge is not None and edges.active_edge.needs_recolor:
                    active_block = edges.active_edge.block_path[-1]
                    assert isinstance(active_block, Leaf)
                    credits = (
                        course.equivalence.credits
                        if course.equivalence is not None
                        else edges.active_edge.flow
                    )
                    new_equiv = EquivalenceId(
                        code=active_block.list_code,
                        credits=credits,
                    )
                    recolors.append(
                        (
                            ClassId(code=course.code, instance=inst.instance_idx),
                            new_equiv,
                        ),
                    )
    return recolors


def _resolve_with_fixed_colors(g: SolvedCurriculum) -> bool:
    """
    Resolve the curriculum, this time inflexibly respecting the fixed assignments.
    """

    # Determine how many courses were taken
    old_taken = 0
    old_fillers = 0
    for usable in g.usable.values():
        for inst in usable.instances:
            if inst.filler is None:
                old_taken += inst.flow
            else:
                old_fillers += inst.flow
    # Forbid edges that require reassignment (coloquially called recoloring)
    for usable in g.usable.values():
        for inst in usable.instances:
            for edges in inst.layers.values():
                for edge in edges.block_edges:
                    if edge.needs_recolor:
                        g.model.Add(lmip.LinearConstraint(edge.active_var, 0, 0))
                        g.model.Add(lmip.LinearConstraint(edge.flow_var, 0, 0))
    # Re-solve model
    solve_status = g.model.Solve(SOLVE_PARAMETERS)
    if not (
        solve_status == lmip.Solver.OPTIMAL or solve_status == lmip.Solver.FEASIBLE
    ):
        raise Exception(
            f"failed to re-solve curriculum: {_solver_status_to_name[solve_status]}",
        )
    # Extract solution
    _tag_edge_flow(g)
    # Determine new course superblocks
    _tag_superblocks(g)
    # Determine how many courses are taken now
    new_taken = 0
    new_fillers = 0
    for usable in g.usable.values():
        for inst in usable.instances:
            if inst.filler is None:
                new_taken += inst.flow
            else:
                new_fillers += inst.flow
    # If more courses were taken, then we had to make sacrifices in order to forbid
    # recoloring
    return new_taken > old_taken or new_fillers > old_fillers


def _explore_options_for(
    g: SolvedCurriculum,
    og_inst: UsableInstance,
) -> list[list[PseudoCourse]]:
    # Place the options in here
    opts: list[list[PseudoCourse]] = []
    # Place the variables that will need their upperbounds restored in here
    restore: list[tuple[lmip.Variable, float]] = []

    insts = [og_inst]
    while True:
        # If this option is a filler, include it in the options
        if any(inst.filler for inst in insts):
            opts.append(
                [
                    pseudocourse_with_credits(
                        inst.filler.course,
                        round(inst.flow_var.SolutionValue()),
                    )
                    for inst in insts
                    if inst.filler
                ],
            )

        # Forbid this courses
        # Note that not only the active instances are forbidden, but also all of the
        # instances associated to their courses
        # These prevents duplicate fillers from showing up in the suggestions
        courses = {inst.code for inst in insts}
        for code in courses:
            for inst in g.usable[code].instances:
                restore.append((inst.flow_var, inst.flow_var.Ub()))
                inst.flow_var.SetUb(0)

        # Solve with these new restrictions
        solve_status = g.model.Solve(SOLVE_PARAMETERS)
        if not (
            solve_status == lmip.Solver.OPTIMAL or solve_status == lmip.Solver.FEASIBLE
        ):
            # Could not solve, we ran out of options
            break

        # Find which course(s) were used to fill in the gap
        insts.clear()
        for usable in g.usable.values():
            for inst in usable.instances:
                if round(inst.flow_var.SolutionValue()) > inst.flow:
                    insts.append(inst)
        assert insts

    # Re-enable the killed variables
    for var, ub in restore:
        var.SetUb(ub)

    return opts
