from pydantic import BaseModel

from app.plan.validation.curriculum.tree import Curriculum, CurriculumSpec
from app.settings import settings


def _try_get(dict: dict[str, Curriculum], spec: CurriculumSpec) -> Curriculum | None:
    return dict.get(spec.json())


class NativeMockData(BaseModel):
    majors: dict[str, Curriculum] = {}
    minors: dict[str, Curriculum] = {}
    titles: dict[str, Curriculum] = {}

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


_native_mock_data_store: NativeMockData | None = None


def native_mock_data() -> NativeMockData:
    global _native_mock_data_store
    _native_mock_data_store = None  # DEBUG HACK: Remove this
    if _native_mock_data_store is None:
        if settings.native_mock_path == "":
            _native_mock_data_store = NativeMockData()
        else:
            _native_mock_data_store = NativeMockData.parse_file(
                settings.native_mock_path,
            )
    return _native_mock_data_store
