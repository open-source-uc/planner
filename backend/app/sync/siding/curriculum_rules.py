"""
En este archivo se concentran las transformaciones sobre las mallas que debemos hacer,
pero que no estan especificadas por SIDING de forma computer-readable, y por ende
tenemos que implementar en Python.

Como este codigo es especifico a SIDING y probablemente tenga que ser tocado por otra
gente en un futuro, los comentarios estan en español al contrario del resto del codigo.

Cuando aparezca una nueva version del curriculum con reglas especificas, este codigo es
el que habra que tocar.
"""

from ...plan.plan import PseudoCourse
from ...plan.validation.curriculum.tree import (
    Combination,
    Curriculum,
    CurriculumSpec,
    Leaf,
)
from ...plan.courseinfo import CourseInfo


def _skip_extras(curriculum: Curriculum):
    # Saltarse los superbloques que solamente contienen bloques de 0 creditos (en
    # realidad, 1 credito fantasma)
    # Elimina el superbloque "Requisitos adicionales para obtener el grado de
    # Licenciado..."
    curriculum.root.children = list(
        filter(
            lambda superblock: not (
                isinstance(superblock, Combination)
                and all(map(lambda block: block.cap == 1, superblock.children))
            ),
            curriculum.root.children,
        )
    )


def _merge_ofgs(curriculum: Curriculum):
    # Junta los bloques de OFG de 10 creditos en un bloque grande de OFG
    # El codigo de lista para los OFG es `!L1`
    for superblock in curriculum.root.children:
        if not isinstance(superblock, Combination):
            continue
        l1_blocks: list[Leaf] = []
        for block in superblock.children:
            if not isinstance(block, Leaf):
                continue
            if len(block.fill_with) > 0 and block.fill_with[0][1].code == "!L1":
                l1_blocks.append(block)
        if len(l1_blocks) > 0:
            superblock.children = list(
                filter(
                    lambda block: not (
                        isinstance(block, Leaf) and block.fill_with[0][1].code == "!L1"
                    ),
                    superblock.children,
                )
            )
            total_cap = sum(map(lambda block: block.cap, l1_blocks))
            fill_with: list[tuple[int, PseudoCourse]] = []
            for block in l1_blocks:
                fill_with.extend(block.fill_with)
            fill_with.sort(key=lambda priority_course: priority_course[0], reverse=True)
            superblock.children.append(
                Leaf(
                    name=l1_blocks[0].name,
                    cap=total_cap,
                    fill_with=fill_with,
                    codes=l1_blocks[0].codes,
                )
            )


def _allow_selection_duplication(courseinfo: CourseInfo, curriculum: Curriculum):
    # Los ramos de seleccion deportiva pueden contar hasta 2 veces (la misma sigla!)
    # Los ramos de seleccion deportiva se definen segun SIDING como los ramos DPT que
    # comienzan con "Seleccion"
    for superblock in curriculum.root.children:
        if not isinstance(superblock, Combination):
            continue
        for block in superblock.children:
            if (
                isinstance(block, Leaf)
                and len(block.fill_with) > 0
                and block.fill_with[0][1].code == "!L1"
            ):
                for code in block.codes.keys():
                    if not code.startswith("DPT"):
                        continue
                    info = courseinfo.try_course(code)
                    if info is None:
                        continue
                    if (
                        info.name.startswith("Seleccion ")
                        or info.name.startswith("Selección ")
                    ):
                        block.codes[code] = 2


def _limit_ofg10(courseinfo: CourseInfo, curriculum: Curriculum):
    # https://intrawww.ing.puc.cl/siding/dirdes/web_docencia/pre_grado/formacion_gral/alumno_2020/index.phtml
    # En el bloque de OFG hay algunos cursos de 5 creditos que en conjunto pueden
    # contribuir a lo mas 10 creditos:
    # - DPT (deportivos)
    # - RII (ingles)
    # - CAR (CARA)
    # - OFG plan antiguo (MEB158, MEB166 y MEB174)
    # TODO: Que significa esta linea:
    #   "Además, es válido para avance curricular de OFG máximo 1 curso optativo en
    #   ciencias (10 cr.) de una lista de cursos Optativos de Ciencia, o su equivalente,
    #   definida por el Comité Curricular de la Escuela de Ingeniería."

    def is_limited(courseinfo: CourseInfo, code: str):
        info = courseinfo.try_course(code)
        if info is None:
            return False
        if info.credits != 5:
            return False
        return (
            code.startswith("DPT")
            or code.startswith("RII")
            or code.startswith("CAR")
            or code == "MEB158"
            or code == "MEB166"
            or code == "MEB174"
        )

    for superblock in curriculum.root.children:
        if not isinstance(superblock, Combination):
            continue
        for block_i, block in enumerate(superblock.children):
            if (
                isinstance(block, Leaf)
                and len(block.fill_with) > 0
                and block.fill_with[0][1].code == "!L1"
            ):
                # Segregar los cursos de 5 creditos que cumplan los requisitos
                limited = {}
                unlimited = {}
                for code, mult in block.codes.items():
                    if is_limited(courseinfo, code):
                        limited[code] = mult
                    else:
                        unlimited[code] = mult
                # Separar el bloque en 2
                limited_block = Leaf(cap=10, codes=limited)
                unlimited_block = Leaf(cap=block.cap, codes=unlimited)
                block = Combination(
                    name=block.name,
                    cap=block.cap,
                    fill_with=block.fill_with,
                    children=[
                        limited_block,
                        unlimited_block,
                    ],
                )
                superblock.children[block_i] = block


async def apply_curriculum_rules(
    courseinfo: CourseInfo, spec: CurriculumSpec, curriculum: Curriculum
) -> Curriculum:

    _skip_extras(curriculum)

    match spec.cyear.raw:
        case "C2020":
            # NOTE: El orden en que se llaman estas funciones es importante
            _merge_ofgs(curriculum)
            _allow_selection_duplication(courseinfo, curriculum)
            _limit_ofg10(courseinfo, curriculum)
            # TODO: El titulo tiene que tener 130 creditos exclusivos
            #   Recordar incluir los optativos (ramos de ing nivel 3000) y IPres
            pass
    return curriculum
