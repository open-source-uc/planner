"""
Algunos curriculums tienen reglas tan unicas que es mejor especificarlos a mano
directamente en el formato universal.
"""


from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from app.plan.course import ConcreteId, EquivalenceId
from app.plan.courseinfo import CourseInfo, EquivDetails
from app.plan.validation.curriculum.tree import (
    Block,
    Combination,
    Curriculum,
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
        courseinfo: CourseInfo,
        siding: SidingInfo,
        storage: CurriculumStorage,
        unique_id: str,
    ) -> Curriculum:
        """
        Translate a human-friendly "bypass" format into a curriculum specification.
        """

        curr = Curriculum.empty()

        # Translate the curriculum tree
        translator = BypassTranslator(courseinfo, siding, unique_id, curr, storage)
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
    courseinfo: CourseInfo
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
        if bypass.layer is not None:
            layer = bypass.layer
        if bypass.superblock is not None:
            superblock = bypass.superblock
        if bypass.filler is not None:
            if filler is not None:
                raise Exception("found nested fillers")
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
            # Create the fillers
            if len(filler.courses) == 1:
                # Create concrete-course fillers
                fillers_to_add = self.create_concrete_filler(filler, bypass.filler)
            else:
                # Create equivalence fillers
                if bypass.name is None:
                    raise Exception("found an equivalence filler with no name")
                fillers_to_add = self.create_equivalence_filler(
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
                if curso.Sigla and self.courseinfo.try_course(curso.Sigla)
            ]
        for code in codes:
            if not self.courseinfo.try_course(code):
                raise Exception(f"unknown course '{code}'")
        # Add the courses to the courses in the filler equivalence
        filler.courses.extend(codes)
        # Accept all codes in this node, and the filler equivalence too
        accept_codes = set(codes)
        accept_codes.add(filler.code)
        return Leaf(
            debug_name=bypass.debug_name,
            name=bypass.name,
            superblock=superblock,
            cap=bypass.credits,
            codes=accept_codes,
            layer=layer,
        )

    def create_concrete_filler(
        self,
        live_filler: LiveBypassFiller,
        filler: BypassFiller,
    ) -> list[FillerCourse]:
        # Create the filler
        code = live_filler.courses[0]
        fillers_to_add: list[FillerCourse] = []
        for order in filler.order:
            if order in self.seen_fillers:
                if self.seen_fillers[order] != code:
                    raise Exception(
                        f"incompatible fillers with order {order}:"
                        f" {self.seen_fillers[order]} and {code}",
                    )
                continue
            fillers_to_add.append(
                FillerCourse(
                    course=ConcreteId(code=code),
                    order=order,
                    cost_offset=filler.cost_offset,
                ),
            )
            self.seen_fillers[order] = code
        return fillers_to_add

    def create_equivalence_filler(
        self,
        live_filler: LiveBypassFiller,
        filler: BypassFiller,
        name: str,
        credits: int,
    ) -> list[FillerCourse]:
        # Create an equivalence
        if not live_filler.courses:
            raise Exception("found empty equivalence")
        equiv = EquivDetails(
            code=live_filler.code,
            name=name,
            is_homogeneous=filler.homogeneous,
            is_unessential=filler.unessential,
            courses=live_filler.courses,
        )
        self.storage.lists[equiv.code] = equiv
        fillers_to_add: list[FillerCourse] = []
        for order in filler.order:
            if order in self.seen_fillers:
                if self.seen_fillers[order] != equiv:
                    raise Exception(
                        f"incompatible fillers with order {order}:"
                        f" {self.seen_fillers[order]} and {equiv}",
                    )
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
