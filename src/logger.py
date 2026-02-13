"""
Centralized structured logging for CuanBot.
Uses loguru for structured, rotated log output.
"""

import sys
from loguru import logger

# Remove default handler
logger.remove()

# Console handler — human-readable
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# File handler — structured JSON logs, rotated
logger.add(
    "/app/logs/cuanbot.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    rotation="10 MB",
    retention="7 days",
    compression="gz",
    level="DEBUG",
    enqueue=True,  # Thread-safe
)


def get_logger(name: str):
    """Get a contextualized logger for a module."""
    return logger.bind(module=name)
