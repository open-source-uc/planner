import logging

from pydantic import BaseModel

from app.plan.course import ConcreteId, EquivalenceId
from app.plan.courseinfo import CourseInfo, EquivDetails
from app.plan.validation.curriculum.tree import (
    SUPERBLOCK_PREFIX,
    Combination,
    Curriculum,
    CurriculumSpec,
    FillerCourse,
    Leaf,
)
from app.sync.curriculums.scrape.common import ScrapedBlock, ScrapedProgram
from app.sync.curriculums.storage import CurriculumStorage
from app.sync.siding.client import BloqueMalla

log = logging.getLogger("plan-collator")


class ProgramType(BaseModel):
    superblock_id: str
    readable_id: str
    layer_id: str
    order_base: int
    exclusive_credits: int | None


class ListBuilder:
    """
    Create an arbitrary amount of unique list codes.
    """

    unique_id: str
    storage: CurriculumStorage
    last_idx: int
    optative_idx: int
    minimum_idx: int

    def __init__(
        self,
        kind: ProgramType,
        storage: CurriculumStorage,
        spec: CurriculumSpec,
    ) -> None:
        self.unique_id = f"{kind.superblock_id.upper()}-{spec.cyear.raw}"
        if spec.major is not None:
            self.unique_id += f"-{spec.major}"
        if spec.minor is not None:
            self.unique_id += f"-{spec.minor}"
        if spec.title is not None:
            self.unique_id += f"-{spec.title}"
        self.storage = storage
        self.last_idx = 0
        self.optative_idx = 0
        self.minimum_idx = 0

    def add_list(self, name: str, courses: list[str]) -> EquivDetails:
        self.last_idx += 1
        lcode = f"#{self.unique_id}-{self.last_idx}"
        equiv = EquivDetails(
            code=lcode,
            name=name,
            is_homogeneous=len(courses) <= 1,
            is_unessential=False,
            courses=courses,
        )
        self.storage.lists[lcode] = equiv
        return equiv

    def next_optative(self) -> int:
        self.optative_idx += 1
        return self.optative_idx

    def next_minimum(self) -> int:
        self.minimum_idx += 1
        return self.minimum_idx


def translate_scrape(
    kind: ProgramType,
    courseinfo: CourseInfo,
    out: CurriculumStorage,
    spec: CurriculumSpec,
    name: str,
    siding: list[BloqueMalla],
    scrape: ScrapedProgram,
) -> Curriculum:
    curr = Curriculum.empty()
    curr.root.cap = -1

    if kind.exclusive_credits is None:
        # Determinar cuantos creditos tiene el programa, sin contar optativos
        # complementarios
        exclusive_credits = 0
        for block in scrape.blocks:
            if block.complementary:
                # Los bloques complementarios no aportan
                pass
            elif block.creds is not None:
                # Un optativo con un creditaje fijo
                exclusive_credits += block.creds
            elif len(block.options) == 1 and courseinfo.try_course(block.options[0]):
                # Un ramo unico
                info = courseinfo.try_course(block.options[0])
                assert info is not None
                exclusive_credits += info.credits
    else:
        # Una cantidad fija de creditos exclusivos (ie. el titulo)
        exclusive_credits = kind.exclusive_credits

    # El bloque exhaustivo consiste de todos los ramos de minor, pero sin optativos
    # complementarios
    # Ademas, es independiente del major y titulo, de manera que los ramos puedan
    # compartirse entre minor exhaustivo y major/titulo
    exhaustive = Combination(
        debug_name=name,
        block_code=f"{SUPERBLOCK_PREFIX}{kind.superblock_id}",
        name=kind.readable_id,
        cap=-1,
        children=[],
    )

    # El bloque exclusivo consiste de todos los ramos de minor y los optativos
    # complementarios
    # Sin embargo, tiene que competir por los ramos con el major y el titulo
    # Por ende, si uno de los ramos cuenta hacia el major/titulo, es necesario tomar un
    # optativo complementario para que el minor exclusivo este completo
    exclusive = Combination(
        debug_name=f"{name} ({exclusive_credits} créditos exclusivos)",
        block_code=f"{SUPERBLOCK_PREFIX}{kind.superblock_id}",
        name=kind.readable_id,
        cap=exclusive_credits,
        children=[],
    )

    curr.root.children.append(exhaustive)
    curr.root.children.append(exclusive)

    listbuilder = ListBuilder(kind, out, spec)
    for block in scrape.blocks:
        exh, exc, fill = translate_block(
            courseinfo,
            kind,
            spec,
            listbuilder,
            block,
            exclusive_credits,
        )
        if exh:
            exhaustive.children.append(exh)
        exclusive.children.append(exc)
        curr.fillers.setdefault(fill.course.code, []).append(fill)

    return curr


def translate_block(
    courseinfo: CourseInfo,
    kind: ProgramType,
    spec: CurriculumSpec,
    listbuilder: ListBuilder,
    block: ScrapedBlock,
    exclusive_credits: int,
) -> tuple[Leaf | None, Leaf, FillerCourse]:
    # Encontrar un buen nombre para el bloque
    if block.name is not None:
        # El bloque tiene nombre, usar este nombre
        name = block.name
    elif len(block.options) == 1 and courseinfo.try_course(block.options[0]):
        # El bloque tiene un único curso, usar el nombre del curso
        info = courseinfo.try_course(block.options[0])
        assert info is not None
        name = info.name
    elif set(block.options) == {"ICS1113", "ICS113H"}:
        # Optimización es un caso especial que sí tiene nombre
        name = "Optimización"
    elif block.complementary:
        # Un optativo complementario
        name = "Optativo Complementario"
    elif block.creds is None:
        # No hay creditos, por ende este es un mínimo de minor
        name = f"Mínimos (LISTA {listbuilder.next_minimum()})"
    else:
        # Tomar cierta cantidad de creditos de esta lista, por ende es un optativo
        # de minor
        name = f"Optativos (LISTA {listbuilder.next_optative()})"

    if "IEE2XXX" in block.options:
        # Arreglar los optativos de electrica
        block.options.remove("IEE2XXX")
        block.options.extend(
            code
            for code in courseinfo.courses
            if code.startswith("IEE2") and len(code) == len("IEE2XXX")
        )

    if block.creds is None and len(block.options) == 1:
        # Agregar este curso al plan
        code = block.options[0]
        info = courseinfo.try_course(code)
        assert info is not None
        exh = Leaf(
            debug_name=name,
            block_code=f"courses:{code}",
            name=name,
            cap=info.credits or 1,
            codes={code},
            layer=kind.layer_id,
        )
        exc = Leaf(
            debug_name=name,
            block_code=f"courses:{code}",
            name=name,
            cap=info.credits or 1,
            codes={code},
        )
        fill = FillerCourse(
            course=ConcreteId(code=code),
            order=kind.order_base + listbuilder.last_idx,
        )
    else:
        creds = block.creds
        if block.complementary:
            # El bloque complementario puede rellenar hasta el minor completo
            creds = exclusive_credits
        if creds is None:
            # Si no hay informacion de creditos, se supone que todas las opciones
            # tienen el mismo creditaje
            assert block.options
            representative = courseinfo.try_course(block.options[0])
            assert representative is not None
            for code in block.options:
                info = courseinfo.try_course(code)
                assert info is not None
                if info.credits != representative.credits:
                    raise Exception(
                        f"credits in credit-less equivalence {name} in"
                        f" {kind.superblock_id} {spec} are not homogeneous",
                    )
            creds = representative.credits

        # Filtrar las opciones que no estan en la base de datos de cursos
        available_options: list[str] = []
        for code in block.options:
            if courseinfo.try_course(code) is None:
                log.warning(f"unknown course {code} in scrape of {spec}")
                continue
            available_options.append(code)

        # Agregar esta equivalencia al plan
        equiv = listbuilder.add_list(name, available_options)
        accept_codes = set(available_options)
        accept_codes.add(equiv.code)
        exh = (
            None
            if block.complementary
            else (
                Leaf(
                    debug_name=name,
                    block_code=f"courses:{equiv.code}",
                    name=name,
                    cap=creds,
                    codes=accept_codes,
                    layer=kind.layer_id,
                )
            )
        )
        exc = Leaf(
            debug_name=name,
            block_code=f"courses:{equiv.code}",
            name=name,
            cap=creds,
            codes=accept_codes,
        )

        fill = FillerCourse(
            course=EquivalenceId(code=equiv.code, credits=creds),
            order=kind.order_base + listbuilder.last_idx,
        )
    return exh, exc, fill
