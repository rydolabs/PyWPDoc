"""Portable section creation: no format-specific options."""
from pathlib import Path
from pywpdoc import Document


def run(fmt: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = Document.new(fmt)
    doc.add_paragraph("Section one")
    section = doc.add_section()  # portable, default position/start only
    assert section is not None
    doc.add_paragraph("Section two")
    path = out_dir / f"sections.{fmt}"
    doc.save(path)
    return path


if __name__ == "__main__":
    import sys
    print(run(sys.argv[1], Path(sys.argv[2])))
