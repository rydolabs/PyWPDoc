"""Backend-specific HWPX API.

0.44.x intentionally reuses the verified 0.44.x HWPX backend without moving
its implementation, so the namespace migration itself cannot alter output.
"""
from pywpdoc._engine.hwpx import *  # noqa: F401,F403
from pywpdoc._engine.hwpx import __all__
