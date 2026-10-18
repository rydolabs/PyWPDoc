"""Synthetic, cross-format demo document. No customer data."""
from pathlib import Path
from pywpdoc import Document, Pt

out = Path(__file__).resolve().parent / "output"
out.mkdir(parents=True, exist_ok=True)

def build(fmt):
    d = Document.new(fmt)
    p = d.add_paragraph()
    r = p.add_run("PyWPDoc  /  DOCUMENT AUTOMATION")
    r.bold = True
    r.font.size = Pt(20)
    d.add_paragraph("ONE PYTHON API  •  DOCX + HWPX  •  v0.43.0")
    d.add_paragraph("Cross-format document authoring with explicit compatibility boundaries")
    d.add_paragraph(" ")
    d.add_paragraph("RELEASE SNAPSHOT  |  Verified scenarios")
    t = d.add_table(4, 3)
    cells = [
        ["Capability", "DOCX", "HWPX"],
        ["Create / edit / template", "Supported", "Supported"],
        ["Text Track Changes", "Native", "Native*"],
        ["Tracked table rows", "Limited cases", "Not supported"],
    ]
    for row, values in zip(t.rows, cells):
        for cell, value in zip(row.cells, values):
            cell.text = value
    d.add_paragraph(" ")
    for heading, description in [
        ("01  /  ONE WORKFLOW, TWO FORMATS", "Generate a DOCX report and an HWPX report using the same Document API, paragraph methods, and table structures."),
        ("02  /  SAFER TEMPLATES", "Preview literal replacements and check missing placeholders before modifying document contents. Regex replacements reject unsafe boundaries."),
        ("03  /  REVIEWABLE CHANGES", "Produce verified native text revisions. Unsupported HWPX structural changes fail closed rather than pretending to track them."),
    ]:
        p = d.add_paragraph()
        h = p.add_run(heading)
        h.bold = True
        h.font.size = Pt(11)
        d.add_paragraph(description)
        d.add_paragraph(" ")
    d.add_paragraph("* HWPX native change-tracking evidence was tested with Hancom 2020. Synthetic demonstration; no customer documents were used.")
    f=out/f"pywpdoc_showcase.{fmt}"
    d.save(f)
    return f

if __name__ == '__main__':
    print('Saved:',*[str(build(fmt)) for fmt in ('docx','hwpx')])
