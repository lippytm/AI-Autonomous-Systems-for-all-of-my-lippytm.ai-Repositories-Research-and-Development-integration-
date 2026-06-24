"""
Structured logging for AI Autonomous Systems.
"""
import logging
import sys
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Return a logger configured with a consistent format.

    Args:
        name: Logger name (typically ``__name__`` of the calling module).
        level: Optional log level override (e.g. ``"DEBUG"``).

    Returns:
        Configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    if level:
        logger.setLevel(level.upper())
    elif not logger.level:
        logger.setLevel(logging.INFO)

    return logger
