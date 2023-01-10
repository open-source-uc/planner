from ...settings import settings
from zeep import AsyncClient
from zeep.transports import AsyncTransport
import zeep
import httpx
import os
from typing import Literal, Optional
from pydantic import BaseModel, parse_obj_as

wsdl_url = os.path.join(os.path.dirname(__file__), "ServiciosPlanner.wsdl")

http_client = httpx.AsyncClient(
    auth=httpx.DigestAuth(
        settings.siding_username, settings.siding_password.get_secret_value()
    )
)

soap_client = AsyncClient(wsdl_url, transport=AsyncTransport(http_client))


class StringArrayInner(BaseModel):
    string: list[str]


class StringArray(BaseModel):
    strings: StringArrayInner


class Major(BaseModel):
    CodMajor: str
    Nombre: str
    VersionMajor: str
    Curriculum: StringArray


class Minor(BaseModel):
    CodMinor: str
    Nombre: str
    TipoMinor: Literal["Amplitud"] | Literal["Profundidad"]
    VersionMinor: Optional[str]
    Curriculum: StringArray


class Titulo(BaseModel):
    CodTitulo: str
    Nombre: str
    TipoTitulo: Literal["CIVIL"] | Literal["INDUSTRIAL"]
    VersionTitulo: Optional[str]
    Curriculum: StringArray


class PlanEstudios(BaseModel):
    CodCurriculum: str
    CodMajor: str
    CodMinor: str
    CodTitulo: str


class Curso(BaseModel):
    Sigla: str
    Nombre: str
    # Strings like `I`, `II`, `I y II`, o `None`
    Semestralidad: Optional[str]
    Creditos: int


class ListaCursos(BaseModel):
    Cursos: list[Curso]


class Restriccion(BaseModel):
    Nombre: Optional[str]
    CreditoMin: Optional[str]


class ListaRestricciones(BaseModel):
    Restricciones: list[Restriccion]


class BloqueMalla(BaseModel):
    Nombre: str
    # If set, this block corresponds to a single course
    CodSigla: Optional[str]
    # If set, this block corresponds to a named predefined list of courses
    CodLista: Optional[str]
    Programa: str
    Creditos: int
    # The recommended semester to take this course.
    SemestreBloque: int
    # The order within a semester (?)
    OrdenSemestre: int
    Equivalencias: Optional[ListaCursos]
    # Catedra, catedra y laboratorio, etc
    # A veces simplemente no hay info
    Tipocurso: Optional[str]
    BloqueAcademico: str
    # Seems to always be empty.
    Requisitos: Optional[ListaCursos]
    # Seems to always be empty.
    Restricciones: Optional[ListaRestricciones]


async def get_majors() -> list[Major]:
    """
    Obtain a global list of all majors.
    """
    return parse_obj_as(
        list[Major],
        zeep.helpers.serialize_object(  # type: ignore
            await soap_client.service.getListadoMajor(), dict
        ),
    )


async def get_minors() -> list[Minor]:
    """
    Obtain a global list of all minors.
    """
    return parse_obj_as(
        list[Minor],
        zeep.helpers.serialize_object(  # type: ignore
            await soap_client.service.getListadoMinor(), dict
        ),
    )


async def get_titles() -> list[Titulo]:
    """
    Obtain a global list of all titles.
    """
    return parse_obj_as(
        list[Titulo],
        zeep.helpers.serialize_object(  # type: ignore
            await soap_client.service.getListadoTitulo(), dict
        ),
    )


async def get_minors_for_major(major_code: str) -> list[Minor]:
    """
    Obtain a list of minors that are a valid choice for each major.
    """
    return parse_obj_as(
        list[Minor],
        zeep.helpers.serialize_object(  # type: ignore
            await soap_client.service.getMajorMinorAsociado(major_code), dict
        ),
    )


async def get_courses_for_spec(study_spec: PlanEstudios) -> list[Curso]:
    """
    Get pretty much all the courses that are available to a certain study spec.
    """
    return parse_obj_as(
        list[Curso],
        zeep.helpers.serialize_object(  # type: ignore
            await soap_client.service.getConcentracionCursos(
                CodCurriculum=study_spec.CodCurriculum,
                CodMajor=study_spec.CodMajor,
                CodMinor=study_spec.CodMinor,
                CodTitulo=study_spec.CodTitulo,
            ),
            dict,
        ),
    )


async def get_curriculum_for_spec(study_spec: PlanEstudios) -> list[BloqueMalla]:
    """
    Get a list of curriculum blocks for the given spec.
    """
    return parse_obj_as(
        list[BloqueMalla],
        zeep.helpers.serialize_object(  # type: ignore
            await soap_client.service.getMallaSugerida(
                CodCurriculum=study_spec.CodCurriculum,
                CodMajor=study_spec.CodMajor,
                CodMinor=study_spec.CodMinor,
                CodTitulo=study_spec.CodTitulo,
            ),
            dict,
        ),
    )


async def get_equivalencies(course_code: str, study_spec: PlanEstudios) -> list[Curso]:
    return parse_obj_as(
        list[Curso],
        zeep.helpers.serialize_object(  # type: ignore
            await soap_client.service.getCursoEquivalente(
                Sigla=course_code,
                CodCurriculum=study_spec.CodCurriculum,
                CodMajor=study_spec.CodMajor,
                CodMinor=study_spec.CodMinor,
                CodTitulo=study_spec.CodTitulo,
            ),
            dict,
        ),
    )


async def get_requirements(course_code: str, study_spec: PlanEstudios) -> list[Curso]:
    return parse_obj_as(
        list[Curso],
        zeep.helpers.serialize_object(  # type: ignore
            await soap_client.service.getRequisito(
                Sigla=course_code,
                CodCurriculum=study_spec.CodCurriculum,
                CodMajor=study_spec.CodMajor,
                CodMinor=study_spec.CodMinor,
                CodTitulo=study_spec.CodTitulo,
            ),
            dict,
        ),
    )


async def get_restrictions(
    course_code: str, study_spec: PlanEstudios
) -> list[Restriccion]:
    return parse_obj_as(
        list[Restriccion],
        zeep.helpers.serialize_object(  # type: ignore
            await soap_client.service.getRestriccion(
                Sigla=course_code,
                CodCurriculum=study_spec.CodCurriculum,
                CodMajor=study_spec.CodMajor,
                CodMinor=study_spec.CodMinor,
                CodTitulo=study_spec.CodTitulo,
            ),
            dict,
        ),
    )


async def get_predefined_list(list_code: str) -> list[Curso]:
    return parse_obj_as(
        list[Curso],
        zeep.helpers.serialize_object(  # type: ignore
            await soap_client.service.getListaPredefinida(list_code),
            dict,
        ),
    )


# Missing student endpoints:
# getInfoEstudiante
# getCursosHechos
# getOfertaMajor
# getOfertaMinor
# getOfertaTitulo
