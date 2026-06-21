"""Logging setup for UTF-8 daily CommitCraft log files."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from .config import CONFIG_DIR, DEFAULT_LOG_LEVEL, validate_log_level


LOGGER_NAME = "commitcraft"
LOG_DIR = CONFIG_DIR / "logs"
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"


def setup_logging(level: str = DEFAULT_LOG_LEVEL) -> Path:
    """Configure the project logger and return today's log file path."""

    normalized_level = validate_log_level(level)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"commitcraft-{datetime.now().strftime('%Y-%m-%d')}.log"
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, normalized_level))
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)
    logger.info("Logging initialized at level %s", normalized_level)
    return log_path


def get_logger() -> logging.Logger:
    """Return the shared CommitCraft logger."""

    return logging.getLogger(LOGGER_NAME)
