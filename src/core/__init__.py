"""
Core package init.
"""
from .config import Config
from .logger import get_logger

__all__ = ["Config", "get_logger"]
