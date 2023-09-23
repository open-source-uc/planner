from app.plan.course import EquivalenceId
from app.plan.courseinfo import CourseInfo, EquivDetails
from app.plan.validation.curriculum.tree import (
    Block,
    Combination,
    Curriculum,
    CurriculumSpec,
    FillerCourse,
    Leaf,
)
from app.sync.curriculums.scrape.minor import ScrapedProgram
from app.sync.curriculums.scrape.translate import ProgramType, translate_scrape
from app.sync.curriculums.storage import CurriculumStorage, ProgramDetails
from app.sync.siding.client import BloqueMalla

MINOR_TYPE = ProgramType(
    superblock_id="Minor",
    readable_id="Minor",
    layer_id="minor",
    order_base=100,
    exclusive_credits=None,
)


def translate_minor(
    courseinfo: CourseInfo,
    out: CurriculumStorage,
    spec: CurriculumSpec,
    meta: ProgramDetails,
    siding: list[BloqueMalla],
    scrape: ScrapedProgram,
):
    curr = translate_scrape(
        MINOR_TYPE,
        courseinfo,
        out,
        spec,
        meta.name,
        siding,
        scrape,
    )

    _patch_n290(courseinfo, spec, curr, out)

    out.set_minor(spec, curr)


N290_CREDITS = 50


def _patch_n290(
    courseinfo: CourseInfo,
    spec: CurriculumSpec,
    curr: Curriculum,
    out: CurriculumStorage,
):
    """
    El minor de articulacion de ingenieria civil, N290, consiste de una lista gigante
    de optativos, con algunos grupos de optativos que en conjunto solo pueden sumar 10
    creditos.
    El minor se scrapea como una lista de minimos, y luego se transforma manualmente en
    un super-optativo.
    """

    if spec.minor != "N290":
        return

    equiv_code = f"#MINOR-{spec.major}-{spec.minor}-OPT"

    # Mezclar el listado de ramos del minor en un optativo gigante de 50 creditos
    # Basicamente, transformar un AND en un OR
    for superblock in curr.root.children:
        assert isinstance(superblock, Combination)
        first_child = superblock.children[0]
        assert isinstance(first_child, Leaf)

        # La equivalencia de todos los cursos aceptados por el optativo
        equiv = EquivDetails(
            code=equiv_code,
            is_homogeneous=False,
            is_unessential=False,
            name="Optativos Minor",
            courses=[],
        )

        # Los cursos que no tienen limite conjunto de creditaje
        direct_requirements = Leaf(
            debug_name="Optativos Minor (genérico)",
            block_code=f"courses:{equiv_code}",
            name=None,
            cap=N290_CREDITS,
            codes={equiv_code},
            layer=first_child.layer,
        )

        # Los cursos que se encuentran "sueltos" se agregan directamente a
        # `direct_requirements`
        # En cambio, los cursos agrupados bajo una equivalencia se mantienen dentro de
        # sus respectivos bloques, de manera que se respeten las limitantes de creditos
        new_blocks: list[Block] = [direct_requirements]
        for block in superblock.children:
            assert isinstance(block, Leaf)
            if len(block.codes) == 1:
                course_code = next(iter(block.codes))
                direct_requirements.codes.add(course_code)
                equiv.courses.append(course_code)
            else:
                block.codes = {
                    code for code in block.codes if courseinfo.try_course(code)
                }
                new_blocks.append(block)
                equiv.courses.extend(block.codes)
                block.codes.add(equiv_code)

        # Actualizar el superbloque resultante
        superblock.cap = N290_CREDITS
        superblock.children = new_blocks

        out.lists[equiv_code] = equiv

    # Arreglar los cursos de relleno, para que se recomienden optativos en lugar de
    # cursos concretos
    curr.fillers.clear()
    for i in range(_ceil_div(N290_CREDITS, 10)):
        curr.fillers.setdefault(equiv_code, []).append(
            FillerCourse(
                course=EquivalenceId(code=equiv_code, credits=10),
                order=MINOR_TYPE.order_base + i,
            ),
        )


def _ceil_div(a: int, b: int) -> int:
    return -(a // -b)
