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

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from ortools.sat.python import cp_model as cpsat

from ...course import ConcreteId, EquivalenceId, PseudoCourse
from ...courseinfo import CourseInfo
from .tree import SUPERBLOCK_PREFIX, Block, Curriculum, FillerCourse, Leaf

# Infinite placeholder.
# A huge value that still fits in a 64-bit integer.
INFINITY: int = 10**18
# Base cost of using a filler course. In contrast with a taken course, filler courses
# are virtual courses that are not actually taken by the user. Instead, filler courses
# serve as a "fallback" when a curriculum can't be filled with taken courses only.
FILLER_COST = 10**6
# Offset the cost of course-block edges by the order in which blocks are defined.
BLOCK_ORDER_COST = 10**3
# Offset the cost of course-block edges by the order in which courses appear in the
# plan.
COURSE_ORDER_COST = 10**0

# Up to what cost is still considered "small" when considering filler equivalents.
EQUIVALENT_FILLER_THRESHOLD = 10**5


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
    multiplicity: int | None
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
    # Indicates the main superblock that each course counts towards.
    superblocks: dict[str, list[str]]
    # Maps from original (code, repeat index) to curriculum (code, repeat index).
    mapping: dict[str, list[tuple[str, int]]]

    def __init__(self) -> None:
        self.model = cpsat.CpModel()
        self.usable = {}
        self.superblocks = {}
        self.mapping = {}

    def map_class_id(self, code: str, rep_idx: int) -> tuple[str, int] | None:
        """
        Given a class id in the original plan, get a class id in the internal plan.
        This does things like mapping courses to their equivalents.
        """
        if code not in self.mapping:
            return None
        if rep_idx >= len(self.mapping[code]) or rep_idx < 0:
            return None
        return self.mapping[code][rep_idx]

    def dump_graphviz_pretty(self, curr: Curriculum) -> str:
        """
        Dumps a graph resembling the original curriculum.
        """
        out = "digraph {\n"
        next_id = 1

        by_block: defaultdict[
            str,
            defaultdict[int, list[tuple[UsableInstance, BlockEdgeInfo]]],
        ] = defaultdict(lambda: defaultdict(list))
        for usable in self.usable.values():
            for inst in usable.instances:
                for layer_id, layer in inst.layers.items():
                    for edge in layer.block_edges:
                        bid = id(edge.block_path[-1])
                        by_block[layer_id][bid].append(
                            (inst, edge),
                        )

        def attach_course(
            layer_id: str,
            code: str,
            attach_to: str,
            flow: int,
            cap: int,
            is_filler: bool,
        ) -> int:
            if cap == 0 or (is_filler and flow == 0):
                return 0

            nonlocal out, next_id
            vid = f"v{next_id}"
            next_id += 1

            style = " style=dotted" if flow == 0 else ""
            style += ' color="red"' if is_filler else ""

            label = code
            if layer_id != "":
                label += f"[{layer_id}]"
            label += "\\n(faltante)" if is_filler else ""
            out += f'{vid} [label="{label}"{style}]\n'

            label = f"{0 if is_filler else flow}/{cap}"
            out += f'{vid} -> {attach_to} [label="{label}"{style}]\n'

            return flow

        def visit(block: Block) -> tuple[str, int]:
            nonlocal out, next_id
            vid = f"v{next_id}"
            next_id += 1

            flow = 0
            if isinstance(block, Leaf):
                for layer_id, layer in by_block.items():
                    if id(block) not in layer:
                        continue
                    for inst, edge in layer[id(block)]:
                        subflow = attach_course(
                            layer_id,
                            inst.code,
                            vid,
                            inst.credits if edge.active else 0,
                            inst.credits,
                            inst.filler is not None,
                        )

                        flow += subflow
                        next_id += 1
            else:
                for child in block.children:
                    subid, subflow = visit(child)
                    flow += subflow
                    sublabel = f"{subflow}/{child.cap}"
                    style = "" if subflow > 0 else " style=dotted"
                    out += f'{subid} -> {vid} [label="{sublabel}"{style}]\n'
            label = block.debug_name
            out += f'{vid} [label="{label}"]\n'

            return vid, flow

        vid, flow = visit(curr.root)
        out += f'v{next_id} [label=""]\n'
        out += f'{vid} -> v{next_id} [label="{flow}/{curr.root.cap}"]'
        out += "}"
        return out

    def dump_graphviz_debug(self, curriculum: Curriculum) -> str:  # noqa: C901 (debug)
        """
        Dump the graph representation as a Graphviz DOT file.
        """
        out = "digraph {\n"
        id_counter = 0

        def next_id():
            nonlocal id_counter
            id_counter += 1
            return f"v{id_counter}"

        def mknode(label: str, extra: str = "", id: str | None = None):
            nonlocal out
            if id is None:
                id = next_id()
            out += f'{id} [label="{label}" {extra}]\n'
            return id

        def mkedge(
            src: str,
            dst: str,
            label: str,
            extra: str = "",
            dotted_flow: int | None = None,
        ):
            nonlocal out
            if dotted_flow == 0:
                extra += " style=dotted"
            extra = extra.strip()
            if extra:
                extra = " " + extra
            out += f'{src} -> {dst} [label="{label}"{extra}]\n'

        by_block: defaultdict[
            str,
            defaultdict[
                int,
                list[tuple[UsableInstance, InstanceEdges, BlockEdgeInfo]],
            ],
        ] = defaultdict(lambda: defaultdict(list))
        for usable in self.usable.values():
            for inst in usable.instances:
                for layer_id, layer in inst.layers.items():
                    for edge in layer.block_edges:
                        bid = id(edge.block_path[-1])
                        by_block[layer_id][bid].append(
                            (inst, layer, edge),
                        )

        def visit(block: Block) -> tuple[str, int]:
            vid = mknode(f"{block.debug_name}")

            flow = 0
            if isinstance(block, Leaf):
                for layer_id, byblock in by_block.items():
                    if id(block) not in byblock:
                        continue
                    courseids: dict[str, str] = {}
                    for inst, layer, edge in byblock[id(block)]:
                        code = inst.code
                        if code not in courseids:
                            usable = self.usable[code]
                            lname = f"[{layer_id}]" if layer_id else ""
                            mult = (
                                "inf"
                                if usable.multiplicity is None
                                else usable.multiplicity
                            )
                            courseids[code] = mknode(
                                f"{code}{lname} {usable.total}/{mult}",
                            )

                        total_inst_flow = 0
                        for block_edge in layer.block_edges:
                            total_inst_flow += inst.credits if block_edge.active else 0

                        label = f"{code} #{inst.instance_idx+1}"
                        style = ""
                        if inst.filler is not None:
                            label += "\n(faltante)"
                            style = "color=red"
                        inst_id = mknode(label, style)
                        mkedge(
                            courseids[code],
                            inst_id,
                            f"{total_inst_flow}/{inst.credits}",
                            dotted_flow=total_inst_flow,
                        )

                        mkedge(
                            inst_id,
                            vid,
                            f"{inst.credits if edge.active else 0}/{inst.credits}",
                            dotted_flow=inst.credits if edge.active else 0,
                        )

                        flow += inst.credits if edge.active else 0
            else:
                for child in block.children:
                    subid, subflow = visit(child)
                    flow += subflow
                    mkedge(
                        subid,
                        vid,
                        f"{subflow}/{child.cap}",
                        dotted_flow=subflow,
                    )

            return vid, flow

        vid, flow = visit(curriculum.root)
        sink = mknode("")
        mkedge(vid, sink, f"{flow}/{curriculum.root.cap}", dotted_flow=flow)
        out += "}"
        return out

    def dump_graphviz_raw(self, curriculum: Curriculum | None = None) -> str:
        """
        Dump the raw graphviz representation using node and edge indices instead of
        names.
        """
        out = "digraph {\n"
        for id, node in enumerate(self.nodes):
            label = f"v{id}"
            if id == self.source:
                label += "(s)"
            elif id == self.sink:
                label += "(t)"
            label += f" {node.debug_name}"
            out += f'  v{id} [label="{label}"];\n'
        for id, edge in enumerate(self.edges):
            if edge.cap == 0:
                continue
            rev = self.edges[edge.rev]
            assert rev.flow == -edge.flow and rev.cap == 0 and rev.cost == -edge.cost
            label = f"e{id} {edge.flow}/{edge.cap}"
            if edge.cost != 0:
                label += f" ${edge.cost}"
            attrs = f'label="{label}"'
            if edge.flow == 0:
                attrs += " style=dotted"
            out += f"  v{edge.src} -> v{edge.dst} [{attrs}];\n"
        out += '  ssink [label=""];\n'
        sink_flow = self.nodes[self.sink].flow(self)
        sink_cap = "?" if curriculum is None else curriculum.root.cap
        out += f'  v{self.sink} -> ssink [label="{sink_flow}/{sink_cap}"];\n'
        out += "}"
        return out


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

    name = f"{inst.code} #{inst.instance_idx+1} -> {block_path[-1].block_code}"

    # Indicates whether the course counts towards the block
    active_var = g.model.NewBoolVar(f"{name} [bool]")

    # The course instance must be used for this edge to be active
    g.model.AddImplication(active_var, inst.used_var)

    # There can only be flow if active is true
    flow_var = g.model.NewIntVar(0, inst.credits, name)
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


def _taken_block_courses_iter(
    g: SolvedCurriculum,
    block: Leaf,
) -> Iterable[UsableInstance]:
    """
    Iterate over the course instances whose codes match the given block.
    The instances are given in an arbitrary order.
    """
    if len(block.codes) < len(g.usable):
        # This block has little codes, iterate over the block codes
        return (
            inst
            for code in block.codes
            if code in g.usable
            for inst in g.usable[code].instances
            if not (
                # Skips instances with mismatching tagged equivalence
                block.layer == ""
                and isinstance(inst.original_pseudocourse, ConcreteId)
                and inst.original_pseudocourse.equivalence is not None
                and inst.original_pseudocourse.equivalence.code not in block.codes
            )
        )
    # This block has too many codes.
    # Iterate over the taken courses instead
    return (
        inst
        for code, usable in g.usable.items()
        if code in block.codes
        for inst in usable.instances
        if not (
            # Skips instances with mismatching tagged equivalence
            block.layer == ""
            and isinstance(inst.original_pseudocourse, ConcreteId)
            and inst.original_pseudocourse.equivalence is not None
            and inst.original_pseudocourse.equivalence.code not in block.codes
        )
    )


@dataclass
class VisitState:
    stack: list[Block] = field(default_factory=list)
    flat_order: int = 0


def _build_visit(
    courseinfo: CourseInfo,
    g: SolvedCurriculum,
    visit_state: VisitState,
    block: Block,
) -> cpsat.IntVar:
    """
    Recursively visit a block of the curriculum tree, building it as we go.
    Connect all of the children, and then connect this node to `connect_to`.
    """
    visit_state.stack.append(block)

    if isinstance(block, Leaf):
        # A list of courses
        visit_state.flat_order += 1

        in_flow: IntExpr = 0
        max_in_flow = 0
        block_path = tuple(visit_state.stack)
        for inst in _taken_block_courses_iter(g, block):
            child_flow = _connect_course_instance(
                courseinfo,
                g,
                block.layer,
                visit_state.flat_order,
                block_path,
                inst,
            )
            in_flow += child_flow
            max_in_flow += inst.credits
    else:
        # A combination of blocks
        max_in_flow = 0
        in_flow: IntExpr = 0
        for c in block.children:
            child_flow = _build_visit(courseinfo, g, visit_state, c)
            in_flow += child_flow
            max_in_flow += c.cap

    visit_state.stack.pop()

    out_flow = g.model.NewIntVar(0, block.cap, block.block_code)
    # out_flow <= in_flow
    g.model.AddLinearConstraint(in_flow - out_flow, 0, max_in_flow)

    return out_flow


def _add_usable_course(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    g: SolvedCurriculum,
    flat_order: int,
    to_add: PseudoCourse | FillerCourse,
):
    """
    Add a course to the usable courses pool (after doing the appropiate conversions).
    """
    og_course = to_add.course if isinstance(to_add, FillerCourse) else to_add
    code = og_course.code

    # Map curriculum equivalencies
    if code in curriculum.equivalencies:
        code = curriculum.equivalencies[code]

    if code in g.usable:
        usable = g.usable[code]
    else:
        usable = UsableCourse(
            multiplicity=curriculum.multiplicity_of(courseinfo, code),
            total=0,
            instances=[],
        )
        g.usable[code] = usable

    if (  # noqa: SIM102 (for clarity)
        usable.multiplicity and usable.total >= usable.multiplicity
    ):
        # This course is already full
        # If the course we are adding is equivalent to some previous course, just skip
        # it
        # For this to work correctly, fillers must be added after taken courses!
        if any(
            previous.original_pseudocourse == og_course for previous in usable.instances
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
            used_var=g.model.NewBoolVar(f"{code} #{inst_idx+1}"),
        ),
    )
    usable.total += credits

    g.mapping.setdefault(og_course.code, []).append((code, inst_idx))


def _build_problem(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    taken_semesters: list[list[PseudoCourse]],
) -> SolvedCurriculum:
    """
    Take a curriculum prototype and a specific set of taken courses, and build a
    solvable graph that represents this curriculum.
    """

    g = SolvedCurriculum()

    # Fill in credit pool from approved courses and filler credits
    flat_order = 0
    for sem in taken_semesters:
        for c in sorted(sem, key=lambda c: c.code):
            if courseinfo.try_any(c) is None:
                continue
            _add_usable_course(courseinfo, curriculum, g, flat_order, c)
            flat_order += 1
    for fillers in curriculum.fillers.values():
        for filler in fillers:
            _add_usable_course(courseinfo, curriculum, g, flat_order, filler)
            flat_order += 1

    # Build curriculum graph from the curriculum tree
    root_flow = _build_visit(courseinfo, g, VisitState(), curriculum.root)

    # Ensure the maximum amount of flow reaches the root
    g.model.AddLinearConstraint(
        root_flow,
        curriculum.root.cap,
        curriculum.root.cap,
    )

    # Apply multiplicity limits
    # Each course can only be taken once (or, a certain number of times)
    for usable in g.usable.values():
        if not usable.multiplicity or usable.total <= usable.multiplicity:
            continue
        course_flow: IntExpr = 0
        for inst in usable.instances:
            course_flow += inst.used_var * inst.credits
        g.model.AddLinearConstraint(course_flow, 0, usable.multiplicity)

    # Each course instance can only feed one block per layer
    for usable in g.usable.values():
        for inst in usable.instances:
            for layer in inst.layers.values():
                if len(layer.block_edges) <= 1:
                    continue
                g.model.AddAtMostOne(edge.active_var for edge in layer.block_edges)

    # Minimize the amount of used courses
    cost: IntExpr = 0
    for usable in g.usable.values():
        for inst in usable.instances:
            cost += inst.used_var * (1 if inst.filler is None else 1000)
    g.model.Minimize(cost)

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
    curriculum: Curriculum,
    taken: list[list[PseudoCourse]],
) -> SolvedCurriculum:
    # Take the curriculum blueprint, and produce a graph for this student
    g = _build_problem(courseinfo, curriculum, taken)
    # Solve the integer optimization problem
    solve_status = solver.Solve(g.model)
    if not (solve_status == cpsat.OPTIMAL or solve_status == cpsat.FEASIBLE):
        dbg = f"\n{g.dump_graphviz_debug(curriculum)}"
        raise Exception(
            f"failed to solve curriculum: {solver.StatusName()}{dbg}",
        )
    # Extract solution from solver
    _tag_edge_flow(solver, g)
    # Determine course superblocks
    _tag_superblocks(g)
    return g
