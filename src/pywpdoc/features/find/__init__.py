"""Independent high-level text search feature."""
from .api import find
from .model import FindMatch

__all__ = ["find", "FindMatch"]
