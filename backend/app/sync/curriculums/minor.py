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
from app.sync.curriculums.scrape.minor import ScrapedMinor, ScrapedMinorBlock
from app.sync.curriculums.storage import CurriculumStorage
from app.sync.siding.client import BloqueMalla, Minor

MINOR_ORDER = 100


class ListBuilder:
    """
    Create an arbitrary amount of unique list codes.
    """

    unique_id: str
    storage: CurriculumStorage
    last_idx: int
    optative_idx: int
    minimum_idx: int

    def __init__(self, storage: CurriculumStorage, spec: CurriculumSpec) -> None:
        self.unique_id = f"{spec.minor or 'N'}-{spec.cyear.raw}"
        if spec.major is not None:
            self.unique_id += f"-{spec.major}"
        if spec.title is not None:
            self.unique_id += f"-{spec.title}"
        self.storage = storage
        self.last_idx = 0
        self.optative_idx = 0
        self.minimum_idx = 0

    def add_list(self, name: str, courses: list[str]) -> EquivDetails:
        self.last_idx += 1
        lcode = f"#MINOR-{self.unique_id}-{self.last_idx}"
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


def translate_minor(
    courseinfo: CourseInfo,
    out: CurriculumStorage,
    spec: CurriculumSpec,
    siding_meta: Minor,
    siding: list[BloqueMalla],
    scrape: ScrapedMinor,
):
    curr = Curriculum.empty()
    curr.root.cap = -1

    # Determinar cuantos creditos tiene el minor, sin contar optativos complementarios
    minor_credits = 0
    for block in scrape.blocks:
        if block.complementary:
            # Los bloques complementarios no aportan
            pass
        elif block.creds is not None:
            # Un optativo con un creditaje fijo
            minor_credits += block.creds
        elif len(block.options) == 1 and courseinfo.try_course(block.options[0]):
            # Un ramo unico
            info = courseinfo.try_course(block.options[0])
            assert info is not None
            minor_credits += info.credits

    # El bloque exhaustivo consiste de todos los ramos de minor, pero sin optativos
    # complementarios
    # Ademas, es independiente del major y titulo, de manera que los ramos puedan
    # compartirse entre minor exhaustivo y major/titulo
    exhaustive = Combination(
        debug_name=siding_meta.Nombre,
        block_code=f"{SUPERBLOCK_PREFIX}Minor",
        name=f"{siding_meta.Nombre} (exhaustive)",
        cap=-1,
        children=[],
    )

    # El bloque exclusivo consiste de todos los ramos de minor y los optativos
    # complementarios
    # Sin embargo, tiene que competir por los ramos con el major y el titulo
    # Por ende, si uno de los ramos cuenta hacia el major/titulo, es necesario tomar un
    # optativo complementario para que el minor exclusivo este completo
    exclusive = Combination(
        debug_name=f"{siding_meta.Nombre} ({minor_credits} créditos exclusivos)",
        block_code=f"{SUPERBLOCK_PREFIX}Minor",
        name=f"{siding_meta.Nombre} (exclusive)",
        cap=minor_credits,
        children=[],
    )

    curr.root.children.append(exhaustive)
    curr.root.children.append(exclusive)

    listbuilder = ListBuilder(out, spec)
    for block in scrape.blocks:
        exh, exc, fill = translate_block(
            courseinfo,
            spec,
            listbuilder,
            block,
            minor_credits,
        )
        if exh:
            exhaustive.children.append(exh)
        exclusive.children.append(exc)
        curr.fillers.setdefault(fill.course.code, []).append(fill)

    out.set_minor(spec, curr)


def translate_block(
    courseinfo: CourseInfo,
    spec: CurriculumSpec,
    listbuilder: ListBuilder,
    block: ScrapedMinorBlock,
    minor_credits: int,
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

    if block.options == ["IEE2XXX"]:
        # Arreglar los optativos de electrica
        block.options = [
            code
            for code in courseinfo.courses
            if code.startswith("IEE2") and len(code) == len("IEE2XXX")
        ]

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
            layer="minor",
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
            order=MINOR_ORDER + listbuilder.last_idx,
        )
    else:
        creds = block.creds
        if block.complementary:
            # El bloque complementario puede rellenar hasta el minor completo
            creds = minor_credits
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
                        f"credits in credit-less equivalence {name} in minor {spec}"
                        " are not homogeneous",
                    )
            creds = representative.credits
        # Agregar esta equivalencia al plan
        equiv = listbuilder.add_list(name, block.options)
        accept_codes = set(block.options)
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
                    layer="minor",
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
            order=MINOR_ORDER + listbuilder.last_idx,
        )
    return exh, exc, fill
