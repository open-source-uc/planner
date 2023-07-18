"""
Logging configuration for the application.
Heavily inspired by https://www.pythonbynight.com/blog/sharpen-your-code
"""

import logging
import sys
from pathlib import Path

from app.settings import settings

DATE_FORMAT = "%y-%b-%d %H:%M:%S"
LOGGER_FORMAT = "%(levelname)s[%(name)s]: \t%(message)s"
LOGGER_FILE = Path(settings.log_path)  # where log is stored


def production_handlers() -> list[logging.Handler]:
    """
    Get a list of log handlers, which redirect log messages to stdout, files, etc...
    For production.
    """

    handler_format = logging.Formatter(LOGGER_FORMAT, datefmt=DATE_FORMAT)

    # Stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(handler_format)

    return [stdout_handler]


def debug_handlers() -> list[logging.Handler]:
    """
    Get a list of log handlers, which redirect log messages to stdout, files, etc...
    For staging and development.
    """
    from rich.logging import RichHandler

    output_file_handler = logging.FileHandler(LOGGER_FILE)
    handler_format = logging.Formatter(LOGGER_FORMAT, datefmt=DATE_FORMAT)
    output_file_handler.setFormatter(handler_format)

    return [
        RichHandler(
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            show_time=False,
        ),
        output_file_handler,
    ]


def setup_logger():
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

    handlers = (
        production_handlers() if settings.env == "production" else debug_handlers()
    )

    logging.basicConfig(
        level=logging.getLevelNamesMapping()[settings.log_level],
        handlers=handlers,
    )
