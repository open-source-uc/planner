from collections.abc import Iterator
from itertools import chain

from pydantic import BaseModel, Field

from app.plan.courseinfo import EquivDetails
from app.plan.validation.curriculum.tree import Curriculum, CurriculumSpec


def _try_get(dict: dict[str, Curriculum], spec: CurriculumSpec) -> Curriculum | None:
    return dict.get(spec.json())


class CurriculumStorage(BaseModel):
    majors: dict[str, Curriculum] = Field(default_factory=dict)
    minors: dict[str, Curriculum] = Field(default_factory=dict)
    titles: dict[str, Curriculum] = Field(default_factory=dict)
    lists: dict[str, EquivDetails] = Field(default_factory=dict)

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
        self.majors[spec.json()] = curr

    def set_minor(self, spec: CurriculumSpec, curr: Curriculum):
        self.minors[spec.json()] = curr

    def set_title(self, spec: CurriculumSpec, curr: Curriculum):
        self.titles[spec.json()] = curr

    def all_plans(self) -> Iterator[Curriculum]:
        return chain(self.majors.values(), self.minors.values(), self.titles.values())
