"""
Fill the slots of a curriculum with courses, making sure that there is no overlap
within a block and respecting exclusivity rules.
"""

from typing import Optional

from ...plan import ClassIndex
from ...course import PseudoCourse

from ...courseinfo import CourseInfo
from .tree import Leaf, Curriculum, Block
from dataclasses import dataclass, field


# Print debug messages when solving a curriculum.
DEBUG_SOLVE = False


@dataclass
class Edge:
    cap: int
    flow: int
    src: int
    dst: int
    rev: int
    cost: int = 0


@dataclass
class Node:
    # Either:
    # - A curriculum `Block`
    # - A course, with a layer id `str`, a semester index and a position within that
    #   semester.
    # - No origin (eg. the virtual sink node)
    origin: Block | tuple[str, ClassIndex] | None = None
    outgoing: list[Edge] = field(default_factory=list)
    incoming: list[Edge] = field(default_factory=list)

    def flow(self) -> int:
        f = 0
        for edge in self.outgoing:
            if edge.flow >= 0:
                f += edge.flow
        return f

    def cap(self) -> int:
        c = 0
        for edge in self.outgoing:
            c += edge.cap
        return c


@dataclass
class TakenCourse:
    # The courseid of the course.
    course: PseudoCourse
    # The amount of credits of the course.
    # Must correspond to `course`.
    credits: int
    # Where in the plan was this course taken.
    index: ClassIndex
    # Flattened index indicating where along the plan this course was taken.
    flat_index: int
    # `0` if this course is unique (by code) in the plan.
    # Otherwise, increments by one per every repetition.
    repeat_index: int


@dataclass
class TakenCourses:
    flat: list[TakenCourse]
    mapped: dict[str, list[TakenCourse]]


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
    # The root curriculum.
    root: int
    # A dictionary from layer ids to a (list of node ids for each course).
    courses: dict[str, list[Optional[int]]]

    def __init__(self):
        self.nodes = [Node(), Node()]
        self.edges = []
        self.source = 0
        self.sink = 1
        self.root = 1
        self.courses = {}

    def add(self, node: Node) -> int:
        id = len(self.nodes)
        self.nodes.append(node)
        return id

    def connect(self, src_id: int, dst_id: int, cap: int):
        src = self.nodes[src_id]
        dst = self.nodes[dst_id]
        edge_fw = Edge(cap=cap, flow=0, src=src_id, dst=dst_id, rev=len(dst.outgoing))
        edge_rev = Edge(cap=0, flow=0, src=dst_id, dst=src_id, rev=len(src.outgoing))
        src.outgoing.append(edge_fw)
        dst.incoming.append(edge_fw)
        dst.outgoing.append(edge_rev)
        src.incoming.append(edge_rev)
        self.edges.append(edge_fw)
        self.edges.append(edge_rev)

    def add_course(self, layer_id: str, taken: TakenCourses, c: TakenCourse) -> int:
        layer: list[Optional[int]]
        if layer_id in self.courses:
            layer = self.courses[layer_id]
        else:
            layer = [None for _c in taken.flat]
            self.courses[layer_id] = layer
        id = layer[c.flat_index]
        if id is not None:
            return id
        id = self.add(Node(origin=(layer_id, c.index)))
        layer[c.flat_index] = id
        self.connect(self.source, id, c.credits)
        return id

    def dump_graphviz(self, taken: list[list[PseudoCourse]]) -> str:  # noqa: C901
        """
        Dump the graph representation as a Graphviz DOT file.
        """
        out = "digraph {\n"
        for id, node in enumerate(self.nodes):
            if id == self.source or id == self.sink:
                continue
            elif id == self.root:
                label = "Root"
            elif isinstance(node.origin, Block):
                label = f"{node.origin.name or f'b{id}'}"
                if len(node.origin.fill_with) > 0:
                    label += f"\n({len(node.origin.fill_with)} recommendations)"
            elif isinstance(node.origin, tuple):
                layer, index = node.origin
                label = taken[index.semester][index.position].code
                if layer != "":
                    label = f"{label}({layer})"
            else:
                label = f"v{id}"
            fountain = 0
            for edge in node.outgoing:
                if edge.dst == self.sink:
                    fountain -= edge.cap
            for edge in node.incoming:
                if edge.src == self.source:
                    fountain += edge.cap
            if fountain > 0:
                label += f" +{fountain}"
            elif fountain < 0:
                label += f" {fountain}"
            out += f'  v{id} [label="{label}"];\n'
        for edge in self.edges:
            if edge.cap == 0 or edge.src == self.source or edge.dst == self.sink:
                continue
            attrs = f'label="{edge.flow}/{edge.cap}"'
            if edge.flow == 0:
                attrs += " style=dotted"
            out += f"  v{edge.src} -> v{edge.dst} [{attrs}];\n"
        out += "}"
        return out


def _connect_course(
    g: SolvedCurriculum, block: Leaf, taken: TakenCourses, c: TakenCourse, superid: int
):
    max_multiplicity = block.codes[c.course.code]
    if max_multiplicity is not None and c.repeat_index >= max_multiplicity:
        # Cannot connect to more than `max_multiplicity` courses at once
        return
    subid = g.add_course(block.layer, taken, c)
    g.connect(subid, superid, c.credits)


def _build_visit(g: SolvedCurriculum, taken: TakenCourses, block: Block) -> int:
    superid = g.add(Node(origin=block))
    if isinstance(block, Leaf):
        # A list of courses
        # TODO: Prioritize edges just like SIDING
        # TODO: Prioritize edges to concrete courses if they are children of an
        #   equivalence that matches the current block

        # For performance, iterate through the taken courses or through the accepted
        # codes, whichever is shorter
        if len(block.codes) < len(taken.flat):
            # There is a small amount of courses in this block
            # Iterate through this list, in taken order
            minitaken: list[TakenCourse] = []
            for code in block.codes:
                if code in taken.mapped:
                    minitaken.extend(taken.mapped[code])
            minitaken.sort(key=lambda c: c.flat_index)
            for c in minitaken:
                _connect_course(g, block, taken, c, superid)
        else:
            # There are way too many codes in this block
            # Iterate through taken courses instead
            for c in taken.flat:
                if c.course.code in block.codes:
                    _connect_course(g, block, taken, c, superid)
    else:
        # A combination of blocks
        for c in block.children:
            subid = _build_visit(g, taken, c)
            g.connect(subid, superid, c.cap)
    return superid


def _build_graph(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    taken_semesters: list[list[PseudoCourse]],
) -> SolvedCurriculum:
    """
    Take a curriculum prototype and a specific set of taken courses, and build a
    solvable graph that represents this curriculum.
    """

    taken = TakenCourses(flat=[], mapped={})
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
            repetitions = taken.mapped.setdefault(c.code, [])
            c = TakenCourse(
                course=c,
                credits=creds,
                index=ClassIndex(semester=sem_i, position=i),
                flat_index=len(taken.flat),
                repeat_index=len(repetitions),
            )
            repetitions.append(c)
            taken.flat.append(c)

    g = SolvedCurriculum()
    g.root = _build_visit(g, taken, curriculum.root)
    g.connect(g.root, g.sink, curriculum.root.cap)
    return g


INFINITY: int = 10**18


def _compute_shortest_path(
    g: SolvedCurriculum, src: int, dst: int
) -> Optional[list[Edge]]:
    # Bellman-Ford
    n = len(g.nodes)
    costs = [INFINITY for _i in range(n)]
    costs[src] = 0
    parent: list[Optional[Edge]] = [None for _i in range(n)]
    for _stage in range(n - 1):
        stop = True
        for edge in g.edges:
            if edge.flow < edge.cap and costs[edge.src] < INFINITY:
                new_cost = costs[edge.src] + edge.cost
                if new_cost < costs[edge.dst]:
                    costs[edge.dst] = new_cost
                    parent[edge.dst] = edge
                    stop = False
        if stop:
            break

    # Extract path (in reversed order, but who cares)
    if costs[dst] >= INFINITY:
        return None
    path: list[Edge] = []
    cur = dst
    while True:
        edge = parent[cur]
        if edge is None:
            break
        path.append(edge)
        cur = edge.src
    return path


def _solve_graph(g: SolvedCurriculum):
    # Iteratively improve flow
    while True:
        # Find shortest path from source to sink
        path = _compute_shortest_path(g, g.source, g.sink)
        if path is None:
            break

        # Find the maximum flow that can go through the path
        flow = INFINITY
        for edge in path:
            s = edge.cap - edge.flow
            if s < flow:
                flow = s

        # Apply flow to path
        for edge in path:
            edge.flow += flow
            g.nodes[edge.dst].outgoing[edge.rev].flow -= flow


def solve_curriculum(
    courseinfo: CourseInfo, curriculum: Curriculum, taken: list[list[PseudoCourse]]
) -> SolvedCurriculum:
    # Take the curriculum blueprint, and produce a graph for this student
    g = _build_graph(courseinfo, curriculum, taken)
    # Solve the flow problem on the produced graph
    _solve_graph(g)
    # Make sure that there is no split flow (ie. there is no course that splits its
    # outgoing flow between two blocks)
    # TODO: Do something about this edge case
    #   Solving this problem is NP-complete, but it is such an edge case that we can
    #   probably get away by trying all possible paths the split flow could take.
    for i, node in enumerate(g.nodes):
        if i == g.source:
            continue
        nonzero = 0
        for edge in node.outgoing:
            if edge.flow > 0:
                nonzero += 1
        if nonzero > 1:
            raise Exception(
                f"flow solution produced invalid split-flow: {g.dump_graphviz(taken)}"
            )
    return g
