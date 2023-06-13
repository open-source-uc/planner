"""
Fill the slots of a curriculum with courses, making sure that there is no overlap
within a block and respecting exclusivity rules.
"""

from collections import defaultdict
from typing import Any, Optional
from ...course import ConcreteId, EquivalenceId, PseudoCourse
from ...courseinfo import CourseInfo
from heapq import heappush, heappop
from .tree import CourseRecommendation, Leaf, Curriculum, Block
from dataclasses import dataclass, field


# Print debug messages when solving a curriculum.
DEBUG_SOLVE = False


@dataclass
class RecommendedCourse:
    # The original `CourseRecommendation` that spawned this course.
    rec: CourseRecommendation
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
    id: int
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
    # - A course, with a layer id `str` and course information.
    #   This course may be either taken by the student or recommended.
    # - No origin (eg. the virtual sink node)
    origin: Block | tuple[str, TakenCourse | RecommendedCourse] | None = None
    outgoing: list[Edge] = field(default_factory=list)
    incoming: list[Edge] = field(default_factory=list)
    outgoing_active: set[int] = field(default_factory=set)
    incoming_active: set[int] = field(default_factory=set)

    def flow(self) -> int:
        f = 0
        for edge in self.incoming:
            if edge.flow >= 0:
                f += edge.flow
        return f

    def cap(self) -> int:
        c = 0
        for edge in self.outgoing:
            c += edge.cap
        return c

    def incoming_cap(self) -> int:
        c = 0
        for edge in self.incoming:
            c += edge.cap
        return c


@dataclass
class LayerCourses:
    """
    Stores the current course -> node id mappings.
    """

    # Contains an entry for each course code.
    # The nested dictionary maps from repeat indices to vertex ids.
    courses: defaultdict[str, dict[int, int]] = field(
        default_factory=lambda: defaultdict(dict)
    )


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
    layers: defaultdict[str, LayerCourses]
    # Taken courses.
    taken: TakenCourses

    def __init__(self):
        self.nodes = [Node()]
        self.edges = []
        self.source = 0
        self.sink = 0
        self.root = 0
        self.layers = defaultdict(LayerCourses)
        self.taken = TakenCourses(flat=[], mapped=defaultdict(list))

    def add(self, node: Node) -> int:
        id = len(self.nodes)
        self.nodes.append(node)
        return id

    def connect(self, src_id: int, dst_id: int, cap: int, cost: int = 0):
        src = self.nodes[src_id]
        dst = self.nodes[dst_id]
        fw_id = len(self.edges)
        bk_id = len(self.edges) + 1
        edge_fw = Edge(
            id=fw_id, cap=cap, flow=0, src=src_id, dst=dst_id, rev=bk_id, cost=cost
        )
        edge_rev = Edge(
            id=bk_id, cap=0, flow=0, src=dst_id, dst=src_id, rev=fw_id, cost=-cost
        )
        src.outgoing.append(edge_fw)
        src.outgoing_active.add(fw_id)
        dst.incoming.append(edge_fw)
        dst.outgoing.append(edge_rev)
        src.incoming.append(edge_rev)
        self.edges.append(edge_fw)
        self.edges.append(edge_rev)

    def add_course(
        self,
        layer_id: str,
        code: str,
        repeat_index: int,
        credits: int,
        origin: TakenCourse | RecommendedCourse,
    ) -> int:
        ids = self.layers[layer_id].courses[code]
        if repeat_index in ids:
            return ids[repeat_index]
        id = self.add(Node(origin=(layer_id, origin)))
        ids[repeat_index] = id
        self.connect(self.source, id, credits)
        return id

    def dump_graphviz(self) -> str:  # noqa: C901
        """
        Dump the graph representation as a Graphviz DOT file.
        """
        out = "digraph {\n"
        for id, node in enumerate(self.nodes):
            if id == self.source:
                continue
            elif id == self.root:
                label = "Root"
            elif isinstance(node.origin, Block):
                label = f"{node.origin.name or f'b{id}'}"
                if isinstance(node.origin, Leaf) and node.origin.fill_with:
                    label += f"\n({len(node.origin.fill_with)} recommendations)"
            elif isinstance(node.origin, tuple):
                layer, c = node.origin
                if isinstance(c, TakenCourse):
                    label = c.course.code
                else:
                    label = f"[{c.rec.course.code}]"
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
            if id == self.sink:
                label += " -inf"
            elif fountain > 0:
                label += f" +{fountain}"
            elif fountain < 0:
                label += f" {fountain}"
            out += f'  v{id} [label="{label}"];\n'
        for edge in self.edges:
            if edge.cap == 0 or edge.src == self.source:
                continue
            label = f"{edge.flow}/{edge.cap}"
            if edge.cost != 0:
                label += f" (${edge.cost})"
            attrs = f'label="{label}"'
            if edge.flow == 0:
                attrs += " style=dotted"
            out += f"  v{edge.src} -> v{edge.dst} [{attrs}];\n"
        out += "}"
        return out

    def dump_raw_graphviz(self, node_labels: Optional[list[Any]] = None) -> str:
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
    block: Leaf,
    superid: int,
    origin: TakenCourse | RecommendedCourse,
):
    """
    Create or look up the node corresponding to course `c` and connect it to the node
    `superid`.
    The caller must uphold that `superid` identifies the node corresponding to block
    `block`, and that the code of `c` is in `block.codes`.
    If the course `c` is repeated and the multiplicity of `block` does not allow it,
    the course is not connected.
    """
    if isinstance(origin, TakenCourse):
        course = origin.course
    else:
        course = origin.rec.course
    repeat_index = origin.repeat_index
    credits = courseinfo.get_credits(course)
    if credits is None:
        return
    elif credits == 0:
        credits = 1
    max_multiplicity = block.codes[course.code]
    if max_multiplicity is not None and repeat_index >= max_multiplicity:
        # Cannot connect to more than `max_multiplicity` courses at once
        return
    subid = g.add_course(block.layer, course.code, repeat_index, credits, origin)
    cost = 2
    if (
        isinstance(course, ConcreteId)
        and course.equivalence is not None
        and course.equivalence.code in block.codes
    ) or isinstance(course, EquivalenceId):
        # Prefer equivalence edges over non-equivalence edges
        # This makes sure that equivalences always count towards their corresponding
        # blocks if there is the option
        cost = 1
    if isinstance(origin, RecommendedCourse):
        cost = 1000 + origin.rec.cost
    g.connect(subid, superid, credits, cost)


def _build_visit(courseinfo: CourseInfo, g: SolvedCurriculum, block: Block) -> int:
    superid = g.add(Node(origin=block))
    if isinstance(block, Leaf):
        # A list of courses
        # TODO: Prioritize edges just like SIDING

        # For performance, iterate through the taken courses or through the accepted
        # codes, whichever is shorter
        if len(block.codes) < len(g.taken.flat):
            # There is a small amount of courses in this block
            # Iterate through this list, in taken order
            minitaken: list[TakenCourse] = []
            for code in block.codes:
                if code in g.taken.mapped:
                    minitaken.extend(g.taken.mapped[code])
            minitaken.sort(key=lambda c: c.flat_index)
            for c in minitaken:
                _connect_course(courseinfo, g, block, superid, c)
        else:
            # There are way too many codes in this block
            # Iterate through taken courses instead
            for c in g.taken.flat:
                if c.course.code in block.codes:
                    _connect_course(courseinfo, g, block, superid, c)

        # Iterate over the recommended courses for this block
        recommend_index: dict[str, int] = {}
        for rec in block.fill_with:
            code = rec.course.code
            if code not in recommend_index:
                recommend_index[code] = len(g.taken.mapped[code])
            repeat_index = recommend_index[code]
            recommended = RecommendedCourse(rec=rec, repeat_index=repeat_index)
            _connect_course(courseinfo, g, block, superid, recommended)
            recommend_index[code] += 1
    else:
        # A combination of blocks
        for c in block.children:
            subid = _build_visit(courseinfo, g, c)
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
    g.root = _build_visit(courseinfo, g, curriculum.root)
    if curriculum.root.cap >= g.nodes[g.root].incoming_cap():
        # The root imposes no restriction on the flow, so we can make it an infinite
        # sink
        g.sink = g.root
    else:
        # The root limits the amount of flow, so it must have an edge to impose that
        # restriction
        g.sink = g.add(Node())
        g.connect(g.root, g.sink, curriculum.root.cap)
    return g


INFINITY: int = 10**18


def _compute_shortest_path(
    g: SolvedCurriculum, src: int, dst: int, counter: list[int]
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
        counter[0] += 1
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


def _make_weights_positive(g: SolvedCurriculum):
    # Bellman-Ford
    n = len(g.nodes)
    costs = [0 for _i in range(n)]
    stop = True
    for _stage in range(n - 1):
        stop = True
        for edge in g.edges:
            new_cost = costs[edge.src] + edge.cost
            if new_cost < costs[edge.dst]:
                costs[edge.dst] = new_cost
                stop = False
        if stop:
            break
    # if not stop:
    #     raise Exception("negative-cost cycles in curriculum graph")

    # Apply cost transformation
    for edge in g.edges:
        edge.cost += costs[edge.src] - costs[edge.dst]
        assert edge.cost >= 0


def _max_flow_min_cost(g: SolvedCurriculum):
    # Iteratively improve flow
    iterations = 0
    bf_iterations = [0]
    while True:
        iterations += 1
        # Find shortest path from source to sink
        path = _compute_shortest_path(g, g.source, g.sink, bf_iterations)
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
            g.edges[edge.rev].flow -= flow
    print(f"      {iterations} flow iterations, {bf_iterations[0]} bellman-ford stages")


def _max_flow_min_cost_2(g: SolvedCurriculum):
    # Iteratively improve flow
    queue: dict[int, None] = {}
    parent: list[Edge] = [g.edges[0] for _node in g.nodes]
    iters = 0
    spfa_iters = 0
    while True:
        iters += 1
        # Find shortest path from source to sink
        # Shortest-Path-Faster-Algorithm (SPFA)
        dists: list[int] = [INFINITY for _node in g.nodes]
        dists[g.source] = 0
        queue.clear()
        queue[g.source] = None
        spfa_budget = len(g.nodes) ** 2
        while queue:
            spfa_iters += 1
            spfa_budget -= 1
            if spfa_budget < 0:
                raise Exception("negative cycle detected in flow graph")
            id = next(iter(queue.keys()))
            del queue[id]
            for edge in g.nodes[id].outgoing:
                src = edge.src
                dst = edge.dst
                if edge.flow < edge.cap:
                    newdist = dists[src] + edge.cost
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
            edge.flow += flow
            g.edges[edge.rev].flow -= flow
            cur = edge.src

    print(f"{iters} flow iterations, {spfa_iters} spfa iterations")


def _max_flow_min_cost_3(g: SolvedCurriculum):
    # Make sure that all active edges have nonnegative cost
    for edge in g.edges:
        if edge.flow >= edge.cap:
            continue
        assert edge.cost >= 0

    # Iteratively improve flow
    queue: list[tuple[int, int]] = []
    parent: list[Optional[Edge]] = [None for _node in g.nodes]
    children: list[set[Edge]] = [set() for _node in g.nodes]
    iter = 0
    dijkstra_iter = 0
    pot_dijkstra_iter = 0
    # The cost of a node (C[u]) is the cost of the path between the source and the node
    # (D[path from source to u]).
    # The potential of a node is an arbitrary value, such that all edges satisfy:
    #   forall (u -> v): W[u, v] + P[u] - P[v] >= 0
    # We also define P[source] = 0
    # The distance of a node is the distance from source to the node in the reweighted
    # graph:
    #   W'[u, v] = W[u, v] + P[u] - P[v]
    # All reweighted edges have nonnegative weight, so we can run Dijkstra.
    # Ie. iteratively enforce the following:
    #   (u -> v): D[v] <- min(D[v], D[u] + W[u, v] + P[u] - P[v])
    # The following is true:
    #   D[v] = W[path from source to v] + P[source] - P[v]
    # Remember that P[source] = 0, and C[v] is the weight of the path in the original
    # graph:
    #   D[v] = C[v] - P[v]
    #   C[v] = D[v] + P[v]

    potentials: list[int] = [0 for _node in g.nodes]
    costs: list[int] = [INFINITY for _node in g.nodes]
    costs[g.source] = 0
    queue.clear()
    queue.append((0, g.source))

    def relax_edge(edge: Edge):
        # This edge has been "added" to the graph
        src = edge.src
        dst = edge.dst
        newcost = costs[src] + edge.cost
        if newcost < costs[dst]:
            costs[dst] = newcost
            oldparent = parent[dst]
            if oldparent is not None:
                children[oldparent.src].remove(edge)
            children[src].add(edge)
            parent[dst] = edge
            heappush(queue, (newcost - potentials[dst], dst))

    def tighten_edge(edge: Edge):
        # This edge has been "removed" from the graph
        src = edge.src
        dst = edge.dst
        if parent[dst] is edge:
            pass

    while True:
        # Find shortest path from source to sink
        # Dijkstra
        found_sink = False
        while queue:
            dijkstra_iter += 1
            if not found_sink:
                pot_dijkstra_iter += 1
            dist, id = heappop(queue)
            if dist + potentials[id] > costs[id]:
                continue
            for edge in g.nodes[id].outgoing:
                if edge.flow < edge.cap:
                    relax_edge(edge)
        iter += 1

        # If no path from source to sink is found, the flow is maximal
        if costs[g.sink] == INFINITY:
            break

        # Use shortest costs as potentials
        potentials = costs.copy()

        # Find the maximum flow that can go through the path
        flow = INFINITY
        cur = parent[g.sink]
        while cur is not None:
            f = cur.cap - cur.flow
            if f < flow:
                flow = f
            cur = parent[cur.src]

        # Apply flow to the path
        cur = parent[g.sink]
        while cur is not None:
            rev = g.edges[cur.rev]
            cur.flow += flow
            if cur.flow == cur.cap:
                # This edge is removed from the graph
                pass
            if rev.flow == cur.cap:
                # This edge is added to the graph
                relax_edge(rev)
            rev.flow -= flow
            cur = parent[cur.src]

    print(
        f"      {iter} flow iterations, {dijkstra_iter} dijkstra iterations, {pot_dijkstra_iter} useful dijkstra iterations"
    )


def _max_flow_min_cost_4(g: SolvedCurriculum):
    # Make sure that all active edges have nonnegative cost
    for edge in g.edges:
        if edge.flow < edge.cap:
            assert edge.cost >= 0

    # Keep the cost from the source node to all nodes
    costs = [INFINITY for _node in g.nodes]
    costs[g.source] = 0
    # Keep a priority queue (heap) of nodes that should propagate their cost
    # The first value is distance (**Not** cost! They are different concepts)
    # Distance[u] = Cost[u] - Potential[u]
    # Cost[u] = Distance[u] + Potential[u]
    # The reason for using distance is that Dijkstra does not normally work with
    # negative weights.
    # However, we if we use distance, defined in terms of a potential, we can use the
    # fact that the "distance weight" of all edges is always positive and Dijkstra
    # magically works.
    # The neat part about distance is that Dijkstra works with negative costs as long
    # as we use distance instead (with a valid potential).
    # The second value is a node ID.
    queue: list[tuple[int, int]] = []
    heappush(queue, (0, g.source))
    # Keep a "potential"
    # A potential is a value P[u] assigned to each node u such that:
    #   forall edge (u -> v): W[u, v] + P[u] - P[v] >= 0
    # Because at the start all edges have nonnegative weight, an all-zero potential is
    # valid.
    potential = [0 for _node in g.nodes]
    # Keep a "minimum cost tree" (ie. the shortest path from the source to any node
    # follows edges from this tree)
    # The values are edge ids
    # The parent array maps node indices to edge indices (the edge that connects its
    # parent to itself)
    parent: list[Optional[int]] = [None for _node in g.nodes]
    # The children array maps node indices to sets of **node** indices (!)
    children: list[set[int]] = [set() for _node in g.nodes]

    def relax_edge(edge: Edge):
        id = edge.id
        src = edge.src
        dst = edge.dst
        newcost = costs[src] + edge.cost
        if newcost < costs[dst]:
            costs[dst] = newcost
            oldparent = parent[dst]
            if oldparent is not None:
                children[g.edges[oldparent].src].remove(dst)
            children[src].add(dst)
            parent[dst] = id
            return True
        return False

    def remove_subtree(nodeid: int):
        costs[nodeid] = INFINITY
        oldparent = parent[nodeid]
        if oldparent is not None:
            children[g.edges[oldparent].src].remove(nodeid)
        parent[nodeid] = None
        for child_id in list(children[nodeid]):
            remove_subtree(child_id)
        relaxed = False
        for in_edge in g.nodes[nodeid].incoming:
            if in_edge.flow < in_edge.cap:
                if relax_edge(in_edge):
                    relaxed = True
        if relaxed:
            heappush(queue, (costs[nodeid] - potential[nodeid], nodeid))

    flow_iters = 0
    dijkstra_iters = 0

    # Iteratively improve flow
    while True:
        flow_iters += 1

        # Update the shortest paths from the source to all nodes
        while queue:
            dijkstra_iters += 1

            dist, id = heappop(queue)
            if dist + potential[id] > costs[id]:
                continue
            for edge in g.nodes[id].outgoing:
                if edge.flow < edge.cap:
                    if relax_edge(edge):
                        dst = edge.dst
                        heappush(queue, (costs[dst] - potential[dst], dst))

        # If no path is found, the flow is maximal
        if parent[g.sink] is None:
            break

        # Use the new shortest distances as a potential.
        # These shortest distances just turn out to be a valid potential:
        # - All edges that are removed don't matter, because they only relax the
        #   potential-condition.
        #   (Remember the potential-condition:
        #   forall edge (u -> v): W[u, v] + P[u] - P[v] >= 0 )
        # - The edges that are added to the graph (v -> u) are reverse-edges of edges
        #   that already exist in the graph (u -> v).
        #   (They must be reverse edges because in order to add a new edge to the graph,
        #   its flow must decrease. In order to decrease a flow, it must be in the
        #   shortest path of the graph, which only includes edges that are *in* the
        #   graph).
        #   Each edge (v -> u) adds an additional restriction:
        #   W[v, u] + P[v] - P[u] >= 0
        #   This can be rearranged as:
        #   P[v] >= P[u] - W[v, u]
        #   Because of the definition of the cost of reverse-edges, W[v, u] = -W[u, v]:
        #   P[v] >= P[u] + W[u, v]
        #   But this condition holds true, because we know that (u -> v) was in the
        #   shortest path from source to v, so P[v] = P[u] + W[u, v].
        # Therefore, the shortest costs is a valid potential.
        potential = costs.copy()

        # Find the maximum flow that we can send along the path
        flow = INFINITY
        cur = parent[g.sink]
        while cur is not None:
            edge = g.edges[cur]
            f = edge.cap - edge.flow
            if f < flow:
                flow = f
            cur = parent[edge.src]

        # Send the flow along the path
        cur = parent[g.sink]
        remove_root = None
        while cur is not None:
            # Send flow along the forward edge
            edge = g.edges[cur]
            edge.flow += flow
            if edge.flow >= edge.cap:
                # If the forward edge reached its capacity, it is removed from the graph
                # Therefore, any nodes whose shortest path to the source passed through
                # this edge now have their costs incorrect in `costs`
                # We need to re-update all nodes that are in the subtree of some edge
                # that was removed
                # Because in this `while` loop we visit nodes in a shortest path, the
                # least deep edge that is removed contains all other removed edges
                remove_root = edge
            # Remove flow from the backward edge
            rev = g.edges[edge.rev]
            if rev.flow >= rev.cap:
                # If the backward edge was full before, it will have space now
                # Naively, we would check this and add the edge
                # However, because the forward edge is part of the shortest path, the
                # backward edge does not improve the cost!
                # In fact, going forward and backward should have the exact same cost
                # as not moving
                assert costs[rev.dst] == costs[rev.src] + rev.cost

                # If the backward edge was full before, it will have space now
                # Therefore, it will be added to the graph and must update the costs
                # if relax_edge(rev):
                #     dst = rev.dst
                #     heappush(queue, (costs[dst] - potential[dst], dst))
            rev.flow -= flow
            cur = parent[edge.src]

        # All of the nodes in the subtree of `remove_root` should have their parent
        # cleared, their cost reset to some upper bound, and added to the update queue.
        if remove_root is not None:
            remove_subtree(remove_root.dst)

    print(
        f"{flow_iters} flow iterations, {dijkstra_iters} dijkstra iterations",
    )


def _max_flow_min_cost_5(g: SolvedCurriculum):
    # Solves the minimum-cost-max-flow problem through a modified Dinitz algorithm,
    # similar to the one explained here:
    # https://codeforces.com/blog/entry/105658

    # Make sure that all active edges have nonnegative cost
    # If this wasn't true, we would need to run Bellman-Ford to calculate the
    # potentials, and do cycle cancelling on negative cycles
    for edge in g.edges:
        if edge.flow < edge.cap:
            assert edge.cost >= 0

    # Keep a priority queue for Dijkstra
    heap: list[tuple[int, int]] = []
    # Keep potentials in order to apply Johnson's algorithm (Dijkstra with negative
    # costs)
    potential = [0 for _node in g.nodes]
    # Keep a "minimum cost subgraph" (part of Dinitz)
    parents: list[list[Edge]] = [[] for _node in g.nodes]
    children: list[list[Edge]] = [[] for _node in g.nodes]

    # Keep a queue for the BFS stage of Dinitz
    # Because dictionaries are insertion-ordered, we can use a dictionary as a queue
    queue: dict[int, None] = {}
    # Keep the seen nodes in the BFS stage of Dinitz
    seen: set[int] = set()
    # Keep the DAG built in the BFS stage of Dinitz
    dag: list[list[Edge]] = [[] for _node in g.nodes]

    # Keep the index of the first non-blocked edge for each node (part of Dinitz)
    checked_edges: list[int] = [0 for _node in g.nodes]

    flow_iters = 0
    dijkstra_iters = 0
    dinic_iters = 0

    def push_flow(id: int, flow_to_push: int) -> int:
        nonlocal dinic_iters
        dinic_iters += 1
        # print(f"pushing {flow_to_push} through node {id}")

        if id == g.sink:
            return flow_to_push
        og_flow_to_push = flow_to_push
        while checked_edges[id] < len(dag[id]):
            edge = dag[id][checked_edges[id]]
            if edge.flow < edge.cap:
                # print(
                #     f"  edge from {edge.src} to {edge.dst} with {edge.flow}/{edge.cap} and cost {edge.cost}"
                # )
                pushed = push_flow(edge.dst, min(edge.cap - edge.flow, flow_to_push))
                if pushed > 0:
                    edge.flow += pushed
                    if edge.flow == edge.cap:
                        g.nodes[edge.src].outgoing_active.remove(edge.id)
                    rev = g.edges[edge.rev]
                    if rev.flow == rev.cap:
                        g.nodes[rev.src].outgoing_active.add(rev.id)
                    rev.flow -= pushed
                    flow_to_push -= pushed
                    if flow_to_push == 0:
                        break
            checked_edges[id] += 1
        return og_flow_to_push - flow_to_push

    # Iteratively improve flow
    while True:
        flow_iters += 1

        # Run Dijkstra (with potentials)
        for ps in parents:
            ps.clear()
        dists = [INFINITY for _node in g.nodes]
        dists[g.source] = 0
        heap.clear()
        heappush(heap, (0, g.source))
        while heap:
            dijkstra_iters += 1

            # The heap contains "virtual distances" instead of just distances
            # (vdist[i] = dist[i] - potential[i])
            # The neat part is that with a valid potential, vdists are always
            # nonnegative, so Dijkstra works
            vdist, id = heappop(heap)
            if vdist + potential[id] > dists[id]:
                continue
            for edgeid in g.nodes[id].outgoing_active:
                edge = g.edges[edgeid]
                dst = edge.dst
                newdist = dists[id] + edge.cost
                if newdist < dists[dst]:
                    dists[dst] = newdist
                    parents[dst].clear()
                    heappush(heap, (dists[dst] - potential[dst], dst))
                if newdist <= dists[dst]:
                    parents[dst].append(edge)

        # If not path is found, the flow is maximal
        if len(parents[g.sink]) == 0:
            break

        # Use the new shortest distances as potentials for the next iteration
        potential = dists

        # Build the other side of the minimum cost subgraph
        for cs in children:
            cs.clear()
        for ps in parents:
            for edge in ps:
                children[edge.src].append(edge)

        while True:
            # Build a DAG out of the minimum cost subgraph
            for cs in dag:
                cs.clear()
            seen.clear()
            seen.add(g.source)
            queue.clear()
            queue[g.source] = None
            while queue:
                id = next(iter(queue.keys()))
                del queue[id]
                for edge in children[id]:
                    dst = edge.dst
                    if dst in seen:
                        continue
                    dag[id].append(edge)
                    seen.add(dst)
                    queue[dst] = None

            # Push as much flow as possible
            checked_edges = [0 for _node in g.nodes]
            push_flow(g.source, INFINITY)
            break

    print(
        f"{flow_iters} flow iterations, "
        + f"{dijkstra_iters} dijkstra iterations, "
        + f"{dinic_iters} dinitz iterations"
    )


def solve_curriculum(
    courseinfo: CourseInfo, curriculum: Curriculum, taken: list[list[PseudoCourse]]
) -> SolvedCurriculum:
    import time

    # Take the curriculum blueprint, and produce a graph for this student
    start = time.monotonic()
    g = _build_graph(courseinfo, curriculum, taken)
    print(f"      build: {(time.monotonic() - start)*1000}ms")
    print(f"      built graph with {len(g.nodes)} nodes and {len(g.edges)} edges")
    # Solve the flow problem on the produced graph
    start = time.monotonic()
    _max_flow_min_cost_2(g)
    print(f"      flow: {(time.monotonic() - start)*1000}ms")
    # Ensure that demand is satisfied
    start = time.monotonic()
    # Recommended courses should always fill in missing demand
    # It's a bug if they cannot fill in the demand
    if g.nodes[g.root].flow() < g.nodes[g.root].cap():
        raise Exception(
            "maximizing flow does not satisfy the root demand,"
            + " even with filler recommendations"
            + f":\n{g.dump_graphviz()}"
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
        for edge in node.outgoing:
            if edge.flow > 0:
                nonzero += 1
        if nonzero > 1:
            raise Exception(
                "min cost max flow produced invalid split-flow"
                + " (ie. there is some node with 2+ non-zero-flow outgoing edges)"
                + f":\n{g.dump_graphviz()}"
            )
    print(f"      checks: {(time.monotonic() - start)*1000}ms")
    return g
