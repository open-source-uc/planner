"""
Logging configuration for the application.
Heavily inspired by https://www.pythonbynight.com/blog/sharpen-your-code
"""

import logging
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.settings import settings

LOGGER_FORMAT = "%(message)s"
LOGGER_FILE = Path(settings.log_path)  # where log is stored
DATE_FORMAT = "%d %b %Y | %H:%M:%S"


class LoggerConfig(BaseModel):
    handlers: list[Any]
    format: str = ""
    date_format: str | None = None
    logger_file: Path | None = None
    level: str = settings.log_level


@lru_cache
def get_logger_config():
    """Installs RichHandler (Rich library) if not in production
    environment, or use the production log configuration.
    """

    if settings.env != "production":
        from rich.logging import RichHandler

        output_file_handler = logging.FileHandler(LOGGER_FILE)
        handler_format = logging.Formatter(LOGGER_FORMAT, datefmt=DATE_FORMAT)
        output_file_handler.setFormatter(handler_format)

        return LoggerConfig(
            handlers=[
                RichHandler(
                    rich_tracebacks=True,
                    tracebacks_show_locals=True,
                    show_time=False,
                ),
                output_file_handler,
            ],
            format="",
            date_format=DATE_FORMAT,
            logger_file=LOGGER_FILE,
        )

    handler_format = logging.Formatter(LOGGER_FORMAT, datefmt=DATE_FORMAT)

    # Stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(handler_format)

    return LoggerConfig(
        handlers=[stdout_handler],
        format="%(levelname)s: \t%(message)s",
        date_format="%d-%b-%y %H:%M:%S",
        logger_file=LOGGER_FILE,
    )


def setup_rich_logger():
    """Cycles through uvicorn root loggers to
    remove handler, then runs `get_logger_config()`
    to populate the `LoggerConfig` class with Rich
    logger parameters.
    """

    # Remove all handlers from root logger
    # and proprogate to root logger.
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    logger_config = get_logger_config()  # get Rich logging config

    logging.basicConfig(
        level=logger_config.level,
        format=logger_config.format,
        datefmt=logger_config.date_format,
        handlers=logger_config.handlers,
    )
