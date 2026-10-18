"""Adapter for an external Microsoft Open XML SDK validator command.

The current execution environment does not ship the .NET SDK.  Release CI can
provide a small validator executable and point ``PYWPDOC_OPENXML_VALIDATOR`` to
it.  Keeping this adapter separate prevents the runtime package from depending
on .NET while still making external schema validation a first-class gate.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import subprocess


@dataclass(frozen=True)
class ExternalValidationResult:
    available: bool
    ok: bool
    command: tuple[str, ...] = ()
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None


def validate_with_openxml_sdk(path: str | Path) -> ExternalValidationResult:
    configured = os.environ.get("PYWPDOC_OPENXML_VALIDATOR", "").strip()
    if not configured:
        return ExternalValidationResult(available=False, ok=False)

    command = [*shlex.split(configured), str(Path(path))]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return ExternalValidationResult(
        available=True,
        ok=completed.returncode == 0,
        command=tuple(command),
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )


__all__ = ["ExternalValidationResult", "validate_with_openxml_sdk"]
