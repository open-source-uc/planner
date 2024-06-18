"""
Procesar el texto que define los minors en el plan de estudios.

El codigo de este archivo esta muy acoplado con la definicion de titulos de la UC.
Idealmente, esto sera reemplazado en algun momento por una definicion central y completa
de los programas de estudio.

Notar que este codigo solo se encarga de traducir el texto mas o menos en formato humano
a un formato mas computacional.
La conversion al formato estandar de planner se hace en otro paso.

Un detalle particular de los minors es que se especifican por separado en varios PDFs.
Los minors de profundidad estan listados en el PDF del major asociado.
Los minors de amplitud estan listados todos juntos en un PDF.
Estos PDFs son de 2 columnas, por lo que requieren mayor intervencion manual para
scrapearlos correctamente.
"""

import logging
import re
from pathlib import Path

from app.plan.courseinfo import CourseDetails
from app.plan.validation.curriculum.tree import MajorCode, MinorCode
from app.sync.curriculums.scrape.common import ScrapedBlock, ScrapedProgram

log = logging.getLogger("plan-collator")

# Usado para separar el archivo scrapeado en bloques por cada minor.
REGEX_MINOR_CODE = re.compile(r"(?:(M\d{3})-)?(N[\d]{3}(?:-\d)?)\)")
# Usado para separar el texto para un minor en bloques, donde cada bloque representa uno
# o mas ramos
REGEX_BLOCK_SPLITTER = re.compile(
    r"(?P<split>"
    r"(?:Mínimo)"
    r"|(?P<nonexc>\(nonexclusive\))"
    r"|(?:(?:(?:[Aa]probar)|(?:Elegir)|(?:Optativos))"
    r" (?P<cr1>\d+) cr(?P<comp1>[^\n]*\(b\))?)"
    r"|(?:Optativos ?(?:Complementarios)? ?(?P<comp2>\(b\)))"
    r"|(?P<bad>Optativos(?:(?: [^\d\(C])|\n))"
    r")",
)
# Describe que representa cada capture group del regex anterior
REGEX_SPLITTER_GROUPS = ["split", "nonexc", "cr", "comp", "comp", "bad", "txt"]
# Identifica un codigo de curso
# Usado para extraer los cursos de cada bloque
REGEX_COURSE_CODE = re.compile(r"([A-Z]{3}\d[\dX]{2}[\dA-Z]?)( o)?")
# Identifica un codigo de facultad
# Usado cuando un bloque especifica cosas como "cualquier curso IEE nivel 3000"
REGEX_FACULTY_CODE = re.compile(r"(?:^|\W)([A-Z]{3})(?:\W|$)")
# Usado para detectar cuando un minor exige "elegir x creditos de cada area"
REGEX_DETECT_EACH_AREA = re.compile("de cada[^\n]+ área")
# Usado para detectar cuando un minor tiene requisitos extraños relacionados con areas
# Si se detecta este regex y no se manejó previamente, algo anda mal
REGEX_DETECT_AREA_FALLBACK = re.compile(r"de [^\n]+ área")
# Identifica el nombre de una area
# Usado para delimitar las areas cuando un minor exige separar por area
REGEX_IDENTIFY_AREA = re.compile(r"(?:^|\n)(Área [^\n\(]+)")


def scrape_minors(
    courses: dict[str, CourseDetails],
) -> dict[MinorCode, list[ScrapedProgram]]:
    log.debug("scraping minors...")

    # Load raw pre-scraped text
    raw = Path("../static-curriculum-data/minor-amplitud-scrape.txt").read_text()
    raw += Path("../static-curriculum-data/minor-profundidad-scrape.txt").read_text()

    # Separar el texto por cada minor, identificando el comienzo del texto que describe
    # a un minor por su codigo
    raw_by_minor = REGEX_MINOR_CODE.split(raw)
    raw_by_minor.pop(0)  # Erase any junk before the first minor

    # Procesar cada minor independientemente
    minors: dict[MinorCode, list[ScrapedProgram]] = {}
    for major_code, minor_code, minor_raw in zip(
        raw_by_minor[::3],
        raw_by_minor[1::3],
        raw_by_minor[2::3],
        strict=True,
    ):
        minor_code = MinorCode(minor_code)
        if major_code is not None:
            major_code = MajorCode(major_code)
        minors.setdefault(minor_code, []).append(
            scrape_minor(courses, minor_code, minor_raw, major_code),
        )

    log.debug("processed %s minors", len(minors))
    log.debug("RECORDAR CHEQUEAR QUE ESTEN TODOS LOS OPTATIVOS COMPLEMENTARIOS")
    log.debug("NO HAY FORMA AUTOMATIZADA DE CHEQUEARLO")
    return minors


def scrape_minor(
    courses: dict[str, CourseDetails],
    code: MinorCode,
    raw: str,
    major_code: MajorCode | None,
) -> ScrapedProgram:
    log.debug("scraping minor '%s'", code)
    out = ScrapedProgram(
        code=code,
        assoc_major=major_code,
        assoc_minor=code,
        assoc_title=None,
        blocks=[],
    )

    split_by_block = REGEX_BLOCK_SPLITTER.split(raw)
    if REGEX_COURSE_CODE.search(split_by_block[0]):
        log.warning(
            "text before first block is not empty, ignoring courses %s",
            REGEX_COURSE_CODE.findall(split_by_block[0]),
        )
    split_by_block.pop(0)

    # Procesar cada bloque
    for i in range(0, len(split_by_block), len(REGEX_SPLITTER_GROUPS)):
        # Recolectar los distintos captures del regex para este bloque
        block_captures = [
            split_by_block[j] for j in range(i, i + len(REGEX_SPLITTER_GROUPS))
        ]

        creds, complementary, nonexclusive, block_raw = _extract_block_metadata(
            block_captures,
        )

        if not block_raw:
            # Este bloque no tiene texto (y por ende no tiene cursos)
            continue

        if creds is None and complementary:
            # Hay optativos complementarios opcionales, y tambien hay optativos normales
            # que en caso de ser necesarios doblan como optativos complementarios
            # Si un optativo complementario no tiene creditos, entonces es opcional y
            # por ende tiene 0 creditos
            creds = 0

        if REGEX_DETECT_EACH_AREA.search(block_raw):
            # Este bloque es del tipo "escoger x creditos de cada area"
            # Por ende, hay que generar un optativo para cada area, y distribuir la
            # cantidad apropiada de creditos a cada area
            areas = REGEX_IDENTIFY_AREA.split(block_raw)
            if REGEX_COURSE_CODE.search(areas[0]):
                log.warning(
                    "first area in area-block is not empty, ignoring %s",
                    REGEX_COURSE_CODE.findall(areas[0]),
                )
            areas.pop(0)
            for area_name, area_raw in zip(areas[::2], areas[1::2], strict=True):
                log.debug(f"        processing area {area_name}")
                process_block(
                    courses,
                    out,
                    creds,
                    complementary,
                    nonexclusive,
                    area_raw,
                    area_name,
                )
        else:
            # Un curso o optativo
            process_block(
                courses,
                out,
                creds,
                complementary,
                nonexclusive,
                block_raw,
                None,
            )

    sanity_check_minor(courses, out)

    return out


def _extract_block_metadata(
    block_captures: list[str | None],
) -> tuple[int | None, bool, bool, str]:
    creds = None
    complementary = False
    nonexclusive = False
    block_raw = None
    for kind, capture in zip(REGEX_SPLITTER_GROUPS, block_captures, strict=True):
        if capture is None:
            continue
        if kind == "cr":
            # Este bloque tiene un creditaje asociado
            creds = int(capture)
        elif kind == "nonexc":
            # Este bloque es no-exclusivo
            # Esto significa que el creditaje de estos cursos no importa, solo
            # importa que se tomen en algun bloque (posiblemente como OFG)
            nonexclusive = True
        elif kind == "comp":
            # Este bloque representa un optativo complementario
            complementary = True
        elif kind == "bad":
            # Este bloque representa un optativo sin creditos (!)
            # Hay que arreglarlo a mano lamentablemente
            creds = 999
        elif kind == "txt":
            # El texto en bruto asociado a este bloque
            # Contiene los ramos que componen al bloque
            block_raw = capture.strip()
        elif kind == "split":
            # Un divisor
            # No se usa por ahora
            pass
        else:
            raise Exception("unreachable")
    return creds, complementary, nonexclusive, block_raw or ""


def process_block(
    courses: dict[str, CourseDetails],
    out: ScrapedProgram,
    creds: int | None,
    complementary: bool,
    nonexclusive: bool,
    raw: str,
    name: str | None,
):
    # Si hay alguna frase mencionando areas, probablemente hay un requisito que no se
    # esta manejando
    has_unhandled_area = REGEX_DETECT_AREA_FALLBACK.search(raw)
    if has_unhandled_area:
        simplified_text = raw.replace("\n", "")
        log.warning(
            "minor contains '%s' in block \"%s\"",
            has_unhandled_area[0],
            simplified_text,
        )

    course_codes = REGEX_COURSE_CODE.findall(raw)

    if "nivel 3000" in raw:
        # Si el bloque dice algo parecido a "cualquier curso nivel 3000", agregarlos
        add_level_3000_courses(courses, course_codes, raw)

    # Identificar cuando no hay cursos en el bloque
    if not course_codes:
        simplified_text = raw.replace("\n", " ")
        if re.match(r"^[A-ZÁÉÍÓÚ\s]+\d\.\d$", simplified_text):
            # Evitar algunos nombres de bloque que producen demasiados falsos positivos
            return
        log.warning("minor has empty block '''%s'''", simplified_text)
        return

    # Identificar los optativos que no indican la cantidad de creditos
    # Hay que arreglar manualmente estos optativos!
    # Por eso emitimos un error aca
    if creds == 999:
        log.error(
            "credit-less optative %s found in minor %s,"
            " assuming %s creds. you should manually fix it",
            name,
            out.code,
            creds,
        )

    if creds is None:
        # Si no se especifican creditos, este bloque probablemente consiste de una lista
        # de varios cursos
        # Muchas veces estos cursos estan conectados con operadores 'o', que representan
        # que los dos cursos son equivalentes (y de cierta forma son un optativo con 2
        # o mas opciones realmente)
        i = 0
        while i < len(course_codes):
            # Generar un nuevo bloque para este ramo
            main_code, or_operator = course_codes[i]
            block = ScrapedBlock(
                creds=None,
                options=[main_code],
                name=name,
                complementary=complementary,
                nonexclusive=nonexclusive,
            )
            # Agregar al bloque cualquier ramo encadenado con 'o's
            while or_operator:
                i += 1
                code, or_operator = course_codes[i]
                block.options.append(code)
                if (
                    code in courses
                    and main_code in courses
                    and courses[code].credits != courses[main_code].credits
                ):
                    log.warning(
                        "block with codes %s has nonhomogeneous credits",
                        block.options,
                    )
            i += 1
            out.blocks.append(block)
    else:
        # Si se especifican creditos, entonces este bloque es una disyuncion que permite
        # rellenar con cualquiera de una lista de ramos
        block = ScrapedBlock(
            creds=creds,
            options=[],
            name=name,
            complementary=complementary,
            nonexclusive=nonexclusive,
        )
        for code, or_operator in course_codes:
            if or_operator:
                log.warning(
                    "course %s in equivalence %s in minor %s has 'o' operator",
                    code,
                    name or "?",
                    out.code,
                )
            block.options.append(code)
        out.blocks.append(block)


def add_level_3000_courses(
    courses: dict[str, CourseDetails],
    course_codes: list[tuple[str, str | None]],
    raw: str,
):
    faculty_codes = set(REGEX_FACULTY_CODE.findall(raw))
    if faculty_codes:
        # Printear cual es el texto que triggereo esta operacion, para identificar
        # mas facilmente operaciones que no tienen sentido
        reference_text = REGEX_COURSE_CODE.split(raw)[-1].replace("\n", " ")
        log.debug(
            "        adding level 3000 courses of faculties %s to block",
            faculty_codes,
        )
        if course_codes:
            log.debug(f"            on top of {len(course_codes)} explicit courses")
        log.debug(f'            based on text "{reference_text}"')

        # Buscar los cursos con el codigo especificado y nivel 3000
        extra_courses: list[tuple[str, str | None]] = []
        for course_code in courses:
            if (
                len(course_code) >= 4
                and course_code[3] == "3"
                and course_code[:3] in faculty_codes
            ):
                extra_courses.append((course_code, None))
        extra_courses[-1] = (extra_courses[-1][0], None)
        course_codes.extend(extra_courses)
    else:
        log.warning(
            "the text instructs to add level 3000 courses"
            ", but it does not specify any 3-letter code",
        )


def sanity_check_minor(courses: dict[str, CourseDetails], minor: ScrapedProgram):
    """
    Hacer un sanity-check del minor.
    Esta funcion no modifica el minor, solo emite diagnosticos al log si algo falla.
    """

    minor_credits = 0
    complementary_blocks = 0
    optatives = 0
    for block in minor.blocks:
        if block.nonexclusive:
            continue
        if block.complementary:
            # Complementary block
            complementary_blocks += 1
        if block.creds is None:
            # Concrete course
            minor_credits += courses[block.options[0]].credits
        else:
            # Optative course
            minor_credits += block.creds
            if len(block.options) > 1:
                optatives += 1

    # Chequear que la cantidad de creditos haga sentido
    if minor_credits != 50:
        log.warning(
            "minor %s has %s credits, normally minors have 50 credits",
            minor.code,
            minor_credits,
        )

    # Chequear que no hayan demasiados optativos complementarios
    if complementary_blocks > 1:
        log.warning(
            "minor %s has %s complementary blocks, expected 0 or 1",
            minor.code,
            complementary_blocks,
        )
