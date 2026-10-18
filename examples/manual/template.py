"""Check the template before rendering: both formats."""
from pathlib import Path
from pywpdoc import Document


def run(fmt: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = Document.new(fmt)
    doc.add_paragraph("Customer: {{customer.name}}")
    data = {"customer": {"name": "Rydolabs"}}
    report = doc.check_template(data)
    assert report.ok and report.tag_count == 1
    assert doc.render_template(data) == 1
    path = out_dir / f"template.{fmt}"
    doc.save(path)
    assert "Rydolabs" in Document.open(path).paragraphs[-1].text
    return path


if __name__ == "__main__":
    import sys
    print(run(sys.argv[1], Path(sys.argv[2])))
