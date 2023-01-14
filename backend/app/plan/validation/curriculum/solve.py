"""
Fill the slots of a curriculum with courses, making sure that there is no overlap
within a block and respecting exclusivity rules.
"""

from typing import Callable, Optional, Union

from ...courseinfo import CourseInfo
from .tree import CourseList, Curriculum, Node
from dataclasses import dataclass


# Print debug messages when solving a curriculum.
DEBUG_SOLVE = False


@dataclass
class SolvedBlock:
    # Name of the block or subblock.
    name: Optional[str]
    # Capacity of the block or subblock.
    # By default, nodes (blocks or subblocks) have their capacity set as the sum of the
    # capacities of their children, but capacity can also be set manually (eg. only 10
    # credits of 5-credit-DPT courses)
    cap: int
    # How much capacity is satisfied.
    # If `flow == cap`, then the node is entirely satisfied.
    flow: int
    # Whether the node is a simple `and` node.
    # This happens when the capacity is exactly the sum of the capacities of the nodes'
    # children.
    is_and: bool
    # The name of the superblock (bloque academico) that this block is a member of.
    superblock: str
    # The child nodes connected to this node.
    children: list["SolvedNode"]

    def __repr__(self):
        children: list[str] = []
        for child in self.children:
            children.append(f"{child}")
        childrenstr = f": {', '.join(children)}" if children else ""
        return f"({self.name}[{self.flow}/{self.cap}]{childrenstr})"


@dataclass
class SolvedCourse:
    # Name of this equivalency.
    name: Optional[str]
    # Course codes.
    codes: list[str]
    # Maximum sum of credits that could potentially be achieved.
    cap: int
    # How many credits are actually taken.
    flow: int
    # The name of the superblock (bloque academico) that this course is a member of.
    superblock: str
    # Whether this course is exclusive or not.
    # Each taken course can only count towards 1 exclusive requirement.
    # However, it can also count toward any amount of non-exclusive requirements.
    exclusive: bool

    def __repr__(self):
        if len(self.codes) == 1:
            course = self.codes[0]
        elif len(self.codes) <= 5:
            course = f"[{', '.join(self.codes)}]"
        else:
            course = f"[{len(self.codes)} courses]"
        if self.flow < self.cap or self.cap != 10:
            credits = f"[{self.flow}/{self.cap}]"
        else:
            credits = ""
        return f"{course}{credits}"


SolvedNode = Union[SolvedBlock, SolvedCourse]


@dataclass
class SolvedCurriculum:
    blocks: list[SolvedNode]


def _calc_taken_courses(
    done_courses: list[str], courseinfo: dict[str, CourseInfo]
) -> dict[str, int]:
    taken_courses: dict[str, int] = {}
    for code in done_courses:
        if code not in courseinfo:
            print(f"course {code} not found in database. assuming 10 credits")
            creds = 10
        else:
            creds = courseinfo[code].credits
        taken_courses[code] = taken_courses.get(code, 0) + creds
    return taken_courses


class CurriculumSolver:
    taken_courses: dict[str, int]
    curriculum: Curriculum
    courseinfo: dict[str, CourseInfo]

    course_assignments: dict[str, SolvedCourse]

    def __init__(
        self,
        curriculum: Curriculum,
        courseinfo: dict[str, CourseInfo],
        done_courses: list[str],
    ):
        self.taken_courses = _calc_taken_courses(done_courses, courseinfo)
        self.curriculum = curriculum
        self.courseinfo = courseinfo
        self.course_assignments = {}

    def walk(self, node: Node, exclusive: bool) -> SolvedNode:
        if isinstance(node, CourseList):
            return SolvedCourse(
                name=node.name,
                codes=node.codes,
                cap=node.cap,
                flow=0,
                exclusive=exclusive,
                superblock=node.superblock,
            )
        else:
            if node.exclusive is not None:
                exclusive = node.exclusive
            solved_children: list[SolvedNode] = []
            is_and = True
            cap = 0
            for child in node.children:
                solved_child = self.walk(child, exclusive)
                cap += solved_child.cap
                solved_children.append(solved_child)
            if node.cap is not None:
                if node.cap != cap:
                    is_and = False
                cap = node.cap
            return SolvedBlock(
                name=node.name,
                cap=cap,
                flow=0,
                children=solved_children,
                is_and=is_and,
                superblock=node.superblock,
            )

    def assign(self, node: SolvedNode, flow_cap: Optional[int]):
        if flow_cap is None or node.cap < flow_cap:
            flow_cap = node.cap
        if isinstance(node, SolvedBlock):
            for child in node.children:
                self.assign(child, flow_cap)
                node.flow += child.flow
                flow_cap -= child.flow
        else:
            for course_code in node.codes:
                if flow_cap <= 0:
                    # No more courses are needed
                    break
                if course_code not in self.taken_courses:
                    # Course not taken by student
                    continue
                if node.exclusive and course_code in self.course_assignments:
                    # Course already assigned to another block
                    continue
                # Assign this course to the current block
                if course_code not in self.courseinfo:
                    print(
                        f"course {course_code} not found in database. "
                        "assuming 10 credits"
                    )
                    creds = 10
                else:
                    creds = self.courseinfo[course_code].credits
                subflow = self.taken_courses[course_code]
                if subflow > creds:
                    # TODO: Cursos de seleccion deportiva se pueden tomar 2 veces y
                    # contar para el avance curricular
                    subflow = creds
                flow_cap -= subflow
                node.flow += subflow
                if node.exclusive:
                    self.course_assignments[course_code] = node
                    if DEBUG_SOLVE:
                        print(f"course {course_code} assigned to {node.name}")
                    # TODO: Mark this course with its corresponding block
            if DEBUG_SOLVE and flow_cap > 0:
                codes = (
                    f"{len(node.codes)} courses"
                    if len(node.codes) > 10
                    else " ".join(node.codes)
                )
                print(f"node {node.name} with courses {codes} left unsatisfied")

    def solve(self) -> SolvedCurriculum:
        solved: list[SolvedNode] = []
        for block in self.curriculum.nodes:
            solved_block = self.walk(block, True)
            solved.append(solved_block)
        for block in solved:
            self.assign(block, None)

        if DEBUG_SOLVE:
            for course in self.taken_courses.keys():
                if course not in self.course_assignments:
                    print(f"course {course} left unassigned")

        return SolvedCurriculum(blocks=solved)


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
    courseinfo: dict[str, CourseInfo], curriculum: Curriculum, taken_courses: list[str]
) -> SolvedCurriculum:
    return CurriculumSolver(curriculum, courseinfo, taken_courses).solve()
