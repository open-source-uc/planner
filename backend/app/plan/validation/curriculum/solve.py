"""
Fill the slots of a curriculum with courses, making sure that there is no overlap
within a block and respecting exclusivity rules.
"""

from typing import Callable, Optional, Union

from ...courseinfo import CourseInfo
from .tree import Combine, Curriculum, Node
from networkx.classes.digraph import DiGraph
import networkx
from dataclasses import dataclass


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

    # Internal graph node id.
    node_id: int

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
    # Course code.
    code: str
    # Source flow of the course (amount of credits).
    cap: int
    # The full amount of `cap` is the course is taken.
    # Otherwise, zero.
    flow: int
    # The one parent node that this course actually feeds.
    parent: Optional[SolvedCombine]

    # Internal graph node id.
    node_id: int

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
    taken_courses: set[str]
    courseinfo: dict[str, CourseInfo]
    graph: DiGraph
    source: int
    sink: int
    next_id: int
    # Cache dictionary from course code to node.
    course_nodes: dict[str, SolvedCourse]

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
        self.graph = DiGraph()
        self.next_id = 0
        self.source = self.add_node()
        self.sink = self.add_node()
        self.course_nodes = {}

    def add_node(self) -> int:
        id = self.next_id
        self.next_id += 1
        self.graph.add_node(id)
        return id

    def build_node(self, node: Node, exclusive: bool = True) -> list[SolvedNode]:
        if isinstance(node, Combine):
            # This node is a combination node
            id = self.add_node()
            total_cap = 0
            if node.exclusive is not None:
                exclusive = node.exclusive
            children: list[SolvedNode] = []
            for child in node.children:
                subnodes = self.build_node(child, exclusive)
                for subnode in subnodes:
                    self.graph.add_edge(subnode.node_id, id, capacity=subnode.cap)
                    total_cap += subnode.cap
                    children.append(subnode)
            if node.cap is not None:
                total_cap = node.cap
            return [
                SolvedCombine(
                    name=node.name,
                    node_id=id,
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
                    node_id=self.add_node(),
                    code=code,
                    cap=self.courseinfo[code].credits,
                    flow=self.courseinfo[code].credits,
                    parent=None,
                )
                self.graph.add_edge(self.source, course.node_id, capacity=course.cap)
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
                built_block.node_id,
                self.sink,
                capacity=built_block.cap,
                weight=built_block.cost,
            )
            built_blocks.append(built_block)
        return SolvedCurriculum(blocks=built_blocks)

    def update_node_flow(self, node: SolvedNode, flows: dict[int, dict[int, int]]):
        if isinstance(node, SolvedCombine):
            flow = 0
            for child in node.children:
                self.update_node_flow(child, flows)
                flow += flows[child.node_id][node.node_id]
                if (
                    isinstance(child, SolvedCourse)
                    and flows[child.node_id][node.node_id] > 0
                ):
                    child.parent = node
            node.flow = flow

    def solve(self) -> SolvedCurriculum:
        built = self.build()
        flows: dict[int, dict[int, int]]
        flows = networkx.max_flow_min_cost(
            self.graph, self.source, self.sink
        )  # pyright: reportUnknownMemberType = false
        print(f"graph = {self.graph}")
        print(f"flows = {flows}")
        for block in built.blocks:
            self.update_node_flow(block, flows)
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
