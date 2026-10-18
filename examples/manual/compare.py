"""Tracked comparison of one text edit with unchanged structure."""
from pathlib import Path
from pywpdoc import Document


def run(fmt: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    before = Document.new(fmt)
    before.add_paragraph("Contract amount: 100")
    after = Document.new(fmt)
    after.add_paragraph("Contract amount: 200")
    tracked = before.compare(after, author="QA Reviewer")
    path = out_dir / f"comparison.{fmt}"
    tracked.save(path)
    assert path.stat().st_size > 0
    return path


if __name__ == "__main__":
    import sys
    print(run(sys.argv[1], Path(sys.argv[2])))
