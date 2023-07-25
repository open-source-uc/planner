"""
Logging configuration for the application.
Heavily inspired by https://www.pythonbynight.com/blog/sharpen-your-code
"""

import logging
import sys
from pathlib import Path

from app.settings import settings

DATE_FORMAT = "%y-%b-%d %H:%M:%S"
LOGGER_FILE = Path(settings.log_path)  # where log is stored

SIMPLE_FORMAT = logging.Formatter(
    "%(levelname)s[%(name)s]: \t%(message)s",
    datefmt=DATE_FORMAT,
)

log_level = logging.getLevelNamesMapping()[settings.log_level]


def production_handlers() -> list[logging.Handler]:
    """
    Get a list of log handlers, which redirect log messages to stdout, files, etc...
    For production.
    """

    # Stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(SIMPLE_FORMAT)

    return [stdout_handler]


def debug_handlers() -> list[logging.Handler]:
    """
    Get a list of log handlers, which redirect log messages to stdout, files, etc...
    For staging and development.
    """
    from rich.logging import RichHandler

    output_file_handler = logging.FileHandler(LOGGER_FILE)
    output_file_handler.setFormatter(SIMPLE_FORMAT)

    rich_stdout_handler = RichHandler(
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        show_time=False,
    )
    rich_stdout_handler.setFormatter(
        logging.Formatter("%(name)s: \t%(message)s", datefmt=DATE_FORMAT),
    )

    return [
        rich_stdout_handler,
        output_file_handler,
    ]


def setup_logger():
    """
    Setup logging depending on the environment type (production, staging, development).
    """

    # For all loggers in external libraries,
    for name in logging.root.manager.loggerDict:
        external_logger = logging.getLogger(name)
        # Remove all handlers
        external_logger.handlers = []
        # Enable propagation to the main logger
        external_logger.propagate = True
        # Force a minimum level of `INFO`
        # If we want to debug, we want to debug our code
        min_level = logging.INFO
        if name == "httpx":
            # Special fix for httpx since it spams INFO
            min_level = logging.WARNING
        external_logger.setLevel(max(min_level, log_level))

    handlers = (
        production_handlers() if settings.env == "production" else debug_handlers()
    )

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
    )
