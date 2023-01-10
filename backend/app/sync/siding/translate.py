"""
Transform the Siding format into something usable.
"""

from . import client
from .client import (
    Major,
    Minor,
    Titulo,
    PlanEstudios,
    Curso as CursoSiding,
)
from prisma.models import (
    Major as DbMajor,
    Minor as DbMinor,
    Title as DbTitle,
    MajorMinor as DbMajorMinor,
)
from ...plan.validation.curriculum.tree import (
    Curriculum,
    CourseList,
    CurriculumSpec,
    Node,
)
import json
import random

_predefined_list_cache: dict[str, list[CursoSiding]] = {}


async def predefined_list(list_code: str) -> list[CursoSiding]:
    if list_code in _predefined_list_cache:
        return _predefined_list_cache[list_code]
    rawlist = await client.get_predefined_list(list_code)
    _predefined_list_cache[list_code] = rawlist
    return rawlist


async def fetch_curriculum_from_siding(spec: CurriculumSpec) -> Curriculum:
    # Fetch raw curriculum blocks for the given cyear-major-minor-title combination
    if spec.major is None or spec.minor is None or spec.title is None:
        raise Exception("blank major/minor/titles are not supported yet")
    raw_blocks = await client.get_curriculum_for_spec(
        PlanEstudios(
            CodCurriculum=spec.cyear,
            CodMajor=spec.major,
            CodMinor=spec.minor,
            CodTitulo=spec.title,
        )
    )

    # Transform into standard blocks
    blocks: list[Node] = []
    for i, raw_block in enumerate(raw_blocks):
        if raw_block.CodLista is not None:
            # Predefined list
            raw_courses = await predefined_list(raw_block.CodLista)
            codes = list(map(lambda c: c.Sigla, raw_courses))
        elif raw_block.CodSigla is not None:
            # Course codes
            codes = [raw_block.CodSigla]
            if raw_block.Equivalencias is not None:
                for equiv in raw_block.Equivalencias.Cursos:
                    codes.append(equiv.Sigla)
        else:
            raise Exception("siding api returned invalid curriculum block")
        course = CourseList(
            name=raw_block.Nombre,
            cap=raw_block.Creditos,
            codes=codes,
            priority=i,
            superblock=raw_block.BloqueAcademico,
        )
        blocks.append(course)

    # TODO: Apply OFG transformation (merge all OFGs into a single 50-credit block, and
    # only allow up to 10 credits of 5-credit sports courses)
    # if cyear == "C2020":
    #     for block in blocks:
    #         if block.name == "Formación General":
    #             # Filter OFG nodes out and count how many credits are required
    #             newchildren: list[Node] = []
    #             ofg_credits = 0
    #             for c in block.children:
    #                 if (
    #                     isinstance(c, CourseList)
    #                     and c.name == "Cursos electivos (Formación general)"
    #                 ):
    #                     ofg_credits += c.cap
    #                 else:
    #                     newchildren.append(c)
    #             # Add OFG node
    #             all_ofg = await predefined_list("L1")
    #             dpt5: list[str] = []
    #             non_dpt5: list[str] = []
    #             for ofg in all_ofg:
    #                 if ofg.Sigla.startswith("DPT") and ofg.Creditos == 5:
    #                     dpt5.append(ofg.Sigla)
    #                 else:
    #                     non_dpt5.append(ofg.Sigla)
    #             newchildren.append(
    #                 Block(
    #                     name="Cursos electivos (Formación general)",
    #                     cap=ofg_credits,
    #                     children=[CourseList(cap=10, codes=dpt5, priority=),
    #                       non_dpt5],
    #                 )
    #             )
    # else:
    #     raise Exception(f"unsupported curriculum year '{cyear}'")

    # TODO: Apply title transformation (130 credits must be exclusive to the title, the
    # rest can be shared)

    return Curriculum(nodes=blocks)


async def fetch_recommended_courses_from_siding(
    spec: CurriculumSpec,
) -> list[list[str]]:
    # Fetch raw curriculum blocks for the given cyear-major-minor-title combination
    if spec.major is None or spec.minor is None or spec.title is None:
        raise Exception("blank major/minor/titles are not supported yet")
    raw_blocks = await client.get_curriculum_for_spec(
        PlanEstudios(
            CodCurriculum=spec.cyear,
            CodMajor=spec.major,
            CodMinor=spec.minor,
            CodTitulo=spec.title,
        )
    )

    # Transform into a list of lists of course codes
    semesters: list[list[str]] = []
    for raw_block in raw_blocks:
        if raw_block.CodLista is not None:
            # TODO: Replace by an ambiguous course
            representative_course = random.choice(
                await predefined_list(raw_block.CodLista)
            ).Sigla
        elif raw_block.CodSigla is not None:
            # TODO: Consider using an ambiguous course for some equivalencies
            representative_course = raw_block.CodSigla
        else:
            raise Exception("invalid siding curriculum block")
        semester_number = raw_block.SemestreBloque
        semester_idx = semester_number - 1  # We use 0-based indices here
        while len(semesters) <= semester_idx:
            semesters.append([])
        semesters[semester_idx].append(representative_course)

    return semesters


async def test_translate():
    print("testing siding api")
    majors: dict[str, Major] = dict(
        map(lambda m: (m.CodMajor, m), await client.get_majors())
    )
    minors: dict[str, Minor] = dict(
        map(lambda m: (m.CodMinor, m), await client.get_minors())
    )
    titles: dict[str, Titulo] = dict(
        map(lambda t: (t.CodTitulo, t), await client.get_titles())
    )
    major_minor: dict[str, list[str]] = {}
    for major in majors:
        assoc = await client.get_minors_for_major(major)
        major_minor[major] = list(map(lambda m: m.CodMinor, assoc))

    plan = PlanEstudios(
        CodCurriculum="C2020", CodMajor="M170", CodMinor="N776", CodTitulo="40082"
    )

    # def random_plan():
    #     c = "C2020"
    #
    #     while True:
    #         maj = random.choice(list(majors.keys()))
    #         if c not in majors[maj].Curriculum.strings.string:
    #             continue
    #         if not major_minor[maj]:
    #             print(f"major {majors[maj]} has no associated minors")
    #             continue
    #         break
    #
    #     while True:
    #         min = random.choice(major_minor[maj])
    #         if c not in minors[min].Curriculum.strings.string:
    #             continue
    #         break
    #
    #     while True:
    #         tit = random.choice(list(titles.keys()))
    #         if c not in titles[tit].Curriculum.strings.string:
    #             continue
    #         break
    #
    #     maj = "M170"
    #     min = "N776"
    #     tit = "40082"
    #
    #     random_plan = PlanEstudios(
    #         CodCurriculum=c,
    #         CodMajor=maj,
    #         CodMinor=min,
    #         CodTitulo=tit,
    #     )
    #     print(f"random plan: {c}-{maj}-{min}-{tit}")
    #     return random_plan

    with open("testclient/plan.json", "w") as file:
        courses = list(
            map(
                lambda c: c.dict(),
                await client.get_courses_for_spec(plan),
            )
        )
        curr = list(
            map(
                lambda b: b.dict(),
                await client.get_curriculum_for_spec(plan),
            )
        )
        json.dump(
            {
                "plan": plan.dict(),
                "major": majors[plan.CodMajor].dict(),
                "minor": minors[plan.CodMinor].dict(),
                "title": titles[plan.CodTitulo].dict(),
                "courses": courses,
                "curr": curr,
            },
            file,
        )

    lists: dict[str, list[CursoSiding]] = {}
    for b in curr:
        lcode = b["CodLista"]
        if lcode is not None and lcode not in lists:
            lists[lcode] = await client.get_predefined_list(lcode)

    with open("testclient/lists.json", "w") as file:
        ser = {}
        for lcode, l in lists.items():
            lser: list[str] = []
            for c in l:
                lser.append(c.Sigla)
            ser[lcode] = lser
        json.dump(ser, file)

    with open("testclient/majors.json", "w") as file:
        ser = {}
        for code, major in majors.items():
            ser[code] = major.dict()
        json.dump(ser, file)
    with open("testclient/minors.json", "w") as file:
        ser = {}
        for code, minor in minors.items():
            ser[code] = minor.dict()
        json.dump(ser, file)
    with open("testclient/titles.json", "w") as file:
        ser = {}
        for code, title in titles.items():
            ser[code] = title.dict()
        json.dump(ser, file)
    with open("testclient/majorminor.json", "w") as file:
        with_name = {}
        for major, m_minors in major_minor.items():
            with_name[f"{major} - {majors[major].Nombre}"] = list(
                map(lambda m: f"{m} - {minors[m].Nombre}", m_minors)
            )
        json.dump(with_name, file)

    cnt = 0
    for c in ["C2013", "C2020", "C2022"]:
        for major in majors.values():
            if c not in major.Curriculum.strings.string:
                continue
            for minor_code in major_minor[major.CodMajor]:
                if c not in minors[minor_code].Curriculum.strings.string:
                    continue
                cnt += len(titles)
    print(f"{cnt} total planspec combinations")

    print("  finished testing")


async def load_offer_to_database():
    """
    Fetch majors, minors and titles.
    """

    print("loading major/minor/title offer to database...")

    print("  clearing previous data")
    await DbMajor.prisma().delete_many()
    await DbMinor.prisma().delete_many()
    await DbTitle.prisma().delete_many()
    await DbMajorMinor.prisma().delete_many()

    print("  loading majors")
    majors = await client.get_majors()
    for major in majors:
        for cyear in major.Curriculum.strings.string:
            await DbMajor.prisma().create(
                data={
                    "cyear": cyear,
                    "code": major.CodMajor,
                    "name": major.Nombre,
                    "version": major.VersionMajor,
                }
            )

    print("  loading minors")
    minors = await client.get_minors()
    for minor in minors:
        for cyear in minor.Curriculum.strings.string:
            await DbMinor.prisma().create(
                data={
                    "cyear": cyear,
                    "code": minor.CodMinor,
                    "name": minor.Nombre,
                    "version": minor.VersionMinor or "",
                    "minor_type": minor.TipoMinor,
                }
            )

    print("  loading titles")
    titles = await client.get_titles()
    for title in titles:
        for cyear in title.Curriculum.strings.string:
            await DbTitle.prisma().create(
                data={
                    "cyear": cyear,
                    "code": title.CodTitulo,
                    "name": title.Nombre,
                    "version": title.VersionTitulo or "",
                    "title_type": title.TipoTitulo,
                }
            )

    print("  loading major-minor associations")
    for major in majors:
        assoc_minors = await client.get_minors_for_major(major.CodMajor)
        for cyear in major.Curriculum.strings.string:
            for minor in assoc_minors:
                if cyear not in minor.Curriculum.strings.string:
                    continue
                await DbMajorMinor.prisma().create(
                    data={
                        "cyear": cyear,
                        "major": major.CodMajor,
                        "minor": minor.CodMinor,
                    }
                )
