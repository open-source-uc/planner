"""
A Ford-Fulkerson flow solver implementation that supports giving priorities to edges.
"""


from typing import NewType


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
    adj: list[Edge]

    def __init__(self, id: VertexId):
        self.id = id
        self.adj = []


class ShortestPaths:
    src: VertexId
    costs: list[int]
    parent: list[VertexId]


class Graph:
    vertices: list[Vertex]
    edges: list[Edge]

    def __init__(self):
        self.vertices = []
        self.edges = []

    def vertex(self, id: VertexId):
        return self.vertices[id]

    def add_vertex(self):
        id = VertexId(len(self.vertices))
        self.vertices.append(Vertex(id))
        return id

    def add_edge(
        self, src: VertexId, dst: VertexId, cap: int = INFINITY, cost: int = 0
    ):
        edge = Edge(src, dst, cap, cost)
        self.vertex(src).adj.append(edge)
        self.edges.append(edge)

        rev_edge = Edge(dst, src, 0, -cost)
        self.vertex(dst).adj.append(rev_edge)
        self.edges.append(rev_edge)

    def compute_shortest_paths(self, src: VertexId):
        pass
