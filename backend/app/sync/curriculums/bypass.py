"""
Algunos curriculums tienen reglas tan unicas que es mejor especificarlos a mano
directamente en el formato universal.
"""

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from app.plan.course import ConcreteId, EquivalenceId
from app.plan.courseinfo import CourseDetails, EquivDetails
from app.plan.validation.curriculum.tree import (
    Block,
    Combination,
    Curriculum,
    CurriculumSpec,
    FillerCourse,
    Leaf,
    Multiplicity,
)
from app.sync.curriculums.siding import SidingInfo
from app.sync.curriculums.storage import CurriculumStorage


class BypassFiller(BaseModel):
    order: list[int]
    cost_offset: int = 0
    homogeneous: bool = False
    unessential: bool = False


@dataclass
class LiveBypassFiller:
    code: str
    courses: list[str] = field(default_factory=list)


class BypassBase(BaseModel):
    debug_name: str
    name: str | None = None
    layer: str | None = None
    superblock: str | None = None
    filler: BypassFiller | None = None


class BypassCombination(BypassBase):
    cap: int | None = None
    children: list["BypassNode"]


class BypassLeaf(BypassBase):
    credits: int
    codes: list[str] | str


BypassNode = BypassCombination | BypassLeaf

BypassCombination.update_forward_refs()


class BypassEquivalentGroup(BaseModel):
    equivalents: set[str]
    max_credits: int


class Bypass(BaseModel):
    blocks: list[BypassNode]
    groups: list[BypassEquivalentGroup] = Field(default_factory=list)

    def translate(
        self,
        courses: dict[str, CourseDetails],
        siding: SidingInfo,
        storage: CurriculumStorage,
        spec: CurriculumSpec,
        unique_id: str,
    ) -> Curriculum:
        """
        Translate a human-friendly "bypass" format into a curriculum specification.
        """

        curr = Curriculum.empty(spec)

        # Translate the curriculum tree
        translator = BypassTranslator(courses, siding, unique_id, curr, storage)
        root, _creds = translator.translate(
            BypassCombination(debug_name="Raíz", children=self.blocks),
            "",
            None,
            None,
        )
        assert isinstance(root, Combination)
        curr.root = root

        # Translate equivalents and special multiplicities
        translator.translate_multiplicity(self.groups)

        return curr


@dataclass
class BypassTranslator:
    courses: dict[str, CourseDetails]
    siding: SidingInfo
    unique_id: str
    out: Curriculum
    storage: CurriculumStorage
    equiv_counter: int = 0
    seen_fillers: dict[int, EquivDetails | str] = field(default_factory=dict)

    def translate(
        self,
        bypass: BypassNode,
        layer: str,
        superblock: str | None,
        filler: LiveBypassFiller | None,
    ) -> tuple[Block, int]:
        """
        Recursively translate a particular node.
        Passes down the current layer, superblock and filler.
        """

        if bypass.layer is not None:
            layer = bypass.layer
        if bypass.superblock is not None:
            superblock = bypass.superblock
        if bypass.filler is not None:
            # Create a filler for the entire subtree rooted at this node
            if filler is not None:
                raise Exception("found nested fillers")
            # If the order number is reused, also reuse the equivalence itself
            previous = self.seen_fillers.get(bypass.filler.order[0])
            if any(
                order in self.seen_fillers and previous != self.seen_fillers[order]
                for order in bypass.filler.order
            ):
                raise Exception(f"incompatible fillers {bypass.filler.order}")
            code = (
                previous.code
                if isinstance(previous, EquivDetails)
                else self.next_equiv_code()
            )
            # Collect courses in the subtree
            filler = LiveBypassFiller(code=code)
        if isinstance(bypass, BypassCombination):
            # This node represents a combination of children nodes
            if not bypass.children:
                raise Exception("found combination node with 0 children")
            block, credits = self.translate_combination(
                bypass,
                layer,
                superblock,
                filler,
            )
        else:
            # This node represents a leaf of the tree
            if filler is None:
                raise Exception("found a leaf with no fillers in path to root")
            if superblock is None:
                raise Exception("found a leaf with no superblock")
            block = self.translate_leaf(bypass, layer, superblock, filler)
            credits = bypass.credits
        if bypass.filler is not None:
            assert filler is not None
            # We have finished processing all nodes in the subtree
            # Therefore, we have collected all courses in the subtree, and we can create
            # the equivalence and filler
            fillers_to_add = self.create_filler(
                filler,
                bypass.filler,
                bypass.name,
                credits,
            )
            # Add the created fillers to the curriculum
            for filler_to_add in fillers_to_add:
                self.out.fillers.setdefault(filler_to_add.course.code, []).append(
                    filler_to_add,
                )
        return block, credits

    def translate_combination(
        self,
        bypass: BypassCombination,
        layer: str,
        superblock: str | None,
        filler: LiveBypassFiller | None,
    ) -> tuple[Combination, int]:
        # Process the children
        children: list[Block] = []
        credits = 0
        for child in bypass.children:
            child_block, child_creds = self.translate(
                child,
                layer,
                superblock,
                filler,
            )
            children.append(child_block)
            credits += child_creds
        if bypass.cap is not None:
            credits = bypass.cap
        block = Combination(
            debug_name=bypass.debug_name,
            name=bypass.name,
            cap=-1 if bypass.cap is None else bypass.cap,
            children=children,
        )
        return block, credits

    def translate_leaf(
        self,
        bypass: BypassLeaf,
        layer: str,
        superblock: str,
        filler: LiveBypassFiller,
    ) -> Leaf:
        # Accept either a literal list of course codes or a SIDING list name
        codes = bypass.codes
        if isinstance(codes, str):
            # This node references a SIDING list
            if codes not in self.siding.lists:
                raise Exception(f"unknown siding list '{codes}'")
            codes = [
                curso.Sigla
                for curso in self.siding.lists[codes]
                if curso.Sigla and curso.Sigla in self.courses
            ]
        for code in codes:
            if code not in self.courses:
                raise Exception(f"unknown course '{code}'")
        # Add the courses to the courses in the filler equivalence
        filler.courses.extend(codes)
        return Leaf(
            debug_name=bypass.debug_name,
            name=bypass.name,
            superblock=superblock,
            cap=bypass.credits,
            list_code=filler.code,
            codes=set(codes),
            layer=layer,
        )

    def create_filler(
        self,
        live_filler: LiveBypassFiller,
        filler: BypassFiller,
        name: str | None,
        credits: int,
    ) -> list[FillerCourse]:
        """
        Create filler courses from the given filler info.
        May create a concrete course or an equivalence based on the amount of courses.
        """
        if not live_filler.courses:
            raise Exception("found filler with no courses")
        # If there is a single course, we can extract metadata from it
        if len(live_filler.courses) == 1:
            main_code = live_filler.courses[0]
            if main_code not in self.courses:
                raise Exception(f"unknown single-course equivalence {main_code}")
            info = self.courses[main_code]
            if name is None:
                name = info.name
            credits = info.credits
            filler.homogeneous = True
        if name is None:
            raise Exception("found nameless filler")
        # Create the equivalence
        equiv = EquivDetails(
            code=live_filler.code,
            name=name,
            is_homogeneous=filler.homogeneous,
            is_unessential=filler.unessential,
            courses=live_filler.courses,
        )
        # Add the equivalence
        self.storage.lists[equiv.code] = equiv
        # Create the fillers
        fillers_to_add: list[FillerCourse] = []
        for order in filler.order:
            if order in self.seen_fillers:
                # Ensure that the filler is compatible
                if self.seen_fillers[order] != equiv:
                    raise Exception(
                        f"incompatible fillers with order {order}:"
                        f" {self.seen_fillers[order]} and {equiv}",
                    )
                # This filler has already been seen, continue
                continue
            equiv_course = EquivalenceId(
                code=equiv.code,
                credits=_ceil_div(credits, len(filler.order)),
            )
            if filler.homogeneous:
                equiv_course = ConcreteId(
                    code=live_filler.courses[0],
                    equivalence=equiv_course,
                )
            fillers_to_add.append(
                FillerCourse(
                    course=equiv_course,
                    order=order,
                    cost_offset=filler.cost_offset,
                ),
            )
            self.seen_fillers[order] = equiv
        return fillers_to_add

    def next_equiv_code(self) -> str:
        self.equiv_counter += 1
        return f"{self.unique_id}-{self.equiv_counter}"

    def translate_multiplicity(self, groups: list[BypassEquivalentGroup]):
        for group in groups:
            for code in group.equivalents:
                if code in self.out.multiplicity:
                    raise Exception(
                        f"found non-transitive equivalent group {group.equivalents}",
                    )
            for code in group.equivalents:
                self.out.multiplicity[code] = Multiplicity(
                    group=group.equivalents,
                    credits=group.max_credits,
                )


def _ceil_div(a: int, b: int) -> int:
    return -(a // -b)
