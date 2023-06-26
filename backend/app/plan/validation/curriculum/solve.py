"""
Fill the slots of a curriculum with courses, making sure that there is no overlap
within a block and respecting exclusivity rules.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ...course import ConcreteId, EquivalenceId, PseudoCourse
from ...courseinfo import CourseInfo
from .tree import Block, Curriculum, FillerCourse, Leaf

# Print debug messages when solving a curriculum.
DEBUG_SOLVE = False


@dataclass
class FilledCourse:
    # The original leaf block that spawned this course.
    block: Leaf
    # The original `CourseRecommendation` that spawned this course.
    fill_with: FillerCourse
    # The repetition index.
    # The recommendation repeat indices start after the taken indices.
    repeat_index: int


@dataclass
class TakenCourse:
    # The courseid of the course.
    course: PseudoCourse
    # The amount of credits of the course.
    # Must correspond to `course`.
    credits: int
    # The semester in which this course was taken.
    sem: int
    # Where in the semester was this course taken.
    index: int
    # Flattened index indicating where along the plan this course was taken.
    flat_index: int
    # `0` if this course is unique (by code) in the plan.
    # Otherwise, increments by one per every repetition.
    repeat_index: int


@dataclass
class TakenCourses:
    flat: list[TakenCourse]
    mapped: defaultdict[str, list[TakenCourse]]


@dataclass
class Edge:
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
class CourseEdgeInfo:
    edge_id: int
    block_path: tuple[Block, ...]


@dataclass
class LayerCourse:
    origin: FilledCourse | TakenCourse
    active_edge: CourseEdgeInfo | None = None
    active_flow: int = 0
    edges: list[CourseEdgeInfo] = field(default_factory=list)


@dataclass
class LayerCourses:
    """
    Stores the current course -> node id mappings.
    """

    # Contains an entry for each course code.
    # The nested dictionary maps from repeat indices to vertex ids.
    courses: defaultdict[str, dict[int, LayerCourse]] = field(
        default_factory=lambda: defaultdict(dict),
    )


@dataclass
class CourseToConnect:
    origin: TakenCourse | FilledCourse
    layer_id: str
    course: PseudoCourse
    repeat_index: int
    block_path: tuple[Block, ...]
    credits: int
    cost: int


class SolvedCurriculum:
    # List of nodes.
    # The ID of each node is its index in this list.
    nodes: list[Node]
    # Flat list of edges.
    edges: list[Edge]
    # The id of the universal source
    source: int
    # The id of the universal sink
    sink: int
    # A dictionary from layer ids to a (list of node ids for each course).
    layers: defaultdict[str, LayerCourses]
    # Taken courses.
    taken: TakenCourses

    def __init__(self) -> None:
        self.nodes = [Node(debug_name="source"), Node(debug_name="sink")]
        self.edges = []
        self.source = 0
        self.sink = 1
        self.layers = defaultdict(LayerCourses)
        self.taken = TakenCourses(flat=[], mapped=defaultdict(list))

    def add(self, node: Node) -> int:
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
    ):
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
        was_active = edgeid in old_src.outgoing_active
        if was_active:
            old_src.outgoing_active.remove(edgeid)
        if was_active:
            new_src.outgoing_active.add(edgeid)

        self.edges[rev_id].dst = new_src_id
        old_src.incoming.remove(rev_id)
        new_src.incoming.add(rev_id)

    def add_course(
        self,
        cc: CourseToConnect,
        connect_to: int,
    ):
        repid2course = self.layers[cc.layer_id].courses[cc.course.code]
        if cc.repeat_index in repid2course:
            info = repid2course[cc.repeat_index]
        else:
            info = LayerCourse(origin=cc.origin)
            repid2course[cc.repeat_index] = info
        ancestors = "\n-> ".join(b.debug_name for b in cc.block_path)
        full_name = f"{ancestors}\n-> {cc.course.code}"
        short_name = cc.course.code
        if cc.layer_id != "":
            full_name = f"{full_name} ({cc.layer_id})"
            short_name = f"{short_name}({cc.layer_id})"
        if len(info.edges) == 0:
            # Create the first edge
            info.edges.append(
                CourseEdgeInfo(
                    edge_id=self.connect(
                        full_name,
                        self.source,
                        connect_to,
                        cc.credits,
                        cc.cost,
                    ),
                    block_path=cc.block_path,
                ),
            )
        else:
            if len(info.edges) == 1:
                # Create a new buffer node and relocate the old edge
                nodeid = self.add(Node(debug_name=short_name))
                self.connect("", self.source, nodeid, cc.credits, cost=0)
                self.move_source(info.edges[0].edge_id, nodeid)
            # Add an edge from the buffer node to wherever we must connect
            info.edges.append(
                CourseEdgeInfo(
                    edge_id=self.connect(
                        full_name,
                        self.edges[info.edges[0].edge_id].src,
                        connect_to,
                        cc.credits,
                        cc.cost,
                    ),
                    block_path=cc.block_path,
                ),
            )

    def dump_graphviz(self) -> str:
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

    def dump_raw_graphviz(self, node_labels: list[Any] | None = None) -> str:
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


def _prepare_course_connection(
    courseinfo: CourseInfo,
    block: Leaf,
    origin: TakenCourse | FilledCourse,
    block_path: tuple[Block, ...],
) -> CourseToConnect | None:
    """
    Create or look up the node corresponding to course `c` and connect it to the node
    `connect_to`.
    The caller must uphold that the code in `origin` is in `block.codes`.
    If the course in `origin` is repeated and the multiplicity of `block` does not allow
    it, the course is not connected.
    """
    course = (
        origin.course if isinstance(origin, TakenCourse) else origin.fill_with.course
    )

    # Figure out the amount of credits
    credits = courseinfo.get_credits(course)
    if credits is None:
        return None
    if credits == 0:
        credits = 1

    # Figure out multiplicity
    repeat_index = origin.repeat_index
    max_multiplicity = block.codes[course.code]
    if max_multiplicity is not None and repeat_index >= max_multiplicity:
        # Cannot connect to more than `max_multiplicity` courses at once
        return None

    # Figure out the edge cost
    cost = 10
    if (
        isinstance(course, ConcreteId)
        and course.equivalence is not None
        and course.equivalence.code in block.codes
    ) or isinstance(course, EquivalenceId):
        # Prefer equivalence edges over non-equivalence edges
        # This makes sure that equivalences always count towards their corresponding
        # blocks if there is the option
        cost = 1
    if isinstance(origin, FilledCourse):
        cost = 1000 + origin.fill_with.cost

    # Connect
    return CourseToConnect(
        layer_id=block.layer,
        course=course,
        repeat_index=repeat_index,
        origin=origin,
        credits=credits,
        cost=cost,
        block_path=block_path,
    )


def _prepare_course_connections(
    courseinfo: CourseInfo,
    g: SolvedCurriculum,
    block: Leaf,
    block_path: tuple[Block, ...],
) -> list[CourseToConnect]:
    # TODO: Prioritize edges just like SIDING
    to_connect: list[CourseToConnect] = []

    # For performance, iterate through the taken courses or through the accepted
    # codes, whichever is shorter
    if len(block.codes) < len(g.taken.flat):
        # There is a small amount of courses in this block
        # Iterate through this list, in taken order
        for code in block.codes:
            if code in g.taken.mapped:
                for course in g.taken.mapped[code]:
                    cc = _prepare_course_connection(
                        courseinfo,
                        block,
                        course,
                        block_path,
                    )
                    if cc is not None:
                        to_connect.append(cc)
        to_connect.sort(
            key=lambda cc: cc.origin.flat_index
            if isinstance(cc.origin, TakenCourse)
            else 0,
        )
    else:
        # There are way too many codes in this block
        # Iterate through taken courses instead
        for c in g.taken.flat:
            if c.course.code in block.codes:
                cc = _prepare_course_connection(courseinfo, block, c, block_path)
                if cc is not None:
                    to_connect.append(cc)

    # Iterate over the recommended courses for this block
    fill_index: dict[str, int] = {}
    for rec in block.fill_with:
        code = rec.course.code
        if code not in fill_index:
            fill_index[code] = len(g.taken.mapped[code])
        repeat_index = fill_index[code]
        filled = FilledCourse(block=block, fill_with=rec, repeat_index=repeat_index)
        cc = _prepare_course_connection(courseinfo, block, filled, block_path)
        if cc is not None:
            to_connect.append(cc)
        fill_index[code] += 1

    return to_connect


def _build_visit(
    courseinfo: CourseInfo,
    g: SolvedCurriculum,
    block_stack: list[Block],
    block: Block,
    connect_to: int,
):
    block_stack.append(block)

    if isinstance(block, Leaf):
        # A list of courses

        # Extract which courses to connect to this leaf block
        to_connect = _prepare_course_connections(
            courseinfo,
            g,
            block,
            tuple(block_stack),
        )

        # Add the taken courses
        subcreds = 0
        for cc in to_connect:
            subcreds += cc.credits
        if subcreds > block.cap:
            # We need to add an intermediate node to model the block capacity
            subnode = g.add(Node(block.debug_name))
            g.connect("", subnode, connect_to, block.cap, cost=0)
            connect_to = subnode
        for cc in to_connect:
            g.add_course(cc, connect_to)
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


def _build_graph(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    taken_semesters: list[list[PseudoCourse]],
) -> SolvedCurriculum:
    """
    Take a curriculum prototype and a specific set of taken courses, and build a
    solvable graph that represents this curriculum.
    """

    taken = TakenCourses(flat=[], mapped=defaultdict(list))
    for sem_i, sem in enumerate(taken_semesters):
        for i, c in sorted(enumerate(sem)):
            creds = courseinfo.get_credits(c)
            if creds is None:
                continue
            if creds == 0:
                # Assign 1 ghost credit to 0-credit courses
                # Kind of a hack, but works pretty well
                # The curriculum definition must correspondingly also consider
                # 0-credit courses to have 1 ghost credit
                creds = 1
            repetitions = taken.mapped[c.code]
            c = TakenCourse(
                course=c,
                credits=creds,
                sem=sem_i,
                index=i,
                flat_index=len(taken.flat),
                repeat_index=len(repetitions),
            )
            repetitions.append(c)
            taken.flat.append(c)

    g = SolvedCurriculum()
    g.taken = taken
    _build_visit(courseinfo, g, [], curriculum.root, g.sink)
    return g


INFINITY: int = 10**18


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
        # Find shortest path from source to sink
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


def solve_curriculum(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    taken: list[list[PseudoCourse]],
) -> SolvedCurriculum:
    # Take the curriculum blueprint, and produce a graph for this student
    g = _build_graph(courseinfo, curriculum, taken)
    # Solve the flow problem on the produced graph
    _max_flow_min_cost(g)
    # Determine active edges
    for layer in g.layers.values():
        for courses in layer.courses.values():
            for course in courses.values():
                # Find the active edge
                for edge in course.edges:
                    if g.edges[edge.edge_id].flow > 0:
                        course.active_edge = edge
                        course.active_flow = g.edges[edge.edge_id].flow
                        break
    # Ensure that demand is satisfied exactly
    # Recommended courses should always fill in missing demand
    # It's a bug if they cannot fill in the demand
    if g.nodes[g.sink].flow(g) != curriculum.root.cap:
        raise Exception(
            "maximizing flow does not satisfy the root demand exactly,"
            " even with filler recommendations"
            f":\n{g.dump_graphviz()}",
        )
    # Make sure that there is no split flow (ie. there is no course that splits its
    # outgoing flow between two blocks)
    # TODO: Do something about this edge case
    #   Solving this problem is NP-complete, but it is such an edge case that we can
    #   probably get away by trying all possible paths the split flow could take.
    for i, node in enumerate(g.nodes):
        if i == g.source:
            continue
        nonzero = 0
        for edgeid in node.outgoing:
            if g.edges[edgeid].flow > 0:
                nonzero += 1
        if nonzero > 1:
            raise Exception(
                "min cost max flow produced invalid split-flow"
                " (ie. there is some node with 2+ non-zero-flow outgoing edges)"
                f":\n{g.dump_graphviz()}",
            )
    return g
