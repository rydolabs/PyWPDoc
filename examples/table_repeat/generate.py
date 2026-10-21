"""Reproducible DOCX/HWPX repeating-table demonstration using PyWPDoc's common API."""
from pathlib import Path
from pywpdoc import Document

OUT = Path(__file__).resolve().parent
DATA = {
    "order_id": "PO-2048",
    "company": "ACME Procurement",
    "items": [
        {"name": "Notebook", "qty": 12},
        {"name": "Monitor", "qty": 8},
        {"name": "USB-C Dock", "qty": 12},
    ],
}

for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("PURCHASE ORDER | {{order_id}}")
    doc.add_paragraph("Customer: {{company}}")
    table = doc.add_table(2, 2, style="Table Grid")
    for c, value in enumerate(("Item", "Qty")):
        table.cell(0, c).text = value
    table.cell(1, 0).text = "{{#items}}{{name}}"
    table.cell(1, 1).text = "{{qty}}{{/items}}"
    template_file = OUT / f"purchase-order-template.{fmt}"
    doc.save(template_file)
    report = doc.check_template(DATA, sections=True, table_rows=True)
    assert report.ok, report.to_dict()
    doc.render_template(DATA, sections=True, table_rows=True)
    final_file = OUT / f"purchase-order-filled.{fmt}"
    doc.save(final_file)
    reopened = Document.open(final_file)
    actual = [[cell.text for cell in row.cells] for row in reopened.tables[0].rows]
    expected = [
        ["Item", "Qty"],
        ["Notebook", "12"],
        ["Monitor", "8"],
        ["USB-C Dock", "12"],
    ]
    assert actual == expected, (fmt, actual)
    print(f"{fmt.upper()} generated + reopened; {len(actual) - 1} real data rows")
