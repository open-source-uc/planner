"""
Fill the slots of a curriculum with courses, making sure that there is no overlap
within a block and respecting exclusivity rules.
"""

from typing import Optional

from ...plan import ClassIndex
from ...course import EquivalenceId, PseudoCourse

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
    course: PseudoCourse
    credits: int
    index: ClassIndex


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

    def add_course(self, layer_id: str, taken: list[TakenCourse], idx: int) -> int:
        layer: list[Optional[int]]
        if layer_id in self.courses:
            layer = self.courses[layer_id]
        else:
            layer = [None for _c in taken]
            self.courses[layer_id] = layer
        id = layer[idx]
        if id is not None:
            return id
        id = self.add(Node(origin=(layer_id, taken[idx].index)))
        layer[idx] = id
        self.connect(self.source, id, taken[idx].credits)
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


def _build_visit(g: SolvedCurriculum, taken: list[TakenCourse], block: Block) -> int:
    superid = g.add(Node(origin=block))
    if isinstance(block, Leaf):
        # A list of courses
        for i, c in enumerate(taken):
            # TODO: Limit courses to count just once (or maybe twice)
            # TODO: Prioritize edges just like SIDING
            if c.course.code in block.codes:
                subid = g.add_course(block.layer, taken, i)
                g.connect(subid, superid, block.codes[c.course.code])
            elif (
                isinstance(c.course, EquivalenceId)
                and c.course.code == block.original_code
            ):
                subid = g.add_course(block.layer, taken, i)
                g.connect(
                    subid,
                    superid,
                    c.course.credits,
                )
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

    taken: list[TakenCourse] = []
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
            taken.append(
                TakenCourse(
                    course=c,
                    credits=creds,
                    index=ClassIndex(semester=sem_i, position=i),
                )
            )

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
