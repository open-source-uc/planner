from pydantic import BaseModel

from app.plan.validation.curriculum.tree import MajorCode, MinorCode, TitleCode


class ScrapedBlock(BaseModel):
    """
    - name: Name of the block. Might not be available for all blocks.
    - creds: Amount of credits that this block weights. Might not be available if the
    block consists of a single course.
    - options: The course codes that this block admits.
    - complementary: Whether the block is a complementary minor/title course or not.
    - nonexclusive: The opposite of a complementary block. It's required that these
    courses are taken, but they may count towards another block.
    """

    name: str | None
    creds: int | None
    options: list[str]
    complementary: bool
    nonexclusive: bool


class ScrapedProgram(BaseModel):
    code: str
    assoc_major: MajorCode | None
    assoc_minor: MinorCode | None
    assoc_title: TitleCode | None
    blocks: list[ScrapedBlock]
