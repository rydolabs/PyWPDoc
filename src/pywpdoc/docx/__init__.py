"""Backend-specific DOCX API.

The current backend is python-docx based.  The public PyWPDoc namespace is
kept separate so the backend can be replaced later without changing the
high-level entry point.
"""
from pywpdoc._engine.docx import *  # noqa: F401,F403
from pywpdoc._engine.docx import __all__
