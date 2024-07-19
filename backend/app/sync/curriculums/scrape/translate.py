import logging

from pydantic import BaseModel
from unidecode import unidecode

from app.plan.course import ConcreteId, EquivalenceId
from app.plan.courseinfo import CourseDetails, EquivDetails
from app.plan.validation.curriculum.tree import (
    Combination,
    Curriculum,
    CurriculumSpec,
    FillerCourse,
    Leaf,
)
from app.sync.curriculums.scrape.common import ScrapedBlock, ScrapedProgram
from app.sync.curriculums.siding import SidingInfo
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
    Create lists, finding an appropiate code that corresponds from the SIDING lists, or
    a custom code otherwise.
    """

    id_prefix: str
    unique_prefix: str
    storage: CurriculumStorage
    added_lists: int
    sequential_id: int
    optative_idx: int
    minimum_idx: int
    siding_lists: dict[str, list[str]]
    siding_list_assignment: dict[str, set[str]]

    def __init__(
        self,
        kind: ProgramType,
        storage: CurriculumStorage,
        spec: CurriculumSpec,
        siding_info: SidingInfo,
        siding: list[BloqueMalla],
    ) -> None:
        self.id_prefix = kind.layer_id.upper()
        self.unique_prefix = f"{self.id_prefix}-{spec}"
        self.storage = storage
        self.added_lists = 0
        self.sequential_id = 0
        self.optative_idx = 0
        self.minimum_idx = 0

        # Find all lists from SIDING, to find matching codes
        self.siding_lists = {}
        for bloque in siding:
            if bloque.CodSigla is not None:
                equivalents: list[str] = [bloque.CodSigla]
                if bloque.Equivalencias is not None:
                    for equivalent in bloque.Equivalencias.Cursos or []:
                        if equivalent.Sigla is not None:
                            equivalents.append(equivalent.Sigla)
                if len(equivalents) > 1:
                    self.siding_lists[f"EQUIV-{bloque.CodSigla}"] = equivalents
            if bloque.CodLista is not None:
                siding_list = siding_info.lists.get(bloque.CodLista)
                courses_in_list: list[str] = []
                if siding_list is not None:
                    for course in siding_list:
                        if course.Sigla is not None:
                            courses_in_list.append(course.Sigla)
                if len(courses_in_list) > 0:
                    self.siding_lists[f"LIST-{bloque.CodLista}"] = courses_in_list
        self.siding_list_assignment = {}

        # Warn if there is no SIDING info
        # TODO: All of these warnings will require manual migration once SIDING adds
        # these plans
        # Alternatively, we could just kill all old plans for these minors/titles
        if len(self.siding_lists) == 0:
            log.warn("no SIDING info available for %s, using unique list IDs", spec)

    def add_list(self, name: str, courses: list[str]) -> EquivDetails:
        # Find the best match from the SIDING list, if possible
        best_list_codes = sorted(
            self.siding_lists,
            key=lambda lcode: self.rate_siding_list(lcode, courses),
        )
        if len(courses) == 1:
            # Single-course lists are special
            # There may not be a SIDING code attached to them
            if best_list_codes and self.siding_lists[best_list_codes[0]] == courses:
                # Okay, use this code
                pass
            else:
                # There is no exact match, synthesize a list with one course
                best_list_codes = []
        else:
            # If a list code is already assigned to a different set of courses, use the
            # next best list code
            while (
                best_list_codes
                and best_list_codes[0] in self.siding_list_assignment
                and self.siding_list_assignment[best_list_codes[0]] != set(courses)
            ):
                # The best siding code was used, try with the next best
                cannot_use = best_list_codes.pop(0)

                # Warn that the best code could not be used
                next_to_try = best_list_codes[0] if best_list_codes else None
                log.warn(
                    "best siding code for %s in spec %s (%s courses) is"
                    " %s (%s missing courses, %s extra courses)"
                    ", but it was already used%s",
                    name,
                    self.unique_prefix,
                    len(courses),
                    cannot_use,
                    len(set(courses).difference(self.siding_lists[cannot_use])),
                    len(set(self.siding_lists[cannot_use]).difference(courses)),
                    f", trying with {next_to_try} next" if next_to_try else "",
                )

        if len(best_list_codes) > 0:
            # Use the SIDING code
            best_list_code = best_list_codes[0]
            lcode = f"{self.id_prefix}-{best_list_code}"
            self.siding_list_assignment[best_list_code] = set(courses)

            missing = set(courses).difference(self.siding_lists[best_list_code])
            if missing:
                log.warn(
                    "siding list %s that was assigned to %s in spec %s (%s courses)"
                    " is missing %s and has %s extra courses",
                    best_list_code,
                    name,
                    self.unique_prefix,
                    len(courses),
                    len(missing),
                    len(set(self.siding_lists[best_list_code]).difference(courses)),
                )
        elif len(courses) == 1:
            # Synthesize a single-course list
            lcode = f"{self.id_prefix}-{courses[0]}"
        else:
            # Use a synthetic code instead
            # The synthetic codes are built from a prefix unique to this curriculum
            # spec and a sequence number
            # These will probably break in the future :(
            self.sequential_id += 1
            lcode = f"{self.unique_prefix}-{self.sequential_id}"

            if len(self.siding_lists) > 0:
                log.warn(
                    "no siding list codes available for courses %s in spec %s"
                    ", so we're using synthetic ID %s",
                    courses,
                    self.unique_prefix,
                    lcode,
                )
            else:
                # There are no SIDING lists, so all equivalences will produce this
                # warning, even though we already warned about the absence of SIDING
                # lists
                # Just spare the noise
                pass

        equiv = EquivDetails(
            code=lcode,
            name=name,
            is_homogeneous=len(courses) <= 1,
            is_unessential=False,
            courses=courses,
        )
        if lcode in self.storage.lists and equiv != self.storage.lists[lcode]:
            log.warn(
                "duplicated lists with code %s: (%s) vs (%s)",
                lcode,
                equiv,
                self.storage.lists[lcode],
            )
        self.storage.lists[lcode] = equiv
        self.added_lists += 1
        return equiv

    def rate_siding_list(self, siding_code: str, equiv_courses: list[str]) -> int:
        """
        Rate how good is a particular siding list code for a set of courses.
        Lower scores are better.

        Calculated as K * |courses - siding| - |siding - courses|.
        That is, missing courses in the SIDING list weight K times more than extra
        courses in the SIDING list.
        """
        siding_set = set(self.siding_lists[siding_code])
        equiv_set = set(equiv_courses)
        return 3 * len(equiv_set.difference(siding_set)) + len(
            siding_set.difference(equiv_set),
        )

    def next_optative(self) -> int:
        self.optative_idx += 1
        return self.optative_idx

    def next_minimum(self) -> int:
        self.minimum_idx += 1
        return self.minimum_idx


def get_credits_of_block(
    courses: dict[str, CourseDetails],
    block: ScrapedBlock,
    spec: CurriculumSpec,
    name: str,
):
    credits = None
    for code in block.options:
        if code not in courses:
            log.warn(
                "program %s defines the amount of credits of block %s"
                " based on unknown course %s",
                spec,
                name,
                code,
            )
            continue
        if credits is None:
            credits = courses[code].credits
        elif credits != courses[code].credits:
            log.warn(
                "inconsistent amount of credits for block %s of program %s:"
                " %s != %s",
                name,
                spec,
                credits,
                courses[code].credits,
            )
    if credits is None:
        log.error(
            "program %s contains block %s with no known course options ?!",
            spec,
            name,
        )
    return credits


def translate_scrape(
    kind: ProgramType,
    courses: dict[str, CourseDetails],
    out: CurriculumStorage,
    spec: CurriculumSpec,
    name: str,
    siding_info: SidingInfo,
    siding: list[BloqueMalla],
    scrape: ScrapedProgram,
) -> Curriculum:
    curr = Curriculum.empty(spec)
    curr.root.cap = -1

    if kind.exclusive_credits is None:
        # Determinar cuantos creditos tiene el programa
        # Los optativos complementarios de 0 creditos obviamente no aportan en esta
        # cuenta
        exclusive_credits = 0
        for block in scrape.blocks:
            if block.nonexclusive:
                continue
            if block.creds is not None:
                # Un optativo con un creditaje fijo
                exclusive_credits += block.creds
            else:
                # La cantidad de creditos viene dada implicitamente por el ramo
                credits = get_credits_of_block(courses, block, spec, name)
                if credits is not None:
                    exclusive_credits += credits

    else:
        # Una cantidad fija de creditos exclusivos (ie. el titulo)
        exclusive_credits = kind.exclusive_credits

    # El bloque exhaustivo consiste de todos los ramos de minor, pero sin optativos
    # complementarios
    # Ademas, es independiente del major y titulo, de manera que los ramos puedan
    # compartirse entre minor exhaustivo y major/titulo
    exhaustive = Combination(
        debug_name=name,
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
        name=kind.readable_id,
        cap=exclusive_credits,
        children=[],
    )

    curr.root.children.append(exhaustive)
    curr.root.children.append(exclusive)

    # Convertir un optativo complementario con creditaje no-nulo en un optativo normal
    # con creditaje y un optativo complementario sin creditaje
    complementary_blocks: list[ScrapedBlock] = []
    for block in scrape.blocks:
        if block.complementary and block.creds is not None and block.creds > 0:
            creditless_copy = block.copy()
            creditless_copy.creds = 0
            complementary_blocks.append(creditless_copy)
            block.complementary = False
    scrape.blocks.extend(complementary_blocks)

    # Convertir bloque por bloque
    listbuilder = ListBuilder(kind, out, spec, siding_info, siding)
    for block in scrape.blocks:
        exh, exc, fills = translate_block(
            courses,
            kind,
            spec,
            listbuilder,
            block,
            exclusive_credits,
        )
        if exh:
            exhaustive.children.append(exh)
        if exc:
            exclusive.children.append(exc)
        for fill in fills:
            curr.fillers.setdefault(fill.course.code, []).append(fill)

    return curr


def translate_block(
    courses: dict[str, CourseDetails],
    kind: ProgramType,
    spec: CurriculumSpec,
    listbuilder: ListBuilder,
    block: ScrapedBlock,
    exclusive_credits: int,
) -> tuple[Leaf | None, Leaf | None, list[FillerCourse]]:
    # Encontrar un buen nombre para el bloque
    if block.name is not None:
        # El bloque tiene nombre, usar este nombre
        name = block.name
    elif len(block.options) == 1 and block.options[0] in courses:
        # El bloque tiene un único curso, usar el nombre del curso
        info = courses[block.options[0]]
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

    # Convertir pseudocodigos como IEE2XXX en listas concretas
    _apply_course_patches(courses, block.options)

    if block.creds is None and len(block.options) == 1:
        # Agregar este curso al plan
        code = block.options[0]
        info = courses[code]
        equiv = listbuilder.add_list(name, block.options)
        exh = Leaf(
            debug_name=name,
            name=name,
            superblock=kind.superblock_id,
            cap=info.credits or 1,
            list_code=equiv.code,
            codes={code},
            layer=kind.layer_id,
        )
        exc = Leaf(
            debug_name=name,
            name=name,
            superblock=kind.superblock_id,
            cap=info.credits or 1,
            list_code=equiv.code,
            codes={code},
        )
        fill = [
            FillerCourse(
                course=ConcreteId(
                    code=code,
                    equivalence=EquivalenceId(code=equiv.code, credits=info.credits),
                ),
                order=kind.order_base + listbuilder.added_lists,
            ),
        ]
    else:
        creds = block.creds
        filler_creds = None
        cost_offset = 0
        if block.complementary:
            # El bloque complementario puede rellenar hasta el minor completo
            creds = exclusive_credits
            filler_creds = 10
            cost_offset = 1
        if creds is None:
            # Si no hay informacion de creditos, se supone que todas las opciones
            # tienen el mismo creditaje
            assert block.options
            representative = courses[block.options[0]]
            for code in block.options:
                info = courses[code]
                if info.credits != representative.credits:
                    raise Exception(
                        f"credits in credit-less equivalence {name} in"
                        f" {kind.superblock_id} {spec} are not homogeneous",
                    )
            creds = representative.credits
        if filler_creds is None:
            filler_creds = creds

        # Filtrar las opciones que no estan en la base de datos de cursos
        available_options: list[str] = []
        for code in block.options:
            if code not in courses:
                log.warning(f"unknown course {code} in scrape of {spec}")
                continue
            available_options.append(code)

        # Agregar esta equivalencia al plan
        equiv = listbuilder.add_list(name, available_options)
        exh = (
            None
            if block.complementary
            else (
                Leaf(
                    debug_name=name,
                    name=name,
                    superblock=kind.superblock_id,
                    cap=creds,
                    list_code=equiv.code,
                    codes=set(available_options),
                    layer=kind.layer_id,
                )
            )
        )
        exc = (
            None
            if block.nonexclusive
            else Leaf(
                debug_name=name,
                name=name,
                superblock=kind.superblock_id,
                cap=creds,
                list_code=equiv.code,
                codes=set(available_options),
            )
        )
        fill = [
            FillerCourse(
                course=EquivalenceId(code=equiv.code, credits=filler_creds),
                order=kind.order_base + listbuilder.added_lists,
                cost_offset=cost_offset,
            )
            for _ in range(_ceil_div(creds, filler_creds))
        ]
    return exh, exc, fill


def _apply_course_patches(allcourses: dict[str, CourseDetails], courses: list[str]):
    if "IEE2XXX" in courses:
        # Arreglar los optativos de electrica
        courses.remove("IEE2XXX")
        courses.extend(
            code
            for code in allcourses
            if code.startswith("IEE2") and len(code) == len("IEE2XXX")
        )

    if "IDI999X" in courses:
        # Optativo de N242 "Tecnologico de Profundizacion"
        # Definido como:
        # Investigación o Proyecto
        # Trabajo Personal Dirigido
        # Otro curso Tecnológico de Profundización
        #
        # Con una notita (e) que dice:
        # "Aprobar 10 créditos entre el listado de cursos optativos ofrecidos por la
        # Escuela de Ingeniería o Instituto vinculado a la Escuela de Ingeniería y
        # aprobados por el Comité de Pregrado de la Escuela."
        #
        # Segun informacion sacada en reuniones, esto se ve estudiante por estudiante,
        # asique mientras no tengamos acceso a los planes personalizados solo podemos
        # ser conservadores.
        # TODO: Fix this once we have student-custom plans
        courses.remove("IDI999X")
        courses.extend(
            course.code
            for course in allcourses.values()
            if unidecode(course.school) == "Ingenieria"
            and (
                "Investigacion o Proyecto" in unidecode(course.name)
                or "Trabajo Personal Dirigido" in unidecode(course.name)
            )
        )


def _ceil_div(a: int, b: int):
    return -(a // -b)
