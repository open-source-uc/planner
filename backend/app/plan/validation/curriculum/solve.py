"""
Fill the slots of a curriculum with courses, making sure that there is no overlap
within a block and respecting exclusivity rules.
"""

from typing import Optional, Union

from ...plan import EquivalenceId, PseudoCourse

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
    # The code of the equivalence that satisfies this block, if any.
    equiv_code: Optional[str]
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
    course_assignments: dict[str, SolvedCourse]
    unassigned_codes: list[str]


def _calc_taken_courses(
    done_courses: list[PseudoCourse], courseinfo: CourseInfo
) -> dict[str, int]:
    taken_courses: dict[str, int] = {}
    for courseid in done_courses:
        max_creds = None
        if isinstance(courseid, EquivalenceId):
            creds = courseid.credits
        else:
            creds = courseinfo.course(courseid.code).credits
            if creds == 0:
                # To allow for zero-credit courses to still be validated, a single
                # phantom credit is given to zero-credit courses
                creds = 1
            # TODO: Cursos de seleccion deportiva se pueden tomar 2 veces y
            # contar para el avance curricular
            max_creds = creds
        new_creds = taken_courses.get(courseid.code, 0) + creds
        if max_creds and new_creds > max_creds:
            new_creds = max_creds
        taken_courses[courseid.code] = new_creds
    return taken_courses


class CurriculumSolver:
    taken_courses: dict[str, int]
    curriculum: Curriculum
    courseinfo: CourseInfo

    course_assignments: dict[str, SolvedCourse]

    def __init__(
        self,
        curriculum: Curriculum,
        courseinfo: CourseInfo,
        done_courses: list[PseudoCourse],
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
                equiv_code=node.equivalence_code,
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

    def try_assign_course(self, node: SolvedCourse, course_code: str) -> int:
        if course_code not in self.taken_courses:
            # Course not taken by student
            return 0
        if node.exclusive and course_code in self.course_assignments:
            # Course already assigned to another block
            return 0
        subflow = self.taken_courses[course_code]
        node.flow += subflow
        if node.exclusive:
            self.course_assignments[course_code] = node
            if DEBUG_SOLVE:
                print(f"course {course_code} assigned to {node.name}")
        return subflow

    def assign(self, node: SolvedNode, flow_cap: Optional[int]):
        node_cap = node.cap
        if node_cap == 0:
            node_cap = 1
        if flow_cap is None or node_cap < flow_cap:
            flow_cap = node_cap
        if isinstance(node, SolvedBlock):
            for child in node.children:
                self.assign(child, flow_cap)
                node.flow += child.flow
                flow_cap -= child.flow
        else:
            if flow_cap > 0 and node.equiv_code is not None:
                flow_cap -= self.try_assign_course(node, node.equiv_code)
            for course_code in node.codes:
                if flow_cap <= 0:
                    # No more courses are needed
                    break
                # Try to assign this course to the current block
                flow_cap -= self.try_assign_course(node, course_code)
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

        unassigned: list[str] = []
        for course in self.taken_courses.keys():
            if course not in self.course_assignments:
                unassigned.append(course)
                if DEBUG_SOLVE:
                    print(f"course {course} left unassigned")

        return SolvedCurriculum(
            blocks=solved,
            course_assignments=self.course_assignments,
            unassigned_codes=unassigned,
        )


def solve_curriculum(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    taken_courses: list[PseudoCourse],
) -> SolvedCurriculum:
    return CurriculumSolver(curriculum, courseinfo, taken_courses).solve()
