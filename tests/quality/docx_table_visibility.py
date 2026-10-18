"""Render-based DOCX table visibility regression helper.

This repository-only QA helper intentionally lives outside the runtime package.
It renders the first page with LibreOffice, rasterizes it to a grayscale PGM,
and checks for long horizontal/vertical dark line segments.  It is designed for
small deterministic fixtures whose purpose is to prove that a visible table
border survived document generation/template rendering.
"""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import tempfile


class VisualToolUnavailable(RuntimeError):
    pass


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise VisualToolUnavailable(f"required visual QA tool is unavailable: {name}")
    return path


def _read_pgm(path: Path) -> tuple[int, int, bytes]:
    with path.open("rb") as fh:
        if fh.readline().strip() != b"P5":
            raise ValueError(f"not a binary PGM: {path}")
        tokens: list[bytes] = []
        while len(tokens) < 3:
            line = fh.readline()
            if not line:
                raise ValueError(f"truncated PGM header: {path}")
            line = line.split(b"#", 1)[0]
            tokens.extend(line.split())
        width, height, max_value = map(int, tokens[:3])
        if max_value != 255:
            raise ValueError(f"unsupported PGM max value: {max_value}")
        pixels = fh.read(width * height)
        if len(pixels) != width * height:
            raise ValueError(f"truncated PGM pixels: {path}")
        return width, height, pixels


def _longest_dark_run_row(pixels: bytes, width: int, y: int, threshold: int) -> int:
    start = y * width
    longest = current = 0
    for value in pixels[start : start + width]:
        if value < threshold:
            current += 1
            if current > longest:
                longest = current
        else:
            current = 0
    return longest


def _longest_dark_run_col(
    pixels: bytes, width: int, height: int, x: int, threshold: int
) -> int:
    longest = current = 0
    for y in range(height):
        value = pixels[y * width + x]
        if value < threshold:
            current += 1
            if current > longest:
                longest = current
        else:
            current = 0
    return longest


def has_visible_table_grid(
    pgm_path: str | Path,
    *,
    threshold: int = 180,
    horizontal_fraction: float = 0.45,
    minimum_horizontal_lines: int = 3,
    minimum_vertical_lines: int = 3,
    minimum_vertical_pixels: int = 35,
) -> bool:
    """Return whether a deterministic fixture visibly contains a table grid.

    The fixture is expected to contain a normal-width 2x2-ish table.  Long
    straight lines are deliberately used instead of OCR or document XML so the
    gate verifies the rendered output, not just the package structure.
    """
    width, height, pixels = _read_pgm(Path(pgm_path))
    min_horizontal = int(width * horizontal_fraction)
    horizontal = sum(
        _longest_dark_run_row(pixels, width, y, threshold) >= min_horizontal
        for y in range(height)
    )
    vertical = sum(
        _longest_dark_run_col(pixels, width, height, x, threshold)
        >= minimum_vertical_pixels
        for x in range(width)
    )
    return horizontal >= minimum_horizontal_lines and vertical >= minimum_vertical_lines


def render_first_page_to_pgm(docx_path: str | Path, output_dir: str | Path) -> Path:
    """Render *docx_path* with LibreOffice and return a first-page grayscale PGM."""
    docx_path = Path(docx_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    soffice = _tool("soffice")
    pdftoppm = _tool("pdftoppm")
    profile = output_dir / "lo-profile"
    profile.mkdir(exist_ok=True)
    pdf_path = output_dir / f"{docx_path.stem}.pdf"

    env = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="pywpdoc-home-") as home:
        env["HOME"] = home
        subprocess.run(
            [
                soffice,
                "--headless",
                f"-env:UserInstallation=file://{profile}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                str(docx_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=60,
        )
    if not pdf_path.exists():
        raise RuntimeError(f"LibreOffice did not create {pdf_path}")

    prefix = output_dir / "page-1"
    subprocess.run(
        [
            pdftoppm,
            "-f",
            "1",
            "-l",
            "1",
            "-singlefile",
            "-gray",
            "-r",
            "150",
            str(pdf_path),
            str(prefix),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    pgm_path = prefix.with_suffix(".pgm")
    if not pgm_path.exists():
        raise RuntimeError(f"pdftoppm did not create {pgm_path}")
    return pgm_path
