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
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ...course import ConcreteId, EquivalenceId, PseudoCourse
from ...courseinfo import CourseInfo
from .tree import SUPERBLOCK_PREFIX, Block, Curriculum, FillerCourse, Leaf

# Cost of using a taken course.
TAKEN_COST = 10**1
# Cost of using a filler course. In contrast with a taken course, filler courses are
# virtual courses that are not actually taken by the user. Instead, filler courses serve
# as a "fallback" when a curriculum can't be filled with taken courses.
FILLER_COST = 10**4
# Infinite placeholder.
# A huge value that still fits in a 64-bit integer.
INFINITY: int = 10**18

# Up to what cost is still considered "small" when considering filler equivalents.
EQUIVALENT_FILLER_THRESHOLD = 10**3


@dataclass
class Edge:
    """
    Represents an edge in the curriculum graph.
    """

    debug_name: str
    id: int
    cap: int
    flow: int
    src: int
    dst: int
    rev: int
    cost: int = 0


@dataclass
class Node:
    """
    Represents a node in the curriculum graph.
    """

    debug_name: str
    outgoing: set[int] = field(default_factory=set)
    incoming: set[int] = field(default_factory=set)
    outgoing_active: set[int] = field(default_factory=set)

    def flow(self, g: "SolvedCurriculum") -> int:
        f = 0
        for edgeid in self.incoming:
            edge = g.edges[edgeid]
            if edge.flow >= 0:
                f += edge.flow
        return f

    def cap(self, g: "SolvedCurriculum") -> int:
        c = 0
        for edgeid in self.outgoing:
            edge = g.edges[edgeid]
            c += edge.cap
        return c

    def incoming_cap(self, g: "SolvedCurriculum") -> int:
        c = 0
        for edgeid in self.incoming:
            edge = g.edges[edgeid]
            c += edge.cap
        return c


@dataclass
class BlockEdgeInfo:
    """
    Represents an edge from a course to a block in the curriculum graph.

    If the edge has flow going through it, it means that the course was assigned to the
    blocks in `block_path`.
    """

    edge_id: int
    block_path: tuple[Block, ...]
    taken_flow: int = 0
    filler_flow: int = 0


@dataclass
class CourseInLayer:
    """
    Contains the data that relates a particular course code with the edges and nodes in
    the graph that represent it.
    The most general representation of a course in the graph looks like this:

          low cost course-edge: capacity = taken credits
        +----------------------+
        |                      |          block-edges
        |                      v       -----------------> block 1
    infinite                 course    -----------------> block 2
     source                   node     -----------------> ...
        |                      ^       -----------------> block n
        |                      |
        +----------------------+
          high cost course-edge: capacity = multiplicity - taken credits

    Remember that multiplicity is the maximum amount of credits of the same course that
    can be taken.
    The idea is that the solver always prefers the low cost edge (with low capacity), so
    the high cost edge is a "fallback" when that capacity isn't enough.

    Note that for optimization purposes sometimes the low or high cost edge might not
    exist, or the course node might not exist and the low/high cost edges connect
    directly to a block (only if there is only 1 block).

    TODO: Use a source -> per-code multiplicity limiter -> course instance -> block
    scheme instead of source -> per-code node -> block.
    """

    # The ID of the low-cost-taken course edge.
    # Might be `None` if there is no taken course.
    low_edge: int | None = None
    # The ID of the high-cost-filler course edge.
    # Might be `None` if the user already took the maximum amount of credits.
    high_edge: int | None = None
    # The ID of the intermediate course node.
    # Might be `None` if there is a single block connected to this course.
    course_node: int | None = None

    # All of the block edges associated to this course.
    block_edges: list[BlockEdgeInfo] = field(default_factory=list)
    # The active edge associated to each taken course.
    active_taken_edges: list[tuple[BlockEdgeInfo, int] | None] = field(
        default_factory=list,
    )
    # The active edge associated to each filler course.
    active_filler_edges: list[tuple[BlockEdgeInfo, int] | None] = field(
        default_factory=list,
    )


@dataclass
class LayerCourses:
    """
    Links courses with graph edges (for a particular layer).
    Information about course matching can be extracted from here.
    """

    # Contains an entry for each course code.
    courses: defaultdict[str, CourseInLayer] = field(
        default_factory=lambda: defaultdict(CourseInLayer),
    )


@dataclass
class UsableCourse:
    """
    Contains information about how many credits of a particular course were taken by the
    user, and how many are available as fillers.
    """

    # The amount of taken credits of the course.
    # This amount is forcefully limited to the multiplicity of the course!
    taken: int
    # The amount of available filler credits of the course.
    # `taken + filler` is forcefully limited to the multiplicity of the course!
    filler: int
    # The concrete list of taken courses making up the taken credit pool.
    taken_list: list[PseudoCourse]
    # The list of filler courses making up the filler credit pool.
    filler_list: list[FillerCourse]
    # Each course is associated to the first time it was taken in the plan.
    # This value is a number such that sorting usable courses by it sorts courses by the
    # first time they appear in the plan.
    flat_order: int


class SolvedCurriculum:
    """
    Context necessary to solve a curriculum.
    Also holds the results of the solving process (hence the name).
    """

    # List of nodes.
    # The ID of each node is its index in this list.
    nodes: list[Node]
    # Flat list of edges.
    edges: list[Edge]
    # The id of the universal source
    source: int
    # The id of the universal sink
    sink: int
    # Maps courses to the graph structure that represents them.
    layers: defaultdict[str, LayerCourses]
    # Taken courses (and filler courses).
    usable: dict[str, UsableCourse]
    # Indicates the main superblock that each course counts towards.
    superblocks: dict[str, list[str]]
    # Maps from original (code, repeat index) to curriculum (code, repeat index).
    mapping: dict[str, list[tuple[str, int]]]

    def __init__(self) -> None:
        self.nodes = [Node(debug_name="source"), Node(debug_name="sink")]
        self.edges = []
        self.source = 0
        self.sink = 1
        self.layers = defaultdict(LayerCourses)
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

    def add(self, node: Node) -> int:
        """
        Add a node to the graph, returning its id.
        """

        id = len(self.nodes)
        self.nodes.append(node)
        return id

    def connect(
        self,
        debug_name: str,
        src_id: int,
        dst_id: int,
        cap: int,
        cost: int = 0,
    ) -> int:
        """
        Connect two nodes in the graph.
        Returns the edge id.
        """

        src = self.nodes[src_id]
        dst = self.nodes[dst_id]
        fw_id = len(self.edges)
        bk_id = len(self.edges) + 1
        edge_fw = Edge(
            debug_name=debug_name,
            id=fw_id,
            cap=cap,
            flow=0,
            src=src_id,
            dst=dst_id,
            rev=bk_id,
            cost=cost,
        )
        edge_rev = Edge(
            debug_name=f"-{debug_name}",
            id=bk_id,
            cap=0,
            flow=0,
            src=dst_id,
            dst=src_id,
            rev=fw_id,
            cost=-cost,
        )
        src.outgoing.add(fw_id)
        src.outgoing_active.add(fw_id)
        dst.incoming.add(fw_id)
        dst.outgoing.add(bk_id)
        src.incoming.add(bk_id)
        self.edges.append(edge_fw)
        self.edges.append(edge_rev)
        return fw_id

    def move_source(self, edgeid: int, new_src_id: int):
        """
        Change the source node of an edge.
        """
        edge = self.edges[edgeid]
        old_src = self.nodes[edge.src]
        new_src = self.nodes[new_src_id]
        rev_id = edge.rev

        edge.src = new_src_id
        old_src.outgoing.remove(edgeid)
        new_src.outgoing.add(edgeid)
        if edgeid in old_src.outgoing_active:
            old_src.outgoing_active.remove(edgeid)
            new_src.outgoing_active.add(edgeid)

        self.edges[rev_id].dst = new_src_id
        old_src.incoming.remove(rev_id)
        new_src.incoming.add(rev_id)

    def dump_graphviz_pretty(self, curr: Curriculum) -> str:
        """
        Dumps a graph resembling the original curriculum.
        """
        out = "digraph {\n"
        next_id = 1

        by_block: defaultdict[
            str,
            defaultdict[int, list[tuple[str, BlockEdgeInfo]]],
        ] = defaultdict(lambda: defaultdict(list))
        for layer_id, layer in self.layers.items():
            for code, layercourse in layer.courses.items():
                for block_edge in layercourse.block_edges:
                    bid = id(block_edge.block_path[-1])
                    by_block[layer_id][bid].append((code, block_edge))

        def attach_course(
            layer_id: str,
            code: str,
            attach_to: str,
            flow: int,
            cap: int,
            is_filler: bool,
        ):
            if cap == 0 or (is_filler and flow == 0):
                return

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

        def visit(block: Block) -> tuple[str, int]:
            nonlocal out, next_id
            vid = f"v{next_id}"
            next_id += 1

            flow = 0
            if isinstance(block, Leaf):
                for layer_id, layer in by_block.items():
                    if id(block) not in layer:
                        continue
                    for code, edge in layer[id(block)]:
                        usable = self.usable[code]
                        attach_course(
                            layer_id,
                            code,
                            vid,
                            edge.taken_flow,
                            usable.taken,
                            False,
                        )
                        attach_course(
                            layer_id,
                            code,
                            vid,
                            edge.filler_flow,
                            usable.filler,
                            True,
                        )

                        flow += edge.taken_flow + edge.filler_flow
                        next_id += 1
            else:
                for child in block.children:
                    subid, subflow = visit(child)
                    flow += subflow
                    sublabel = f"{subflow}/{child.cap}"
                    out += f'{subid} -> {vid} [label="{sublabel}"]\n'
            label = block.debug_name
            out += f'{vid} [label="{label}"]\n'

            return vid, flow

        vid, flow = visit(curr.root)
        out += f'v{next_id} [label=""]\n'
        out += f'{vid} -> v{next_id} [label="{flow}/{curr.root.cap}"]'
        out += "}"
        return out

    def dump_graphviz_true(self) -> str:
        """
        Dump the graph representation as a Graphviz DOT file.
        """
        out = "digraph {\n"
        for id, node in enumerate(self.nodes):
            if id == self.source:
                continue
            label = node.debug_name
            out += f'  v{id} [label="{label}"];\n'
        for id, node in enumerate(self.nodes):
            if id == self.source:
                continue
            has_source = False
            for edgeid in node.incoming:
                edge = self.edges[edgeid]
                if edge.src == self.source:
                    has_source = True
            if has_source:
                out += f'  s{id} [label="source" style=dotted];\n'
        for edge in self.edges:
            if edge.cap == 0:
                continue
            srcid = f"s{edge.dst}" if edge.src == self.source else f"v{edge.src}"
            label = f"{edge.flow}/{edge.cap}"
            if edge.debug_name != "":
                label = f"{edge.debug_name}\n{label}"
            if edge.cost != 0:
                label += f" (${edge.cost})"
            attrs = f'label="{label}"'
            if edge.flow == 0:
                attrs += " style=dotted"
            out += f"  {srcid} -> v{edge.dst} [{attrs}];\n"
        out += "}"
        return out

    def dump_graphviz_raw(self, node_labels: list[Any] | None = None) -> str:
        """
        Dump the raw graphviz representation using node and edge indices instead of
        names.
        """
        out = "digraph {\n"
        for id, _node in enumerate(self.nodes):
            label = f"v{id}"
            if id == self.source:
                label += "(s)"
            elif id == self.sink:
                label += "(t)"
            if node_labels is not None:
                label += f" {node_labels[id]}"
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
        out += "}"
        return out


def _connect_course(
    courseinfo: CourseInfo,
    g: SolvedCurriculum,
    layer_id: str,
    code: str,
    usable: UsableCourse,
    block_path: tuple[Block, ...],
    connect_to: int,
):
    """
    Create or look up the node corresponding to course `c` and connect it to the node
    `connect_to`.
    """

    ancestors = "\n-> ".join(b.debug_name for b in block_path)
    full_name = f"{ancestors}\n-> {code}"
    short_name = code
    if layer_id != "":
        full_name = f"{full_name} ({layer_id})"
        short_name = f"{short_name}({layer_id})"

    layercourse = g.layers[layer_id].courses[code]
    credits = usable.taken + usable.filler
    if len(layercourse.block_edges) == 0 and (usable.taken == 0 or usable.filler == 0):
        # This is the first time we see this course
        # We also only need to add one edge, so instead of building something like the
        # following:
        # source --> course --> block
        # Skip 1 node and build the following:
        # source --> block
        cost = TAKEN_COST if usable.filler == 0 else FILLER_COST
        last_block = block_path[-1]
        cost += last_block.cost if isinstance(last_block, Leaf) else 0
        edge_id = g.connect(
            full_name,
            g.source,
            connect_to,
            credits,
            cost,
        )
        if usable.filler == 0:
            layercourse.low_edge = edge_id
        else:
            layercourse.high_edge = edge_id
        layercourse.block_edges.append(
            BlockEdgeInfo(
                edge_id=edge_id,
                block_path=block_path,
            ),
        )
        # All done
        return

    if layercourse.course_node is None:
        # Either the course is new or the graph looks something like this:
        # source --> old block
        # In either case, we need to create the node and build something like this:
        # source --> course --> old block (if it existed)
        nodeid = g.add(Node(debug_name=short_name))
        layercourse.course_node = nodeid
        for old_block_edge in layercourse.block_edges:
            g.edges[old_block_edge.edge_id].cost = 0
            g.edges[g.edges[old_block_edge.edge_id].rev].cost = 0
            g.move_source(old_block_edge.edge_id, nodeid)
        if usable.taken != 0:
            g.connect("", g.source, nodeid, usable.taken, cost=TAKEN_COST)
        if usable.filler != 0:
            g.connect("", g.source, nodeid, usable.filler, cost=FILLER_COST)

    # Add the new edge to the block
    layercourse.block_edges.append(
        BlockEdgeInfo(
            edge_id=g.connect(
                full_name,
                layercourse.course_node,
                connect_to,
                credits,
                cost=0,
            ),
            block_path=block_path,
        ),
    )


def _build_visit(
    courseinfo: CourseInfo,
    g: SolvedCurriculum,
    block_stack: list[Block],
    block: Block,
    connect_to: int,
):
    """
    Recursively visit a block of the curriculum tree, building it as we go.
    Connect all of the children, and then connect this node to `connect_to`.
    """
    block_stack.append(block)

    if isinstance(block, Leaf):
        # A list of courses

        # Count the maximum amount of credits that could flow into this block
        subcreds = 0
        if len(block.codes) < len(g.usable):
            # This block has little codes, iterate over those
            for code in block.codes:
                if code in g.usable:
                    usable = g.usable[code]
                    subcreds += usable.taken + usable.filler
        else:
            # This block has many codes, iterate over taken courses
            for code, usable in g.usable.items():
                if code in block.codes:
                    subcreds += usable.taken + usable.filler

        # Check if we must add an intermediate node to model the effect of the block's
        # capacity
        # Ie. if there are less credits that come in than the capacity that can go out,
        # then the capacity has no effect
        if subcreds > block.cap:
            subnode = g.add(Node(block.debug_name))
            g.connect("", subnode, connect_to, block.cap, cost=0)
            connect_to = subnode

        # Actually connect the courses
        block_path = tuple(block_stack)
        if len(block.codes) < len(g.usable):
            # This block has little codes, iterate over those
            # However, remember to preserve order!
            for code in sorted(
                (code for code in block.codes if code in g.usable),
                key=lambda code: g.usable[code].flat_order,
            ):
                _connect_course(
                    courseinfo,
                    g,
                    block.layer,
                    code,
                    g.usable[code],
                    block_path,
                    connect_to,
                )
        else:
            # This block has many codes, iterate over taken courses
            for code, usable in g.usable.items():
                if code in block.codes:
                    _connect_course(
                        courseinfo,
                        g,
                        block.layer,
                        code,
                        usable,
                        block_path,
                        connect_to,
                    )
    else:
        # If this block imposes capacity restrictions, add a node to model this
        children_cap = 0
        for c in block.children:
            children_cap += c.cap
        if children_cap > block.cap:
            subnode = g.add(Node(block.debug_name))
            g.connect("", subnode, connect_to, block.cap, cost=0)
            connect_to = subnode

        # A combination of blocks
        for c in block.children:
            _build_visit(courseinfo, g, block_stack, c, connect_to)

    block_stack.pop()


def _add_usable_credits(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    g: SolvedCurriculum,
    to_add: PseudoCourse | FillerCourse,
):
    """
    Add a certain amount of taken and filler credits to the usable pool.
    """
    course = to_add.course if isinstance(to_add, FillerCourse) else to_add
    og_code = course.code

    # Only allow equivalencies to count towards their corresponding block
    if isinstance(course, ConcreteId) and course.equivalence is not None:
        course = course.equivalence
    # Map curriculum equivalencies
    if course.code in curriculum.equivalencies:
        code = curriculum.equivalencies[course.code]
        course = (
            ConcreteId(code=code)
            if isinstance(course, ConcreteId)
            else EquivalenceId(code=code, credits=course.credits)
        )
    code = course.code

    if code in g.usable:
        usable = g.usable[code]
    else:
        usable = UsableCourse(
            taken=0,
            filler=0,
            taken_list=[],
            filler_list=[],
            flat_order=len(g.usable),
        )
        g.usable[code] = usable

    info = courseinfo.try_course(code)
    intrinsic_credits = (
        None if info is None else (1 if info.credits == 0 else info.credits)
    )
    multiplicity = curriculum.multiplicity.get(code, intrinsic_credits)

    # Assign 1 ghost credit to 0-credit courses
    # Kind of a hack, but works pretty well
    # The curriculum definition must correspondingly also consider
    # 0-credit courses to have 1 ghost credit
    credits = courseinfo.get_ghost_credits(course)
    if credits is None:
        return
    if multiplicity and usable.taken + usable.filler + credits > multiplicity:
        return

    if isinstance(to_add, FillerCourse):
        rep_idx = len(usable.taken_list)
        usable.filler += credits
        usable.filler_list.append(to_add)
    else:
        rep_idx = len(usable.taken_list) + len(usable.filler_list)
        usable.taken += credits
        usable.taken_list.append(to_add)

    g.mapping.setdefault(og_code, []).append((code, rep_idx))


def _build_graph(
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
    # TODO: Use curriculum equivalencies
    for sem in taken_semesters:
        for c in sorted(sem, key=lambda c: c.code):
            if courseinfo.try_any(c) is None:
                continue
            _add_usable_credits(courseinfo, curriculum, g, c)
    for fillers in curriculum.fillers.values():
        for filler in fillers:
            _add_usable_credits(courseinfo, curriculum, g, filler)

    # Build curriculum graph from the curriculum tree
    _build_visit(courseinfo, g, [], curriculum.root, g.sink)
    return g


def _max_flow_min_cost(g: SolvedCurriculum):
    # Check that there are no negative cycles in the residual graph
    # To simplify this check, we just check that there are no negative cost edges in
    # the residual graph
    for edge in g.edges:
        if edge.flow < edge.cap and edge.cost < 0:
            raise Exception(
                "curriculum residual flow graph has negative cost edges",
            )
    if len(g.edges) == 0:
        return

    # Iteratively improve flow
    queue: dict[int, None] = {}
    parent: list[Edge] = [g.edges[0] for _node in g.nodes]
    while True:
        # Find shortest path from source to sink using SPFA
        dists: list[int] = [INFINITY for _node in g.nodes]
        dists[g.source] = 0
        queue.clear()
        queue[g.source] = None
        while queue:
            id = next(iter(queue.keys()))
            del queue[id]
            for edgeid in g.nodes[id].outgoing_active:
                edge = g.edges[edgeid]
                dst = edge.dst
                newdist = dists[edge.src] + edge.cost
                if newdist < dists[dst]:
                    dists[dst] = newdist
                    parent[dst] = edge
                    queue[dst] = None

        # If no path from source to sink is found, the flow is maximal
        if dists[g.sink] == INFINITY:
            break

        # Find the maximum flow that can go through the path
        flow = INFINITY
        cur = g.sink
        while cur != g.source:
            edge = parent[cur]
            f = edge.cap - edge.flow
            if f < flow:
                flow = f
            cur = edge.src

        # Apply flow to the path
        cur = g.sink
        while cur != g.source:
            edge = parent[cur]
            rev = g.edges[edge.rev]
            edge.flow += flow
            if edge.flow == edge.cap:
                # This edge reached max capacity, so it is no longer in the residual
                # graph
                g.nodes[edge.src].outgoing_active.remove(edge.id)
            if rev.flow == rev.cap:
                # This edge is about to have some spare capacity, so it will go back
                # into the residual graph
                g.nodes[rev.src].outgoing_active.add(rev.id)
            rev.flow -= flow
            cur = edge.src


def _tag_edge_flow(g: SolvedCurriculum):
    for layer in g.layers.values():
        for code, layercourse in layer.courses.items():
            # Considering a single layer-course pair
            available_taken_flow = g.usable[code].taken
            for block_edge in layercourse.block_edges:
                flow = g.edges[block_edge.edge_id].flow
                if flow > 0:
                    # This layer-course-block assignment has flow through it!
                    if flow > available_taken_flow:
                        # If there is not enough taken flow, use filler flow
                        block_edge.filler_flow += flow - available_taken_flow
                        flow = available_taken_flow
                    block_edge.taken_flow += flow
                    available_taken_flow += flow


class InvalidSolutionError(Exception):
    """
    Currently, the solver does not verify that there is no split flow.
    In other words, a course could be split in half and satisfy two blocks at once.
    This error is raised when that happens.

    TODO: Do something about this edge case
        Solving this problem is NP-complete, but it is such an edge case that we can
        probably get away by trying all possible paths the split flow could take.
    """


def _tag_source_courses(courseinfo: CourseInfo, g: SolvedCurriculum):
    """
    For every block edge (ie. an edge from a course node to a block node), find out
    which course instance sourced its flow.
    """

    def creds_or_zero(course: PseudoCourse) -> int:
        return course.credits if isinstance(course, EquivalenceId) else 0

    for layer in g.layers.values():
        for code, layercourse in layer.courses.items():
            usable = g.usable[code]

            # The problem is: assign a set of courses to each block edge, such that the
            # sum of credits of the courses in each set is exactly the amount of credits
            # in the corresponding block edge.
            # TODO: Solve this problem correctly.
            # This is a variation of the knapsack problem, and is NP-complete.
            # Currently, we use an heuristic: use the largest courses first, then the
            # smaller ones.
            layercourse.active_taken_edges = [None for _ in usable.taken_list]
            layercourse.active_filler_edges = [None for _ in usable.filler_list]
            taken_indices = iter(
                sorted(
                    (i for i, _ in enumerate(usable.taken_list)),
                    key=lambda i: -creds_or_zero(usable.taken_list[i]),
                ),
            )
            filler_indices = iter(
                sorted(
                    (j for j, _ in enumerate(usable.filler_list)),
                    key=lambda j: -creds_or_zero(usable.filler_list[j].course),
                ),
            )
            for edge in layercourse.block_edges:
                # Figure out where the taken flow comes from
                flow = edge.taken_flow
                while flow > 0:
                    i = next(taken_indices)
                    credits = courseinfo.get_ghost_credits(usable.taken_list[i]) or 0
                    flow -= credits
                    layercourse.active_taken_edges[i] = (edge, credits)
                if flow != 0:
                    raise InvalidSolutionError(f"{code} has split taken flow")
                # Figure out where the filler flow comes from
                flow = edge.filler_flow
                while flow > 0:
                    j = next(filler_indices)
                    credits = (
                        courseinfo.get_ghost_credits(usable.filler_list[j].course) or 0
                    )
                    flow -= credits
                    layercourse.active_filler_edges[j] = (edge, credits)
                if flow != 0:
                    raise InvalidSolutionError(f"{code} has split filler flow")


def _get_superblock(
    g: SolvedCurriculum,
    layers_to_check: list[str],
    code: str,
    rep_idx: int,
) -> str:
    for layer_id in layers_to_check:
        layer = g.layers[layer_id]
        if code not in layer.courses:
            continue
        layercourse = layer.courses[code]
        usable = g.usable[code]

        # Get the edge connected to this course on this layer
        maybe_block_edge = (
            layercourse.active_taken_edges[rep_idx]
            if rep_idx < len(usable.taken_list)
            else layercourse.active_filler_edges[rep_idx - len(usable.taken_list)]
        )
        if maybe_block_edge is None:
            continue
        block_edge, _active_credits = maybe_block_edge

        # Use the first superblock block in the path
        for block in block_edge.block_path:
            if block.block_code.startswith(SUPERBLOCK_PREFIX):
                return block.block_code[len(SUPERBLOCK_PREFIX) :]

    # No superblock found
    return ""


def _tag_superblocks(g: SolvedCurriculum):
    # Sort layers to check them in order
    # In particular, check the default "" layer first
    layer_ids = sorted(g.layers)

    # Find superblocks for all codes
    g.superblocks = {}
    for code, usable in g.usable.items():
        # Find the superblock for all course instances with this code
        g.superblocks[code] = [
            _get_superblock(g, layer_ids, code, i)
            for i in range(len(usable.taken_list) + len(usable.filler_list))
        ]


def solve_curriculum(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    taken: list[list[PseudoCourse]],
) -> SolvedCurriculum:
    # Take the curriculum blueprint, and produce a graph for this student
    g = _build_graph(courseinfo, curriculum, taken)
    # Solve the flow problem on the produced graph
    _max_flow_min_cost(g)
    # Determine the amount of flow in each edge
    _tag_edge_flow(g)
    # Match flow to the originating courses
    try:
        _tag_source_courses(courseinfo, g)
    except InvalidSolutionError as e:
        raise InvalidSolutionError(
            "min cost max flow produced invalid split-flow"
            " (ie. there is some node with 2+ non-zero-flow outgoing edges)"
            f":\n{g.dump_graphviz_pretty(curriculum)}",
        ) from e
    # Determine course superblocks
    _tag_superblocks(g)
    # Ensure that demand is satisfied exactly
    # Recommended courses should always fill in missing demand
    # It's a bug if they cannot fill in the demand
    if g.nodes[g.sink].flow(g) != curriculum.root.cap:
        raise Exception(
            "maximizing flow does not satisfy the root demand exactly,"
            " even with filler recommendations"
            f":\n{g.dump_graphviz_pretty(curriculum)}",
        )
    return g


class EquivalentFillerFinder:
    g: SolvedCurriculum
    outgoing: list[list[Edge]]
    incoming: list[list[Edge]]
    queue: dict[int, None]

    def __init__(self, g: SolvedCurriculum) -> None:
        self.g = g
        outgoing: list[list[Edge]] = [[] for _node in g.nodes]
        incoming: list[list[Edge]] = [[] for _node in g.nodes]
        for node in g.nodes:
            for edgeid in node.outgoing_active:
                edge = g.edges[edgeid]
                outgoing[edge.src].append(edge)
                incoming[edge.dst].append(edge)
        self.outgoing = outgoing
        self.incoming = incoming
        self.queue = {}

    def find_equivalents(self, active_edge: BlockEdgeInfo) -> set[str]:
        """
        Find all of the courses that can "equivalently" fill in the gap that
        `active_edge` can fill (including the course itself).
        """

        # The active edge we are considering goes is a block edge that goes from a
        # course node to a block node.
        # We are going to find low-cost cycles in the residual network that go in the
        # opposite direction of this edge and go through another block edge for another
        # course.
        # The reason we do this, is that adding flow along this path is equivalent to
        # taking another course instead of the active course, at a very low cost.
        # We are going to define the reverse of the active edge as the "main edge".
        # We'll compute the distances from the "source" (the destination of the main
        # edge) to all nodes.
        # We'll also compute the distances from the "sink" (the source of the main edge)
        # to all nodes.
        # Then, we can quickly compute the length of a cycle going through the main edge
        # and another edge by adding up 4 values.

        g = self.g
        main_edge = g.edges[g.edges[active_edge.edge_id].rev]
        source = main_edge.dst
        sink = main_edge.src

        # Run an SPFA to find distances from source to all nodes
        source_dist: list[int] = [INFINITY for _node in g.nodes]
        source_dist[source] = 0
        queue = self.queue
        queue.clear()
        queue[source] = None
        while queue:
            id = next(iter(queue.keys()))
            del queue[id]
            for edge in self.outgoing[id]:
                dst = edge.dst
                newdist = source_dist[id] + edge.cost
                if newdist < source_dist[dst]:
                    source_dist[dst] = newdist
                    queue[dst] = None

        # Run an SPFA to find distances from all nodes to the sink
        sink_dist: list[int] = [INFINITY for _node in g.nodes]
        sink_dist[sink] = 0
        queue = self.queue
        queue.clear()
        queue[sink] = None
        while queue:
            id = next(iter(queue.keys()))
            del queue[id]
            for edge in self.incoming[id]:
                src = edge.src
                newdist = sink_dist[id] + edge.cost
                if newdist < sink_dist[src]:
                    sink_dist[src] = newdist
                    queue[src] = None

        # Identify which filler courses have low distances
        equivalents: set[str] = set()
        for layer in g.layers.values():
            for code, layercourse in layer.courses.items():
                usable = g.usable[code]
                if usable.filler == 0 or code in equivalents:
                    continue

                # Find an unused filler course
                filler_course = None
                for j, other_active_edge in enumerate(layercourse.active_filler_edges):
                    if other_active_edge is None:
                        filler_course = usable.filler_list[j]
                        break
                if filler_course is None:
                    continue

                # Check if there is a cycle that goes through some free
                for block_edge in layercourse.block_edges:
                    edge = g.edges[block_edge.edge_id]
                    if edge.flow < edge.cap and (
                        main_edge.cost
                        + source_dist[edge.src]
                        + edge.cost
                        + sink_dist[edge.dst]
                        <= EQUIVALENT_FILLER_THRESHOLD
                    ):
                        # This is an equivalent filler!
                        equivalents.add(code)
                        # Do not suggest twice if there are two reachable cycles
                        break
        return equivalents
