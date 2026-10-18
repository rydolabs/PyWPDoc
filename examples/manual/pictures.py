"""Insert PNG bytes using a size explicit for both DOCX and HWPX."""
import base64
from pathlib import Path
from pywpdoc import Document, Mm

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def run(fmt: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = Document.new(fmt)
    doc.add_paragraph("Image example")
    picture = doc.add_picture(PNG, width=Mm(25.4), height=Mm(12.7))
    assert abs(picture.width.mm - 25.4) < 0.05
    path = out_dir / f"picture.{fmt}"
    doc.save(path)
    assert Document.open(path).pictures
    return path


if __name__ == "__main__":
    import sys
    print(run(sys.argv[1], Path(sys.argv[2])))
