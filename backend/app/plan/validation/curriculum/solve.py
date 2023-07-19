"""
Fill the slots of a curriculum with courses, making sure that there is no overlap
within a block and respecting exclusivity rules.

General program flow when solving a curriculum:
1. A curriculum tree is built from external sources such as SIDING (see
    `sync.siding.translate`).
2. Some hand-written transformations are applied on the tree (see
    `sync.siding.siding_rules`), and the result is a curriculum tree as defined in
    `plan.validation.curriculum.tree`.
    This tree is not yet a graph, but instead is a "blueprint" to build a graph later.
3. When a plan needs to be validated, `solve_curriculum` is called with the taken
    courses and the curriculum tree as arguments.
4. A flow network is built, with each unit of flow representing a single credit. Each
    unit of flow that reaches the flow sink represents a credit in the curriculum.
    Flow can be sourced from a taken course, or from a virtual filler course.
    Filler courses represent courses that have not yet been taken, but *could* be taken.
    While building the network graph, a table is kept that maps from course codes to
    edge IDs in the graph, so that later we can identify which edge represents which
    course.
5. Min-cost-max-flow is run on the flow network.
    Virtual filler courses are given a high cost so that concrete taken courses are
    always preferred.
6. Once `solve_curriculum` returns, other modules like
    `plan.validation.curriculum.diagnose` analyze which edges have flow in them.
    If an edge from a filler course has flow, it means that some block could not be
    satisfied only with taken courses, and the solver had to fall back to filler
    courses.
    In this case, we report an error to the user.
7. When a user's plan is missing a course, sometimes there are several filler courses
    that could plug the hole equally well (or at least similarly well).
    However, the flow algorithm has to choose 1 option, and chooses that option
    arbitrarily.
    In order to determine all of the options that could satisfy a course, we have to
    find cycles in the solved graph.
    The `EquivalentFillerFinder` class helps with this.


The solved network (which is different than the curriculum tree) looks like this:

         course       instance          block
          edge          edge            edge       curriculum-tree edges
infinite -----> course -----> instance -----> leaf ----->  tree   -----> curriculum
 source          node  ----->   nodes  -----> node        nodes...          root

Each edge and node fulfills a different role:
    - Infinite source: The global source of flow (supersource).
    - Course edge: Has the course multiplicity as its edge capacity. This edge limits
    the amount of times a particular course can be coursed and still count towards
    the curriculum.
    - Course node: Distributes available flow for a particular course code within the
    course instances.
    - Instance edge: Limits the amount of credits a single instance can provide, and
    has an associated cost that depends on the particular course instance.
    For example, taken courses have a low cost and filler courses have a high cost.
    - Instance node: Distribute the available flow of an instance across the different
    curriculum blocks that a course can provide.
    - Block edge: Carries the flow between a particular course instance and a
    particular curriculum block that is being fed.
    Note that the specific curriculum blocks that a course can provide does not
    depend only on its course code.
    In particular, concrete courses with an associated equivalence can only count
    towards blocks that accept the equivalence.
    However, the same course with the same code, but tagged with another
    equivalence, would count towards other blocks.
    - Leaf node: Accepts flow from a set of courses, defined by the leaf.
    Called a leaf node because leaves in the curriculum tree are nodes of this type.
    - Tree nodes: The rest of the nodes are part of the structure of the curriculum
    itself.
    These nodes form a tree that eventually ends up in the root node.
    - Root node: The root of the curriculum graph. All flow ends up here. This is
    usually also an infinite sink that accepts all flow.

Note that for optimization some nodes may not physically exist in the flow network.
For example, any node that has one input and one output is useless, and is usually
replaced by a single edge.
In general, any node with one output that has at least as much output capacity as it
has input capacity is useless.
Similarly, any node with one input that has at least as much input capacity as it
has output capacity is useless.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from ortools.sat.python import cp_model as cpsat

from app.plan.course import ConcreteId, EquivalenceId, PseudoCourse
from app.plan.courseinfo import CourseInfo
from app.plan.validation.curriculum.tree import (
    SUPERBLOCK_PREFIX,
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
# Base cost of using a filler course. In contrast with a taken course, filler courses
# are virtual courses that are not actually taken by the user. Instead, filler courses
# serve as a "fallback" when a curriculum can't be filled with taken courses only.
FILLER_COST = 10**6
# Base cost of taking a course. This number should be large enough so that cost offsets
# dont make it more profitable to take an extra course.
TAKEN_COST = 10**3


IntExpr = int | cpsat.LinearExpr


@dataclass
class BlockEdgeInfo:
    """
    Represents an edge from a course instance to a block in the curriculum graph.

    If the edge has flow going through it, it means that the course was assigned to the
    blocks in `block_path`.

    - active_flow: The amount of flow in this course instance - leaf block association.
        If this amount is zero, the association is not made.
        If it is not zero, `flow` amount of credits are being assigned to the
        course-block pair.
    - block_path: The curriculum block that is connected to receive the flow through
        this edge.
        The first element is the root, the last element is the leaf and there is any
        number of elements in between.
    """

    block_path: tuple[Block, ...]

    active: bool
    active_var: cpsat.IntVar


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

    used: bool
    used_var: cpsat.IntVar
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
    model: cpsat.CpModel
    # Taken courses (and filler courses).
    usable: dict[str, UsableCourse]
    # Taken course codes.
    # The keys of `usable`.
    usable_keys: set[str]
    # Indicates the main superblock that each course counts towards.
    superblocks: dict[str, list[str]]

    def __init__(self) -> None:
        self.model = cpsat.CpModel()
        self.usable = {}
        self.usable_keys = set()
        self.superblocks = {}
        self.mapping = {}

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
) -> cpsat.IntVar:
    """
    Connect the course instance `inst` to the graph node `connect_to`.
    Creates a minimal amount of nodes and edges to model the connection in the graph.
    """

    # TODO: Per-edge cost

    # Indicates whether the course counts towards the block
    active_var = g.model.NewBoolVar("")

    # The course instance must be used for this edge to be active
    g.model.AddImplication(active_var, inst.used_var)

    # There can only be flow if active is true
    flow_var = g.model.NewIntVar(0, inst.credits, "")
    # flow <= active * credits
    g.model.AddLinearConstraint(active_var * inst.credits - flow_var, 0, inst.credits)

    layer = inst.layers[layer_id]
    layer.block_edges.append(
        BlockEdgeInfo(
            block_path=block_path,
            active=False,
            active_var=active_var,
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
) -> list[cpsat.IntVar]:
    """
    Recursively visit a block of the curriculum tree, building it as we go.
    Connect all of the children, and then connect this node to `connect_to`.
    """
    visit_state.stack.append(block)

    if isinstance(block, Leaf):
        # A list of courses
        visit_state.flat_order += 1

        in_flows: list[cpsat.IntVar] = []
        max_in_flow = 0
        block_path = tuple(visit_state.stack)
        for code in block.codes.intersection(g.usable_keys):
            for inst in g.usable[code].instances:
                if (
                    block.layer == ""
                    and isinstance(inst.original_pseudocourse, ConcreteId)
                    and inst.original_pseudocourse.equivalence is not None
                    and inst.original_pseudocourse.equivalence.code not in block.codes
                ):
                    # Skips instances with mismatching tagged equivalence
                    continue
                child_flow = _connect_course_instance(
                    courseinfo,
                    g,
                    block.layer,
                    visit_state.flat_order,
                    block_path,
                    inst,
                )
                in_flows.append(child_flow)
                max_in_flow += inst.credits
    else:
        # A combination of blocks
        max_in_flow = 0
        in_flows: list[cpsat.IntVar] = []
        for c in block.children:
            child_flow = _build_visit(courseinfo, g, visit_state, c)
            in_flows.extend(child_flow)
            max_in_flow += c.cap

    visit_state.stack.pop()

    out_flows = in_flows
    if max_in_flow > block.cap:
        out_flow = g.model.NewIntVar(0, block.cap, "")
        # out_flow <= in_flow
        g.model.AddLinearConstraint(
            cpsat.LinearExpr.Sum(in_flows) - out_flow,
            0,
            max_in_flow,
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
            used=False,
            used_var=g.model.NewBoolVar(""),
        ),
    )
    usable.total += credits


def _build_problem(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    taken_semesters: list[list[PseudoCourse]],
    tolerance: int = 0,
) -> SolvedCurriculum:
    """
    Take a curriculum prototype and a specific set of taken courses, and build a
    solvable graph that represents this curriculum.
    """

    g = SolvedCurriculum()

    # Fill in credit pool from approved courses and filler credits
    flat_order = 0
    filler_cap: dict[str, int] = {
        code: sum(courseinfo.get_credits(filler.course) or 0 for filler in fillers)
        for code, fillers in curriculum.fillers.items()
    }
    for sem in taken_semesters:
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

    # Build curriculum graph from the curriculum tree
    root_flow = _build_visit(courseinfo, g, VisitState(), curriculum.root)

    # Ensure the maximum amount of flow reaches the root
    g.model.AddLinearConstraint(
        cpsat.LinearExpr.Sum(root_flow),
        curriculum.root.cap - tolerance,
        curriculum.root.cap,
    )

    # Apply multiplicity limits
    # Each course can only be taken once (or, a certain number of times)
    seen: set[str] = set()
    for code, usable in g.usable.items():
        if code in seen:
            continue
        seen.add(code)
        max_creds = usable.multiplicity.credits
        group = usable.multiplicity.group

        total_credits = sum(g.usable[ecode].total for ecode in group)
        if max_creds is None or total_credits <= max_creds:
            continue
        vars = [inst.used_var for ecode in group for inst in g.usable[ecode].instances]
        coeffs = [inst.credits for ecode in group for inst in g.usable[ecode].instances]
        g.model.AddLinearConstraint(
            cpsat.LinearExpr.WeightedSum(vars, coeffs),
            0,
            max_creds,
        )

    # Each course instance can only feed one block per layer
    for usable in g.usable.values():
        for inst in usable.instances:
            for layer in inst.layers.values():
                if len(layer.block_edges) <= 1:
                    continue
                g.model.AddAtMostOne(edge.active_var for edge in layer.block_edges)

    # Minimize the amount of used courses
    vars: list[cpsat.IntVar] = []
    coeffs: list[int] = []
    for usable in g.usable.values():
        for inst in usable.instances:
            vars.append(inst.used_var)
            coeffs.append(
                TAKEN_COST
                if inst.filler is None
                else FILLER_COST + inst.filler.cost_offset,
            )
    g.model.Minimize(cpsat.LinearExpr.WeightedSum(vars, coeffs))

    return g


def _tag_edge_flow(solver: cpsat.CpSolver, g: SolvedCurriculum):
    """
    Update the `used` and `active` flags of all course instances and edges.
    """
    for usable in g.usable.values():
        for inst in usable.instances:
            inst.used = solver.BooleanValue(inst.used_var)
            for layer in inst.layers.values():
                for edge in layer.block_edges:
                    edge.active = solver.BooleanValue(edge.active_var)
                    if edge.active:
                        layer.active_edge = edge


def _get_superblock(
    g: SolvedCurriculum,
    inst: UsableInstance,
) -> str:
    for _layer_id, layer in sorted(inst.layers.items(), key=lambda pair: pair[0]):
        if layer.active_edge is not None:
            # This block edge is active!
            # Use the first superblock block in the path
            for block in layer.active_edge.block_path:
                if block.block_code.startswith(SUPERBLOCK_PREFIX):
                    return block.block_code[len(SUPERBLOCK_PREFIX) :]

    # No superblock found
    return ""


def _tag_superblocks(g: SolvedCurriculum):
    # Find superblocks for all codes
    g.superblocks = {}
    for code, usable in g.usable.items():
        # Find the superblock for all course instances with this code
        g.superblocks[code] = [_get_superblock(g, inst) for inst in usable.instances]


solver = cpsat.CpSolver()
solver.parameters.num_workers = 1  # type: ignore


def solve_curriculum(
    courseinfo: CourseInfo,
    spec: CurriculumSpec,
    curriculum: Curriculum,
    taken: list[list[PseudoCourse]],
) -> SolvedCurriculum:
    # Take the curriculum blueprint, and produce a graph for this student
    g = _build_problem(courseinfo, curriculum, taken)
    # Solve the integer optimization problem
    solve_status = solver.Solve(g.model)
    if not (solve_status == cpsat.OPTIMAL or solve_status == cpsat.FEASIBLE):
        if logging.getLogger().getEffectiveLevel() <= logging.DEBUG:
            logging.debug(f"solving failed for {spec}: {solver.StatusName()}")
            logging.debug(f"original graph:\n{g.dump_graphviz_debug(curriculum)}")
            logging.debug("searching for minimum relaxation to make it feasible...")
            tol = "infinite"
            for i in range(curriculum.root.cap):
                g = _build_problem(courseinfo, curriculum, taken, tolerance=i + 1)
                solve_status_2 = solver.Solve(g.model)
                if solve_status_2 == cpsat.OPTIMAL or solve_status_2 == cpsat.FEASIBLE:
                    tol = i
                    _tag_edge_flow(solver, g)
                    break
            logging.debug(
                f"solvable with tolerance {tol}:\n{g.dump_graphviz_debug(curriculum)}",
            )
        raise Exception(
            f"failed to solve curriculum {spec}: {solver.StatusName()}",
        )
    # Extract solution from solver
    _tag_edge_flow(solver, g)
    # Determine course superblocks
    _tag_superblocks(g)

    return g
