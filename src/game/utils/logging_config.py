"""Utility helpers for configuring logging across the project."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from loguru import logger


_DEFAULT_LOG_LEVEL = "INFO"
_LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}"


def _ensure_log_directory(log_dir: Path) -> None:
    """Create the log directory if it does not already exist."""
    log_dir.mkdir(parents=True, exist_ok=True)


def setup_logging(log_dir: str | os.PathLike[str] = "logs",
                  level: str = _DEFAULT_LOG_LEVEL) -> logger.__class__:
    """Configure Loguru and return the configured logger.

    The previous version of the project configured logging directly inside
    ``game.py``.  As part of the refactor we centralise the configuration so
    that any entry-point (CLI, tests, interactive session) can obtain a
    consistently configured logger.

    Parameters
    ----------
    log_dir:
        Directory where the rotating log files will be written.
    level:
        Minimum severity for the stderr handler.
    """
    # Remove existing handlers so that repeated calls don't duplicate logs.
    logger.remove()

    log_path = Path(log_dir)
    _ensure_log_directory(log_path)

    # File handler – keep the verbose information for diagnostics.
    logger.add(
        log_path / "pokemon_{time}.log",
        rotation="1 week",
        enqueue=True,
        backtrace=True,
        diagnose=True,
        format=_LOG_FORMAT,
    )

    # Stream handler – make the console a bit less noisy by default.
    logger.add(
        logging.StreamHandler(),
        level=level,
        backtrace=True,
        diagnose=True,
        format=_LOG_FORMAT,
    )

    return logger


__all__ = ["setup_logging"]
