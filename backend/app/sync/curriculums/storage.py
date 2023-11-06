from collections import defaultdict
from collections.abc import Iterator
from itertools import chain
from typing import Annotated

from pydantic import BaseModel, Field

from app.plan.courseinfo import EquivDetails
from app.plan.validation.curriculum.tree import Curriculum, CurriculumSpec, Cyear


def _try_get(dict: dict[str, Curriculum], spec: CurriculumSpec) -> Curriculum | None:
    return dict.get(str(spec))


class ProgramDetails(BaseModel):
    code: str
    name: str
    version: str
    program_type: str


class ProgramOffer(BaseModel):
    major: dict[str, ProgramDetails] = {}
    minor: dict[str, ProgramDetails] = {}
    title: dict[str, ProgramDetails] = {}
    major_minor: dict[str, list[str]] = {}


class CurriculumStorage(BaseModel):
    offer: defaultdict[
        Cyear,
        Annotated[ProgramOffer, Field(default_factory=ProgramOffer)],
    ] = defaultdict(ProgramOffer)
    majors: dict[str, Curriculum] = {}
    minors: dict[str, Curriculum] = {}
    titles: dict[str, Curriculum] = {}
    lists: dict[str, EquivDetails] = {}

    def get_major(self, spec: CurriculumSpec) -> Curriculum | None:
        if x := _try_get(self.majors, spec):
            return x
        if x := _try_get(self.majors, spec.no_title()):
            return x
        if x := _try_get(self.majors, spec.no_minor()):
            return x
        if x := _try_get(self.majors, spec.no_minor().no_title()):
            return x
        return None

    def get_minor(self, spec: CurriculumSpec) -> Curriculum | None:
        if x := _try_get(self.minors, spec):
            return x
        if x := _try_get(self.minors, spec.no_title()):
            return x
        if x := _try_get(self.minors, spec.no_major()):
            return x
        if x := _try_get(self.minors, spec.no_major().no_title()):
            return x
        return None

    def get_title(self, spec: CurriculumSpec) -> Curriculum | None:
        if x := _try_get(self.titles, spec):
            return x
        if x := _try_get(self.titles, spec.no_minor()):
            return x
        if x := _try_get(self.titles, spec.no_major()):
            return x
        if x := _try_get(self.titles, spec.no_major().no_minor()):
            return x
        return None

    def set_major(self, spec: CurriculumSpec, curr: Curriculum):
        self.majors[str(spec)] = curr

    def set_minor(self, spec: CurriculumSpec, curr: Curriculum):
        self.minors[str(spec)] = curr

    def set_title(self, spec: CurriculumSpec, curr: Curriculum):
        self.titles[str(spec)] = curr

    def all_plans(self) -> Iterator[Curriculum]:
        return chain(self.majors.values(), self.minors.values(), self.titles.values())
