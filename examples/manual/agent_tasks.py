"""Agent-oriented document workflow, exercised on DOCX and HWPX."""
from pathlib import Path
from pywpdoc import Document


def run(fmt: str, out_dir: Path) -> Path:
    """Check template, preview replacement, save and re-open a document."""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = Document.new(fmt)
    doc.add_paragraph("Customer: {{customer.name}}")
    doc.add_paragraph("Status: DRAFT")
    table = doc.add_table(2, 2)
    table.cell(0, 0).text = "Item"
    table.cell(0, 1).text = "Quantity"
    table.cell(1, 0).text = "Notebook"
    table.cell(1, 1).text = "12"

    data = {"customer": {"name": "Example Ltd"}}
    report = doc.check_template(data)
    if not report.ok:
        raise ValueError(f"Unresolved template fields: {report.missing_keys}")
    assert doc.render_template(data) == 1

    preview = doc.preview_replace("DRAFT", "APPROVED")
    assert preview.count == 1
    assert "DRAFT" in doc.paragraphs[-1].text  # read-only preview
    assert doc.replace_text("DRAFT", "APPROVED") == 1

    path = out_dir / f"agent-workflow.{fmt}"
    doc.save(path)
    reopened = Document.open(path)
    assert reopened.format == fmt
    assert any("Example Ltd" in p.text for p in reopened.paragraphs)
    assert any("APPROVED" in p.text for p in reopened.paragraphs)
    assert reopened.tables[0].cell(1, 1).text == "12"
    return path


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    for fmt in ("docx", "hwpx"):
        print(run(fmt, out))
