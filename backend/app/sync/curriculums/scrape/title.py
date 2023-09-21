"""
Procesar el texto del plan de estudios que define los titulos.

El codigo de este archivo esta muy acoplado con la definicion de titulos de la UC.
Idealmente, esto sera reemplazado en algun momento por una definicion central y completa
de los programas de estudio.

Notar que este codigo solo se encarga de traducir el texto mas o menos en formato humano
a un formato mas computacional.
La conversion al formato estandar de planner se hace en otro paso.
"""

import logging
import re
from pathlib import Path

from app.plan.courseinfo import CourseInfo
from app.sync.curriculums.scrape.common import ScrapedBlock, ScrapedProgram

log = logging.getLogger("plan-collator")

# Usado para separar el archivo de texto enorme en bloques por codigo de titulo.
REGEX_TITLE_CODE = re.compile(r"\(([\d]{5}(?:-\d)?)\)")

# Usado para separar el bloque de OPIs del resto de la definicion del titulo
REGEX_OPI_SPLITTER = re.compile(r"Bloque Optativos \(d\)")

# Usado para separar entre bloques del titulo
REGEX_BLOCK_SPLITTER = re.compile(
    r"(?:Elegir (\d+) cr)|(?:Especialidad)|(?:BLOQUE)|(?:Mínimos)|(?:Minimos)",
)

# Utilizado para reconocer los codigos de curso que componen un bloque
REGEX_COURSE_CODE = re.compile(r"([A-Z]{3}\d{3}[\dA-Z]?)( o)?")

# Usado para reconocer codigos de facultad
# Por ejemplo, algunas listas de curso dicen "cualquier curso IEE nivel 3000"
REGEX_FACULTY_CODE = re.compile(r"(?:^|\W)([A-Z]{3})(?:\W|$)")

# Usado para identificar de manera fuzzy si el titulo tiene una disyuncion de area
# El codigo tiene casos especiales para cuando el titulo indica "de cada area", pero
# este regex es mas general, detecta cualquier frase de la forma "de x area".
# Si se detecta este regex y no se maneja especialmente, probablemente algo anda mal
REGEX_DETECT_AREA = re.compile(r"cr de [^\n]+ área")

# Usado para identificar los nombres de las areas y delimitarlas, una vez que se
# identifica que un titulo contiene areas
REGEX_IDENTIFY_AREA = re.compile(r"Área \d+: ([^\n\(]+)")


def scrape_titles(courseinfo: CourseInfo) -> dict[str, ScrapedProgram]:
    log.debug("scraping titles...")

    # Load raw pre-scraped text
    raw = Path("../static-curriculum-data/title-scrape.txt").read_text()

    # Split raw text into raw text for each title
    raw_by_title = REGEX_TITLE_CODE.split(raw)
    raw_by_title.pop(0)  # Remove junk before first title code

    titles: dict[str, ScrapedProgram] = {}
    for title_code, title_raw in zip(
        raw_by_title[::2],
        raw_by_title[1::2],
        strict=True,
    ):
        titles[title_code] = scrape_title(courseinfo, title_code, title_raw)

    return titles


def scrape_title(courseinfo: CourseInfo, code: str, raw: str) -> ScrapedProgram:
    log.debug("scraping title '%s'", code)
    out = ScrapedProgram(code=code, blocks=[])

    # Eliminar la practica 2, no nos interesa
    raw = raw.replace("ING2001", "")

    # Eliminar los cursos GOB
    raw = remove_standard_gob(code, raw)

    # Eliminar la seccion de OPIs
    raw = REGEX_OPI_SPLITTER.split(raw)[0]

    # Separar por bloques
    raw_by_block = REGEX_BLOCK_SPLITTER.split(raw)
    course_in_first_block = REGEX_COURSE_CODE.search(raw_by_block[0])
    if course_in_first_block:
        # Si hay cursos antes del primer bloque, eliminar el ruido antes del primer
        # codigo de curso
        raw_by_block[0] = raw_by_block[0][course_in_first_block.start() :]
        raw_by_block.insert(0, (None, None))
    else:
        # Si no hay cursos antes del primer bloque, es solo ruido para nosotros
        # Lo podemos eliminar sin remordimientos
        raw_by_block.pop(0)

    # Procesar cada bloque independientemente
    for creds, block_raw in zip(raw_by_block[::2], raw_by_block[1::2], strict=True):
        block_raw = block_raw.strip()
        if not block_raw:
            continue

        if "de cada área" in block_raw:
            areas_raw = REGEX_IDENTIFY_AREA.split(block_raw)
            areas_raw.pop(0)
            for name, area_raw in zip(areas_raw[::2], areas_raw[1::2], strict=True):
                log.debug("        processing area %s", name)
                scrape_block(courseinfo, out, creds, area_raw, name)
        else:
            has_de_cada = REGEX_DETECT_AREA.search(block_raw)
            if has_de_cada:
                simplified_text = block_raw.replace("\n", " ")
                log.warning(
                    "title contains '%s' in block \"%s\"",
                    has_de_cada[0],
                    simplified_text,
                )
            scrape_block(courseinfo, out, creds, block_raw, None)

    return out


def scrape_block(
    courseinfo: CourseInfo,
    out: ScrapedProgram,
    creds_str: str | None,
    raw: str,
    name: str | None,
):
    # Parse credits
    # Determinar si un bloque es una equivalencia a partir de si tiene creditos
    # asignados o no
    # Si tiene creditos asignados, es una equivalencia
    # Si no, es un curso
    creds = None if creds_str is None else int(creds_str)

    course_codes: list[tuple[str, str | None]] = REGEX_COURSE_CODE.findall(raw)
    if "nivel 3000" in raw:
        # Si el bloque dice algo parecido a "cualquier curso nivel 3000", agregarlos
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
            for course_code in courseinfo.courses:
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

    # Identificar cuando no hay cursos en el bloque
    if not course_codes:
        simplified_text = raw.replace("\n", " ")
        if re.match(r"^[A-ZÁÉÍÓÚ\s]+\d\.\d$", simplified_text):
            # Evitar algunos nombres de bloque que producen demasiados falsos positivos
            return
        log.warning("title has empty block '''%s'''", simplified_text)
        return

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
                complementary=False,
            )
            # Agregar al bloque cualquier ramo encadenado con 'o's
            while or_operator:
                i += 1
                code, or_operator = course_codes[i]
                block.options.append(code)
                if (
                    code in courseinfo.courses
                    and main_code in courseinfo.courses
                    and courseinfo.courses[code].credits
                    != courseinfo.courses[main_code].credits
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
        block = ScrapedBlock(creds=creds, options=[], name=name, complementary=False)
        for code, or_operator in course_codes:
            if or_operator:
                log.warning("course in equivalence has 'o' operator: %s", course_codes)
            block.options.append(code)
        out.blocks.append(block)


def remove_standard_gob(code: str, txt: str):
    """
    Asegurarse que no haya cambiado esto y eliminarlo, es solo ruido para efectos
    practicos.
    """
    stdtxt = (
        "Gobierno: GOB3001, GOB3004, GOB3006, GOB3007, GOB3008, GOB3009"
        ", GOB3010, GOB3011 Y GOB3012."
    )
    if stdtxt not in txt.replace("\n", " "):
        raise Exception(f"nonstandard GOB for title {code}")
    return txt.replace("GOB", "")
