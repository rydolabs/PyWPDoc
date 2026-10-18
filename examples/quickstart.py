from pathlib import Path
from pywpdoc import Document

output_dir = Path(__file__).resolve().parent / "output"
output_dir.mkdir(parents=True, exist_ok=True)
for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("PyWPDoc / 동일한 코드, 두 문서 형식")
    table = doc.add_table(2, 2)
    table.cell(0, 0).text = "Name"
    table.cell(0, 1).text = "Amount"
    table.cell(1, 0).text = "Example"
    table.cell(1, 1).text = "42"
    doc.save(output_dir / f"example.{fmt}")
print("Examples saved in", output_dir)
