from __future__ import annotations

import json
import logging
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any, Final, Literal, TypeVar

import httpx
import zeep
from pydantic import BaseModel, ConstrainedStr, Field, parse_obj_as
from zeep import AsyncClient
from zeep.transports import AsyncTransport

from app.plan.validation.curriculum.tree import MajorCode, MinorCode, TitleCode
from app.settings import settings
from app.user.key import Rut


class StringArrayInner(BaseModel):
    string: list[str] | None


class StringArray(BaseModel):
    strings: StringArrayInner


class Major(BaseModel):
    CodMajor: MajorCode
    Nombre: str
    VersionMajor: str
    # For some reason after a SIDING update majors stopped having associated
    # curriculums
    # TODO: This no longer happens with the new version of the webservice
    # Do something about this?
    Curriculum: StringArray | None


Major.update_forward_refs()


class Minor(BaseModel):
    CodMinor: MinorCode
    Nombre: str
    TipoMinor: Literal["Amplitud"] | Literal["Profundidad"]
    VersionMinor: str | None
    # For some reason after a SIDING update minors stopped having associated
    # curriculums
    # TODO: This no longer happens with the new version of the webservice
    # Do something about this?
    Curriculum: StringArray | None


class Titulo(BaseModel):
    CodTitulo: TitleCode
    Nombre: str
    TipoTitulo: Literal["CIVIL"] | Literal["INDUSTRIAL"]
    VersionTitulo: str | None
    # For some reason after a SIDING update titles stopped having associated
    # curriculums
    # TODO: This no longer happens with the new version of the webservice
    # Do something about this?
    Curriculum: StringArray | None


class PlanEstudios(BaseModel):
    CodCurriculum: str
    CodMajor: MajorCode | Literal["M"]
    CodMinor: MinorCode | Literal["N"]
    CodTitulo: TitleCode | Literal[""]


class Curso(BaseModel):
    Sigla: str | None
    Nombre: str | None
    Semestralidad: Literal["I", "II", "I y II"] | None
    Creditos: Annotated[int, Field(ge=0)] | None


class ListaCursos(BaseModel):
    Cursos: list[Curso] | None


class Restriccion(BaseModel):
    Nombre: str | None
    CreditoMin: str | None


class ListaRestricciones(BaseModel):
    Restricciones: list[Restriccion] | None


class ListaRequisitos(BaseModel):
    Cursos: list[Curso] | None


class BloqueMalla(BaseModel):
    Nombre: str
    # If set, this block corresponds to a single course
    CodSigla: str | None
    # If set, this block corresponds to a named predefined list of courses
    CodLista: str | None
    Programa: str
    Creditos: int
    # The recommended semester to take this course.
    SemestreBloque: int
    # The order within a semester (?)
    OrdenSemestre: int
    Equivalencias: ListaCursos | None
    # Catedra, catedra y laboratorio, etc
    # A veces simplemente no hay info
    Tipocurso: str | None
    BloqueAcademico: str | None
    # Seems to always be empty.
    Requisitos: ListaRequisitos | None
    # Seems to always be empty.
    Restricciones: ListaRestricciones | None


class AcademicPeriod(ConstrainedStr):
    regex = r"\d{4}-[1-3]"


class InfoEstudiante(BaseModel):
    # Full name, all uppercase and with Unicode accents.
    Nombre: str
    # Seems to be either 'M' or 'F'.
    # Not used.
    Sexo: str | None
    # The cyear string associated with the student (e.g. "C2020", "C2013", etc...).
    # Usually coupled with `PeriodoAdmision`
    Curriculo: str | None
    # Major code of the self-reported intended major.
    MajorInscrito: MajorCode | None
    # Minor code of the self-reported intended minor.
    MinorInscrito: MinorCode | None
    # Title code of the self-reported intended title.
    TituloInscrito: TitleCode | None
    # Not really sure what this is.
    # Seems to be `None`.
    Codigo: str | None
    # Career
    # Seems to be 'INGENIERÍA CIVIL' (mind the Unicode accent)
    # Not used
    Carrera: str
    # Semester in which the student joined the university.
    # For example, '2012-2' for the second semester of 2012.
    PeriodoAdmision: AcademicPeriod | None
    # Number of semesters coursed?
    # Not sure what are the exact semantics around skipped semesters.
    SemestresCursados: int | None = None

    # Average student grades
    # Since this is somewhat sensitive data and we don't use it, it's best to ignore it

    # Student status
    # Regular students have 'REGULAR' status.
    # Not useful for us, and it may even be sensitive data, so it's best to ignore it


class CursoHecho(BaseModel):
    Sigla: str
    Nombre: str
    Creditos: int
    # Approval status of the course.
    # See the `ESTADO_*` associated constants.
    # TODO: Find out all the codes.
    Estado: str
    # When was the course taken.
    # E.g. "2020-2" for the second semester of the year 2020
    Periodo: AcademicPeriod
    # Not sure, but probably whether the course is catedra or lab.
    # Unused
    TipoCurso: str | None
    # Academic unit, probably.
    # Unused
    UnidadAcademica: str | None

    ESTADO_APROBADO: Final[str] = "Aprobado"
    ESTADO_REPROBADO: Final[str] = "Reprobado"


class CursoInscrito(BaseModel):
    Sigla: str
    Nombre: str
    Creditos: int
    # When was the course taken.
    # E.g. "2020-2" for the second semester of the year 2020
    Periodo: AcademicPeriod
    # Not sure, but probably whether the course is catedra or lab.
    # Unused
    TipoCurso: str | None
    # Academic unit, probably.
    # Unused
    UnidadAcademica: str | None


class SeleccionEstudiante(BaseModel):
    # Codename of the selection.
    # Examples: 'biologico', 'fundamentos', 'exploratorio'
    Selector: str
    # Course code of the selection.
    # I don't know whether empty selections are represented by an empty string or a
    # `None` value.
    Valor: str | None


T = TypeVar("T")


def parse_nullable_list(ty: type[T], value: Any) -> list[T]:  # noqa: ANN401
    if value is None:
        return []
    return parse_obj_as(
        list[ty],
        value,
    )


def decode_cyears(cyears: StringArray | None) -> list[str]:
    if cyears is None:
        return []
    return cyears.strings.string or []


class SoapClient:
    soap_client: AsyncClient | None
    mock_db: dict[str, dict[str, Any]]
    record_path: Path | None

    def __init__(self) -> None:
        self.soap_client = None
        self.mock_db = {}
        self.record_path = None

    def on_startup(self):
        # Load mock data
        if settings.siding_mock_path != "":
            try:
                # Clear mock DB
                self.mock_db = {}
                # Read all files in the index
                file_list: list[str] = json.load(settings.siding_mock_path.open())
                for file_name in file_list:
                    # Load this submock
                    file_path = settings.siding_mock_path.parent.joinpath(file_name)
                    submock: dict[str, dict[str, Any]] = json.load(file_path.open())
                    # Merge submock with main mock DB
                    for endpoint_name, responses in submock.items():
                        db_responses = self.mock_db.setdefault(endpoint_name, {})
                        for request_key, response in responses.items():
                            db_responses[request_key] = response
                # Log that we've finished
                cnt = sum(len(r) for r in self.mock_db.values())
                logging.info(
                    f"Loaded {cnt} SIDING mock responses from"
                    f" '{settings.siding_mock_path}'",
                )
            except (OSError, ValueError) as err:
                logging.error(
                    "Failed to read SIDING mock data from"
                    f" '{settings.siding_mock_path}': {err}",
                )
                self.mock_db = {}

        # Connect to SIDING webservice
        if settings.siding_host_base != "":
            # Load SIDING WebService definition
            wsdl_path = Path(__file__).with_name("ServiciosPlanner.wsdl")
            raw_wsdl_text = wsdl_path.read_text(encoding="utf-8")
            wsdl_text = raw_wsdl_text.replace("SITIO_SIDING", settings.siding_host_base)

            http_client = httpx.AsyncClient(
                auth=httpx.DigestAuth(
                    settings.siding_username,
                    settings.siding_password.get_secret_value(),
                ),
            )
            self.soap_client = AsyncClient(
                BytesIO(wsdl_text.encode()),
                transport=AsyncTransport(http_client),
            )
            logging.info("Connected to live SIDING webservice")

        # Setup response recording
        if settings.siding_record_path != "":
            self.record_path = settings.siding_record_path
            logging.info("Recording SIDING responses")

    async def call_endpoint(
        self,
        name: str,
        args: dict[str, Any],
    ) -> Any:  # noqa: ANN401 (using dynamic typing here is much simpler)
        # Check if request is in mock database
        args_str = json.dumps(args)
        if name in self.mock_db and args_str in self.mock_db[name]:
            return self.mock_db[name][args_str]

        if self.soap_client is None:
            raise Exception(
                f"mock data not found for SIDING request {name}({args_str})",
            )

        # Pack arguments
        args_raw: dict[str, Any] = {}
        if args:
            args_raw["request"] = args

        # Carry out request to SIDING webservice backend
        response: Any = zeep.helpers.serialize_object(  # type: ignore
            await self.soap_client.service[name](**args_raw),
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
                    def default(self, o: Any):  # noqa: ANN401
                        if isinstance(o, Decimal):
                            return float(o)
                        return super().default(o)

                with self.record_path.open("w") as file:
                    json.dump(self.mock_db, file, cls=CustomEncoder, ensure_ascii=False)
            except Exception as err:  # noqa: BLE001 (any error is non-fatal here)
                print(
                    "failed to save recorded SIDING data to"
                    f" '{self.record_path}': {err}",
                )


client = SoapClient()


async def get_majors() -> list[Major]:
    """
    Obtain a global list of all majors.
    """

    # DEBUG: Show raw XML response
    # with soap_client.settings(raw_response=True):
    #     with open("log.txt", "a") as f:
    #         print(resp.content, file=f)

    return parse_nullable_list(
        Major,
        await client.call_endpoint("getListadoMajor", {}),
    )


async def get_minors() -> list[Minor]:
    """
    Obtain a global list of all minors.
    """
    return parse_nullable_list(
        Minor,
        await client.call_endpoint("getListadoMinor", {}),
    )


async def get_titles() -> list[Titulo]:
    """
    Obtain a global list of all titles.
    """
    return parse_nullable_list(
        Titulo,
        await client.call_endpoint("getListadoTitulo", {}),
    )


async def get_minors_for_major(major_code: str) -> list[Minor]:
    """
    Obtain a list of minors that are a valid choice for each major.
    """
    return parse_nullable_list(
        Minor,
        await client.call_endpoint("getMajorMinorAsociado", {"CodMajor": major_code}),
    )


async def get_courses_for_spec(study_spec: PlanEstudios) -> list[Curso]:
    """
    Get pretty much all the courses that are available to a certain study spec.
    """
    return parse_nullable_list(
        Curso,
        await client.call_endpoint(
            "getConcentracionCursos",
            study_spec.dict(),
        ),
    )


async def get_curriculum_for_spec(study_spec: PlanEstudios) -> list[BloqueMalla]:
    """
    Get a list of curriculum blocks for the given spec.
    """
    return parse_nullable_list(
        BloqueMalla,
        await client.call_endpoint(
            "getMallaSugerida",
            study_spec.dict(),
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
    return parse_nullable_list(
        Curso,
        await client.call_endpoint(
            "getCursoEquivalente",
            {
                "Sigla": course_code,
            }
            | study_spec.dict(),
        ),
    )


async def get_requirements(course_code: str, study_spec: PlanEstudios) -> list[Curso]:
    """
    Get the requirements of the given course in the context of the given study spec.
    Note that these requirements are broken, as real Banner requirements are
    represented as a logical expression and not as a list.
    These requirements are only a heuristic.
    """
    return parse_nullable_list(
        Curso,
        await client.call_endpoint(
            "getRequisito",
            {
                "Sigla": course_code,
            }
            | study_spec.dict(),
        ),
    )


async def get_restrictions(
    course_code: str,
    study_spec: PlanEstudios,
) -> list[Restriccion]:
    """
    Get the basic SIDING restriccions as a list.
    This is actually broken, Banner restrictions are represented as a logical
    expression and not as a list.
    """
    return parse_nullable_list(
        Restriccion,
        await client.call_endpoint(
            "getRestriccion",
            {
                "Sigla": course_code,
            }
            | study_spec.dict(),
        ),
    )


async def get_predefined_list(list_code: str) -> list[Curso]:
    """
    Get a global named list of courses.
    Returns `null` if the list is empty.
    """

    return parse_nullable_list(
        Curso,
        await client.call_endpoint("getListaPredefinida", {"CodLista": list_code}),
    )


async def get_student_info(rut: Rut) -> InfoEstudiante:
    """
    Get the information associated with the given student, by RUT.
    """
    return parse_obj_as(
        InfoEstudiante,
        await client.call_endpoint("getInfoEstudiante", {"rut": rut}),
    )


async def get_student_done_courses(rut: Rut) -> list[CursoHecho]:
    """
    Get the information associated with the given student, by RUT.
    """
    return parse_nullable_list(
        CursoHecho,
        await client.call_endpoint("getCursosHechos", {"rut": rut}),
    )


async def get_student_current_courses(rut: Rut) -> list[CursoInscrito]:
    """
    Get the courses that the given student is currently coursing, by RUT.

    Not sure when exactly are current courses converted into past courses.
    """
    return parse_nullable_list(
        CursoInscrito,
        await client.call_endpoint("getCargaAcademica", {"rut": rut}),
    )


async def get_student_selections(rut: Rut) -> list[SeleccionEstudiante]:
    """
    Get the courses that the given student is currently coursing, by RUT.

    Not sure when exactly are current courses converted into past courses.
    """
    return parse_nullable_list(
        SeleccionEstudiante,
        await client.call_endpoint("getSeleccionesEstudiante", {"rut": rut}),
    )


async def get_current_period() -> AcademicPeriod:
    """
    Get the current academic period.

    NOTE: Not sure what happens when in between academic periods.
    This function may error out.
    """
    return parse_obj_as(
        AcademicPeriod, await client.call_endpoint("getPeriodoAcademicoActual", {})
    )


# Missing student endpoints:
# getOfertaMajor
# getOfertaMinor
# getOfertaTitulo
