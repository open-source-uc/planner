"""
A Ford-Fulkerson flow solver implementation that supports giving priorities to edges.
"""


from typing import NewType, Optional


VertexId = NewType("VertexId", int)
INFINITY: int = 10**18


class Edge:
    src: VertexId
    dst: VertexId
    cost: int
    cap: int
    flow: int

    def __init__(self, src: VertexId, dst: VertexId, cap: int, cost: int):
        self.src = src
        self.dst = dst
        self.cost = cost
        self.cap = cap
        self.flow = 0


class Vertex:
    id: VertexId
    adj: dict[VertexId, Edge]

    def __init__(self, id: VertexId):
        self.id = id
        self.adj = {}


class Graph:
    vertices: list[Vertex]
    edges: list[Edge]

    def __init__(self):
        self.vertices = []
        self.edges = []

    def vertex(self, id: VertexId):
        return self.vertices[id]

    def flow(self, src: VertexId, dst: VertexId) -> int:
        adj = self.vertices[src].adj
        return adj[dst].flow if dst in adj else 0

    def add_vertex(self) -> VertexId:
        id = VertexId(len(self.vertices))
        self.vertices.append(Vertex(id))
        return id

    def add_edge(
        self, src: VertexId, dst: VertexId, *, cap: int = INFINITY, cost: int = 0
    ):
        edge = Edge(src, dst, cap, cost)
        self.vertex(src).adj[dst] = edge
        self.edges.append(edge)

        rev_edge = Edge(dst, src, 0, -cost)
        self.vertex(dst).adj[src] = rev_edge
        self.edges.append(rev_edge)

    def compute_shortest_path(
        self, src: VertexId, dst: VertexId
    ) -> Optional[list[Edge]]:
        # Bellman-Ford
        n = len(self.vertices)
        costs = [INFINITY for _i in range(n)]
        costs[src] = 0
        parent: list[Optional[Edge]] = [None for _i in range(n)]
        for _stage in range(n - 1):
            stop = True
            for edge in self.edges:
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

    def maximize_flow(self, source: VertexId, sink: VertexId):
        # Initialize flows to 0
        for edge in self.edges:
            edge.flow = 0
        # Iteratively improve flow
        while True:
            # Find shortest path from source to sink
            path = self.compute_shortest_path(source, sink)
            if path is None:
                break

            # Find the maximum flow that can go through the path
            flow = INFINITY
            for edge in path:
                if edge.cap - edge.flow < flow:
                    flow = edge.cap - edge.flow

            # Apply flow to path
            for edge in path:
                edge.flow += flow
                self.vertices[edge.dst].adj[edge.src].flow -= flow
