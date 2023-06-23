import json
import os
from decimal import Decimal
from typing import Any, Literal, Optional

import httpx
import zeep
from pydantic import BaseModel, parse_obj_as
from zeep import AsyncClient
from zeep.transports import AsyncTransport

from ...settings import settings


class StringArrayInner(BaseModel):
    string: list[str]


class StringArray(BaseModel):
    strings: StringArrayInner


class Major(BaseModel):
    CodMajor: str
    Nombre: str
    VersionMajor: str
    # For some reason after a SIDING update majors stopped having associated
    # curriculums
    # TODO: Learn why and what to do about it
    Curriculum: Optional[StringArray]


class Minor(BaseModel):
    CodMinor: str
    Nombre: str
    TipoMinor: Literal["Amplitud"] | Literal["Profundidad"]
    VersionMinor: Optional[str]
    # For some reason after a SIDING update minors stopped having associated
    # curriculums
    # TODO: Learn why and what to do about it
    Curriculum: Optional[StringArray]


class Titulo(BaseModel):
    CodTitulo: str
    Nombre: str
    TipoTitulo: Literal["CIVIL"] | Literal["INDUSTRIAL"]
    VersionTitulo: Optional[str]
    # For some reason after a SIDING update titles stopped having associated
    # curriculums
    # TODO: Learn why and what to do about it
    Curriculum: Optional[StringArray]


class PlanEstudios(BaseModel):
    CodCurriculum: str
    CodMajor: str
    CodMinor: str
    CodTitulo: str


class Curso(BaseModel):
    Sigla: str
    Nombre: Optional[str]
    # Strings like `I`, `II`, `I y II`, o `None`
    Semestralidad: Optional[str]
    Creditos: Optional[int]


class ListaCursos(BaseModel):
    Cursos: list[Curso]


class Restriccion(BaseModel):
    Nombre: Optional[str]
    CreditoMin: Optional[str]


class ListaRestricciones(BaseModel):
    Restricciones: list[Restriccion]


class ListaRequisitos(BaseModel):
    Cursos: list[Curso]


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
    Requisitos: Optional[ListaRequisitos]
    # Seems to always be empty.
    Restricciones: Optional[ListaRestricciones]


class InfoEstudiante(BaseModel):
    # Full name, all uppercase and with Unicode accents.
    Nombre: str
    # Either 'M' or 'F'.
    Sexo: str
    # The cyear string associated with the student (e.g. "C2020", "C2013", etc...).
    # Usually coupled with `PeriodoAdmision`
    Curriculo: str
    # Major code of the self-reported intended major.
    MajorInscrito: Optional[str]
    # Minor code of the self-reported intended minor.
    MinorInscrito: Optional[str]
    # Title code of the self-reported intended title.
    TituloInscrito: Optional[str]
    # Not really sure what this is.
    # Seems to be `None`.
    Codigo: Optional[str]
    # Career
    # Should be 'INGENIERÍA CIVIL' (mind the Unicode accent)
    Carrera: str
    # Semester in which the student joined the university.
    # For example, '2012-2' for the second semester of 2012.
    PeriodoAdmision: str

    # Average student grades
    # Since this is somewhat sensitive data and we don't use it, it's best to ignore it
    # PPA: Decimal

    # Student status
    # Regular students have 'REGULAR' status.
    # Not useful for us, and it may even be sensitive data, so it's best to ignore it
    # Estado: str


class CursoHecho(BaseModel):
    Sigla: str
    Nombre: str
    Creditos: int
    # Approval status of the course.
    # Codified as a string, with different strings representing different statuses.
    # For example, '12' seems to be "approved".
    # TODO: Find out all the codes.
    Estado: str
    # When was the course taken.
    # E.g. "2020-2" for the second semester of the year 2020
    Periodo: str
    # Not sure, but probably whether the course is catedra or lab.
    # Seems to be `None`
    TipoCurso: Optional[str]
    # Academic unit, probably.
    # Seems to be `None`
    UnidadAcademica: Optional[str]


class SoapClient:
    soap_client: Optional[AsyncClient]
    mock_db: dict[str, dict[str, Any]]
    record_path: Optional[str]

    def __init__(self):
        self.soap_client = None
        self.mock_db = {}
        self.record_path = None

    def on_startup(self):
        # Load mockup data
        if settings.siding_mock_path != "":
            try:
                with open(settings.siding_mock_path, "r") as file:
                    self.mock_db = json.load(file)
                cnt = sum(map(lambda r: len(r), self.mock_db.values()))
                print(
                    f"loaded {cnt} SIDING mock responses from"
                    + f" '{settings.siding_mock_path}'"
                )
            except Exception as err:
                print(
                    "failed to read SIDING mock data from"
                    + f" '{settings.siding_mock_path}': {err}"
                )
                self.mock_db = {}

        # Connect to SIDING webservice
        if settings.siding_username != "":
            wsdl_url = os.path.join(os.path.dirname(__file__), "ServiciosPlanner.wsdl")
            http_client = httpx.AsyncClient(
                auth=httpx.DigestAuth(
                    settings.siding_username,
                    settings.siding_password.get_secret_value(),
                )
            )
            self.soap_client = AsyncClient(
                wsdl_url,
                transport=AsyncTransport(http_client),
            )
            print("connected to live SIDING webservice")

        # Setup response recording
        if settings.siding_record_path != "":
            self.record_path = settings.siding_record_path
            print("recording SIDING responses")

    async def call_endpoint(self, name: str, args: dict[str, Any]) -> Any:
        # Check if request is in mock database
        args_str = json.dumps(args)
        if name in self.mock_db:
            if args_str in self.mock_db[name]:
                return self.mock_db[name][args_str]

        if self.soap_client is None:
            raise Exception(
                f"mock data not found for SIDING request {name}({args_str})"
            )

        # Carry out request to SIDING webservice backend
        response: Any = zeep.helpers.serialize_object(  # type: ignore
            await self.soap_client.service[name](**args)
        )

        # Record response if enabled
        if self.record_path is not None:
            self.mock_db.setdefault(name, {})[args_str] = response

        return response

    def on_shutdown(self):
        if self.record_path is not None:
            print(f"saving recorded SIDING responses to '{self.record_path}'")
            try:

                class CustomEncoder(json.JSONEncoder):
                    def default(self, o: Any):
                        if isinstance(o, Decimal):
                            return float(o)
                        return super().default(o)

                with open(self.record_path, "w") as file:
                    json.dump(self.mock_db, file, cls=CustomEncoder)
            except Exception as err:
                print(
                    "failed to save recorded SIDING data to"
                    + f" '{self.record_path}': {err}"
                )


client = SoapClient()


async def get_majors() -> list[Major]:
    """
    Obtain a global list of all majors.
    """

    # DEBUG: Show raw XML response
    # with soap_client.settings(raw_response=True):
    #     resp = await soap_client.service.getListadoMajor()
    #     with open("log.txt", "a") as f:
    #         print(resp.content, file=f)

    return parse_obj_as(
        list[Major],
        await client.call_endpoint("getListadoMajor", {}),
    )


async def get_minors() -> list[Minor]:
    """
    Obtain a global list of all minors.
    """
    return parse_obj_as(
        list[Minor],
        await client.call_endpoint("getListadoMinor", {}),
    )


async def get_titles() -> list[Titulo]:
    """
    Obtain a global list of all titles.
    """
    return parse_obj_as(
        list[Titulo],
        await client.call_endpoint("getListadoTitulo", {}),
    )


async def get_minors_for_major(major_code: str) -> list[Minor]:
    """
    Obtain a list of minors that are a valid choice for each major.
    """
    return parse_obj_as(
        list[Minor],
        await client.call_endpoint("getMajorMinorAsociado", {"CodMajor": major_code}),
    )


async def get_courses_for_spec(study_spec: PlanEstudios) -> list[Curso]:
    """
    Get pretty much all the courses that are available to a certain study spec.
    """
    return parse_obj_as(
        list[Curso],
        await client.call_endpoint(
            "getConcentracionCursos",
            {
                "CodCurriculum": study_spec.CodCurriculum,
                "CodMajor": study_spec.CodMajor,
                "CodMinor": study_spec.CodMinor,
                "CodTitulo": study_spec.CodTitulo,
            },
        ),
    )


async def get_curriculum_for_spec(study_spec: PlanEstudios) -> list[BloqueMalla]:
    """
    Get a list of curriculum blocks for the given spec.
    """
    return parse_obj_as(
        list[BloqueMalla],
        await client.call_endpoint(
            "getMallaSugerida",
            {
                "CodCurriculum": study_spec.CodCurriculum,
                "CodMajor": study_spec.CodMajor,
                "CodMinor": study_spec.CodMinor,
                "CodTitulo": study_spec.CodTitulo,
            },
        ),
    )


async def get_equivalencies(course_code: str, study_spec: PlanEstudios) -> list[Curso]:
    """
    Get all courses that are equivalent to the given course in the context of the given
    study spec.

    Note that equivalencies are not commutative.
    In particular, this method is intended only to be called on courses of a study plan.
    If a curriculum block specifies 'FIS1514', it may also accept its equivalents.
    For example, 'FIS1514' has 3 equivalencies, including 'ICE1514'.
    However, 'ICE1514' has zero equivalencies.
    """
    return parse_obj_as(
        list[Curso],
        await client.call_endpoint(
            "getCursoEquivalente",
            {
                "Sigla": course_code,
                "CodCurriculum": study_spec.CodCurriculum,
                "CodMajor": study_spec.CodMajor,
                "CodMinor": study_spec.CodMinor,
                "CodTitulo": study_spec.CodTitulo,
            },
        ),
    )


async def get_requirements(course_code: str, study_spec: PlanEstudios) -> list[Curso]:
    """
    Get the requirements of the given course in the context of the given study spec.
    Note that these requirements are broken, as real Banner requirements are
    represented as a logical expression and not as a list.
    These requirements are only a heuristic.
    """
    return parse_obj_as(
        list[Curso],
        await client.call_endpoint(
            "getRequisito",
            {
                "Sigla": course_code,
                "CodCurriculum": study_spec.CodCurriculum,
                "CodMajor": study_spec.CodMajor,
                "CodMinor": study_spec.CodMinor,
                "CodTitulo": study_spec.CodTitulo,
            },
        ),
    )


async def get_restrictions(
    course_code: str, study_spec: PlanEstudios
) -> list[Restriccion]:
    """
    Get the basic SIDING restriccions as a list.
    This is actually broken, Banner restrictions are represented as a logical
    expression and not as a list.
    """
    return parse_obj_as(
        list[Restriccion],
        await client.call_endpoint(
            "getRestriccion",
            {
                "Sigla": course_code,
                "CodCurriculum": study_spec.CodCurriculum,
                "CodMajor": study_spec.CodMajor,
                "CodMinor": study_spec.CodMinor,
                "CodTitulo": study_spec.CodTitulo,
            },
        ),
    )


async def get_predefined_list(list_code: str) -> list[Curso]:
    """
    Get a global named list of courses.
    """
    return parse_obj_as(
        list[Curso],
        await client.call_endpoint("getListaPredefinida", {"CodLista": list_code}),
    )


async def get_student_info(rut: str) -> InfoEstudiante:
    """
    Get the information associated with the given student, by RUT.
    The RUT must be in the format "011222333-K", the same format used by CAS.
    """
    return parse_obj_as(
        InfoEstudiante,
        await client.call_endpoint("getInfoEstudiante", {"rut": rut}),
    )


async def get_student_done_courses(rut: str) -> list[CursoHecho]:
    """
    Get the information associated with the given student, by RUT.
    The RUT must be in the format "011222333-K", the same format used by CAS.
    """
    return parse_obj_as(
        list[CursoHecho], await client.call_endpoint("getCursosHechos", {"rut": rut})
    )


# Missing student endpoints:
# getOfertaMajor
# getOfertaMinor
# getOfertaTitulo
