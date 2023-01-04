"""
Fill the slots of a curriculum with courses, making sure that there is no overlap
within a block and respecting exclusivity rules.
"""

from typing import Callable, Optional, Union

from ...courseinfo import CourseInfo
from .tree import Combine, CourseList, Curriculum, InternalNode, Node, RequireSome
from dataclasses import dataclass
from .flow import Graph, VertexId
from hashlib import blake2b as good_hash


@dataclass
class SolvedCombine:
    # Name of the block or subblock.
    name: str
    # Capacity of the block or subblock.
    # By default, nodes (blocks or subblocks) have their capacity set as the sum of the
    # capacities of their children, but capacity can also be set manually (eg. only 10
    # credits of 5-credit-DPT courses)
    cap: int
    # Cost per unit of flow.
    # Used as a priority for the order in which to fill the nodes.
    cost: int
    # How much capacity is satisfied.
    # If `flow == cap`, then the node is entirely satisfied.
    flow: int
    # The child nodes connected to this node.
    children: list["SolvedNode"]

    # Internal graph vertex id.
    vert_id: VertexId

    def __str__(self):
        children: list[str] = []
        for child in self.children:
            childstr = f"{child}"
            if isinstance(child, SolvedCourse):
                if child.parent is not self:
                    childstr = f"{childstr}[inactive]"
            children.append(f"({childstr})")
        childrenstr = f": {', '.join(children)}" if children else ""
        return f"{self.name}[{self.flow}/{self.cap}]{childrenstr}"


@dataclass
class SolvedCourse:
    # Course codes.
    code: list[str]
    # Maximum sum of credits that could potentially be achieved.
    cap: int
    # How many credits are actually taken.
    flow: int
    # The one parent node that this course actually feeds.
    parent: Optional[SolvedCombine]

    # Internal graph vertex id.
    vert_id: VertexId

    def __str__(self):
        credits = "" if self.cap == 10 else f"[{self.cap} credits]"
        return f"{self.code}{credits}"


SolvedNode = Union[SolvedCombine, SolvedCourse]


@dataclass
class SolvedCurriculum:
    # Info about the different blocks (common, major, minor, title, etc...)
    blocks: list[SolvedCombine]

    def get_course_blocks_visit(
        self,
        course2blocks: dict[str, SolvedCombine],
        block: SolvedCombine,
        node: SolvedNode,
    ):
        if isinstance(node, SolvedCourse):
            course2blocks[node.code] = block
        else:
            for child in node.children:
                if isinstance(child, SolvedCourse) and child.parent is not node:
                    continue
                self.get_course_blocks_visit(course2blocks, block, child)

    def get_course_blocks(self) -> dict[str, SolvedCombine]:
        """
        Get the curriculum block that each course is counting towards.
        """
        course2block: dict[str, SolvedCombine] = {}
        for block in self.blocks:
            self.get_course_blocks_visit(course2block, block, block)
        return course2block

    def __str__(self):
        blocks: list[str] = []
        for block in self.blocks:
            blocks.append(f"{block}")
        return "\n".join(blocks)


class CurriculumSolver:
    curriculum: Curriculum
    courseinfo: dict[str, CourseInfo]
    graph: Graph
    source: VertexId
    sink: VertexId
    next_id: int

    # A list of all courselist nodes.
    course_nodes: list[SolvedCourse]

    # A map from course code to courselist node.
    course2node: dict[str, SolvedCourse]

    def __init__(
        self,
        curriculum: Curriculum,
        courseinfo: dict[str, CourseInfo],
        taken_courses: set[str],
    ):
        for code in taken_courses:
            if code not in courseinfo:
                raise Exception(f"Course {code} not in course database")
        self.curriculum = curriculum
        self.taken_courses = taken_courses
        self.courseinfo = courseinfo
        self.graph = Graph()
        self.next_id = 0
        self.source = self.graph.add_vertex()
        self.sink = self.graph.add_vertex()
        self.course_nodes = []
        self.course2node = {}

    def build_course_hashes(
        self, course_hashes: dict[str, bytes], node: Node, id: int
    ) -> int:
        id += 1
        if isinstance(node, InternalNode):
            for child in node.children:
                id = self.build_course_hashes(course_hashes, child, id)
        else:
            if isinstance(node, CourseList):
                courselist = node.courses
            else:
                # assert isinstance(node, str)
                courselist = [node]
            for code in courselist:
                h = good_hash(course_hashes.get(code, bytes()))
                h.update(id.to_bytes(4))
                course_hashes[code] = h.digest()
        return id

    def build_course_nodes(self, course_hashes: dict[str, bytes]):
        # Build nodes aggregating by hash
        hash2node: dict[bytes, SolvedCourse] = {}
        for code, h in course_hashes.items():
            if h in hash2node:
                node = hash2node[h]
            else:
                node = SolvedCourse(
                    code=[], cap=0, flow=0, parent=None, vert_id=self.graph.add_vertex()
                )
                hash2node[h] = node
            node.code.append(code)
            node.cap += self.courseinfo[code].credits
        # Move nodes from local dictionary to instance attributes
        self.course_nodes.clear()
        self.course2node.clear()
        for node in hash2node.values():
            self.course_nodes.append(node)
            for code in node.code:
                self.course2node[code] = node

    def build_node(self, node: Node, exclusive: bool = True) -> list[SolvedNode]:
        if isinstance(node, Combine):
            # This node is a combination node
            id = self.graph.add_vertex()
            total_cap = 0
            if node.exclusive is not None:
                exclusive = node.exclusive
            children: list[SolvedNode] = []
            for child in node.children:
                subnodes = self.build_node(child, exclusive)
                for subnode in subnodes:
                    self.graph.add_edge(subnode.vert_id, id, cap=subnode.cap)
                    total_cap += subnode.cap
                    children.append(subnode)
            if node.cap is not None:
                total_cap = node.cap
            return [
                SolvedCombine(
                    name=node.name,
                    vert_id=id,
                    cap=total_cap,
                    flow=0,
                    children=children,
                    cost=0,
                )
            ]
        else:
            # This node is a course or special course
            courses: list[str] = []
            if node.startswith("!"):
                # SpecialSource
                # Add any taken courses that match a special function
                if node not in special_sources:
                    raise Exception(f"Unrecognized special function '{node}'")
                special = special_sources[node]
                for code in self.taken_courses:
                    if special(self.courseinfo[code]):
                        courses.append(code)
            else:
                # Standard course
                if node in self.taken_courses:
                    courses.append(node)
            course_nodes: list[SolvedNode] = []
            for code in courses:
                if exclusive and code in self.course_nodes:
                    course_nodes.append(self.course_nodes[code])
                    continue
                course = SolvedCourse(
                    vert_id=self.graph.add_vertex(),
                    code=code,
                    cap=self.courseinfo[code].credits,
                    flow=self.courseinfo[code].credits,
                    parent=None,
                )
                self.graph.add_edge(self.source, course.vert_id, cap=course.cap)
                if exclusive:
                    self.course_nodes[code] = course
                course_nodes.append(course)
            return course_nodes

    def build(self) -> SolvedCurriculum:
        built_blocks: list[SolvedCombine] = []
        cost = 1
        for block in self.curriculum.blocks:
            built_block = self.build_node(block)
            assert len(built_block) == 1 and isinstance(
                built_block[0], SolvedCombine
            ), "block is of type Combine, so built_block should be SolvedCombine"
            built_block = built_block[0]
            built_block.cost = cost
            cost *= 10
            self.graph.add_edge(
                built_block.vert_id,
                self.sink,
                cap=built_block.cap,
                cost=built_block.cost,
            )
            built_blocks.append(built_block)
        return SolvedCurriculum(blocks=built_blocks)

    def update_node_flow(self, node: SolvedNode):
        if isinstance(node, SolvedCombine):
            flow = 0
            for child in node.children:
                self.update_node_flow(child)
                flow += self.graph.flow(child.vert_id, node.vert_id)
                if (
                    isinstance(child, SolvedCourse)
                    and self.graph.flow(child.vert_id, node.vert_id) > 0
                ):
                    child.parent = node
            node.flow = flow

    def solve(self) -> SolvedCurriculum:
        built = self.build()
        self.graph.maximize_flow(self.source, self.sink)
        print(f"graph = {self.graph}")
        for block in built.blocks:
            self.update_node_flow(block)
        return built


special_sources: dict[str, Callable[[CourseInfo], bool]] = {
    "!dpt5": lambda c: c.credits == 5 and c.code.startswith("DPT"),
    "!ttf": lambda c: c.code.startswith("TTF"),
    # TODO: Investigar que define a un OFG
    "!ofg": lambda c: False,
    # TODO: La definicion de un optativo de ingenieria es: "cursos de la Escuela de
    # Ingeniería nivel 3000, que no sean cursos de servicio exclusivo para otras
    # facultades"
    # Investigar que significa esto exactamente
    "!opting": lambda c: c.school == "Ingenieria"
    and 3 < len(c.code)
    and c.code[3] == "3",
}


def solve_curriculum(
    courseinfo: dict[str, CourseInfo], curriculum: Curriculum, taken_courses: set[str]
) -> SolvedCurriculum:
    return CurriculumSolver(curriculum, courseinfo, taken_courses).solve()
