import logging
import re
from pathlib import Path

from app.plan.validation.curriculum.tree import MajorCode

log = logging.getLogger("plan-collator")

REGEX_MAJOR_CODE = re.compile(r"\((M\d{3})\)")


def scrape_majors() -> set[MajorCode]:
    log.debug("scraping majors...")

    # Load raw pre-scraped text
    raw = Path("../static-curriculum-data/major-scrape.txt").read_text()

    return {MajorCode(code) for code in REGEX_MAJOR_CODE.findall(raw)}
