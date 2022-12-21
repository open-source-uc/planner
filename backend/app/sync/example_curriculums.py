from prisma import Json
from prisma.models import CurriculumBlock
from ..plan.validation.curriculum.tree import Combine
import os

import pydantic


async def load_to_database():
    print("loading example curriculums...")
    # Load from json file relative to this file
    ex_path = os.path.join(os.path.dirname(__file__), "example_curriculums.json")
    # Strip comments (to allow example curriculum to have comments)
    raw = ""
    with open(ex_path, "r") as file:
        for line in file.read().splitlines():
            comment_idx = line.find("//")
            if comment_idx != -1:
                line = line[:comment_idx]
            raw += line + "\n"
    # Convert to a list of (kind, block) tuples
    blocks = pydantic.parse_raw_as(list[tuple[str, Combine]], raw)
    print(f"  loaded {len(blocks)} curriculum blocks")
    # Clear previous blocks
    await CurriculumBlock.prisma().delete_many()
    # Put blocks into database
    print("  loading blocks into db...")
    for kind, block in blocks:
        await CurriculumBlock.prisma().create(
            {"kind": kind, "name": block.name, "req": Json(block.dict())}
        )
    print("  done")
