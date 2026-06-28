"""
logger.py — centralised logging setup.

All modules call `setup_logger(__name__)` to get a consistently formatted logger.
"""

import logging
import sys


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Return a logger with a clean, timestamped format.

    Uses a StreamHandler to stdout so output is visible both locally
    and in containerised / cloud environments (stdout → CloudWatch, etc.).
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if the module is imported multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False  # prevent duplicate output from root logger
    return logger


# Convenience: a ready-to-use project-level logger
log = setup_logger("telecom_assistant")
