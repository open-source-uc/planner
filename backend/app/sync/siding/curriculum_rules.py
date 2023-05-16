"""
En este archivo se concentran las transformaciones sobre las mallas que debemos hacer,
pero que no estan especificadas por SIDING de forma computer-readable, y por ende
tenemos que implementar en Python.

Como este codigo es especifico a SIDING y probablemente tenga que ser tocado por otra
gente en un futuro, los comentarios estan en español al contrario del resto del codigo.

Cuando aparezca una nueva version del curriculum con reglas especificas, este codigo es
el que habra que tocar.
"""

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
        l1_creds = 0
        l1_block = None
        for block in superblock.children:
            if not isinstance(block, Leaf):
                continue
            if block.original_code == "!L1":
                l1_creds += block.cap
                l1_block = block
        if l1_block is not None:
            superblock.children = list(
                filter(
                    lambda block: not (
                        isinstance(block, Leaf)
                        and block.original_code == "!L1"
                        and block is not l1_block
                    ),
                    superblock.children,
                )
            )
            l1_block.cap = l1_creds


async def apply_curriculum_rules(
    courseinfo: CourseInfo, spec: CurriculumSpec, curriculum: Curriculum
) -> Curriculum:

    _skip_extras(curriculum)
    _merge_ofgs(curriculum)

    match spec.cyear.raw:
        case "C2020":
            # TODO: Cuentan como maximo 2 ramos DPT de 5 creditos distintos como OFG
            # TODO: Los ramos de seleccion deportiva pueden contar 2 veces la misma
            #   sigla
            # TODO: El titulo tiene que tener 130 creditos exclusivos
            #   Recordar incluir los optativos (ramos de ing nivel 3000) y IPres
            pass
    return curriculum
