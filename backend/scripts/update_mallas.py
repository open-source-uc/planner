"""
Este script descarga las mallas desde SIDING y las almacena en
`/siding-mock-data/mallas.json`.

Si hay algun cambio en SIDING hay que correr este script nuevamente.
En `/siding-mock-data/README.md` estan las razones por las que es buena idea hacer
manuales las actualizaciones desde SIDING, al menos por ahora.
"""

from pathlib import Path

from app.settings import settings
from app.sync.siding import client as siding_client


async def download_mallas_from_siding():
    settings.siding_mock_path = ""
    settings.siding_record_path = Path("../siding-mock-data/mallas.json")
    siding_client.client.on_startup()
    try:
        # Versions of the curriculum for which to fetch stuff
        cyears = ["C2020", "C2022"]

        # Fetch the major/minor/title offer to ensure it's recorded
        print("fetching major listing")
        majors = await siding_client.get_majors()
        print("fetching minor listing")
        minors = await siding_client.get_minors()
        print("fetching title listing")
        titles = await siding_client.get_titles()
        print(f"fetching associated minors for {len(majors)} majors")
        for major in majors:
            print(f"  loading associations for major {major.CodMajor}")
            await siding_client.get_minors_for_major(major.CodMajor)

        # Fetch all plans
        raw_blocks: list[siding_client.BloqueMalla] = []
        for cyear in cyears:
            print(f"fetching {len(majors)} majors for cyear {cyear}")
            for major in majors:
                print(f"  fetching major {major.CodMajor}")
                raw_blocks.extend(
                    await siding_client.get_curriculum_for_spec(
                        siding_client.PlanEstudios(
                            CodCurriculum=cyear,
                            CodMajor=major.CodMajor,
                            CodMinor="N",
                            CodTitulo="",
                        ),
                    ),
                )
            print(f"fetching {len(minors)} minors for cyear {cyear}")
            for minor in minors:
                print(f"  fetching minor {minor.CodMinor}")
                raw_blocks.extend(
                    await siding_client.get_curriculum_for_spec(
                        siding_client.PlanEstudios(
                            CodCurriculum=cyear,
                            CodMajor="M",
                            CodMinor=minor.CodMinor,
                            CodTitulo="",
                        ),
                    ),
                )
            print(f"fetching {len(titles)} titles for cyear {cyear}")
            for title in titles:
                print(f"  fetching title {title.CodTitulo}")
                raw_blocks.extend(
                    await siding_client.get_curriculum_for_spec(
                        siding_client.PlanEstudios(
                            CodCurriculum=cyear,
                            CodMajor="M",
                            CodMinor="N",
                            CodTitulo=title.CodTitulo,
                        ),
                    ),
                )

        # Find all referenced predefined lists
        predefined_lists: set[str] = set()
        for raw_block in raw_blocks:
            if raw_block.CodLista:
                predefined_lists.add(raw_block.CodLista)

        # Fetch all predefined lists
        print(f"fetching {len(predefined_lists)} predefined lists")
        for lcode in predefined_lists:
            print(f"  fetching predefined list {lcode}")
            await siding_client.get_predefined_list(lcode)
    finally:
        siding_client.client.on_shutdown()


if __name__ == "__main__":
    import asyncio

    asyncio.run(download_mallas_from_siding())
