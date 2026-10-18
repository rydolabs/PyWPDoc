"""Quick start: generate DOCX and HWPX with the same public API."""
from pathlib import Path
from pywpdoc import Document


def run(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for fmt in ("docx", "hwpx"):
        doc = Document.new(fmt)
        doc.add_paragraph("Quarterly report / 분기 보고서")
        table = doc.add_table(2, 2)
        for row, cells in enumerate((("Item", "Qty"), ("Notebook", "12"))):
            for col, value in enumerate(cells):
                table.cell(row, col).text = value
        path = out_dir / f"quickstart.{fmt}"
        doc.save(path)
        results.append(path)
    return results


if __name__ == "__main__":
    import sys
    for path in run(Path(sys.argv[1] if len(sys.argv) > 1 else ".")):
        print(path)
