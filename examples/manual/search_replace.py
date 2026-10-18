"""Read-only preview, literal replacement, and regex replacement."""
from pathlib import Path
from pywpdoc import Document


def run(fmt: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = Document.new(fmt)
    doc.add_paragraph("Customer: Alice; Amount: 123")
    preview = doc.preview_replace("Alice", "Bob")
    assert preview.count == 1
    assert "Alice" in doc.paragraphs[-1].text  # preview never edits
    assert doc.replace_text("Alice", "Bob") == 1
    assert doc.replace_regex(r"\b123\b", "456") == 1
    path = out_dir / f"search-replace.{fmt}"
    doc.save(path)
    assert "Bob" in Document.open(path).paragraphs[-1].text
    return path


if __name__ == "__main__":
    import sys
    print(run(sys.argv[1], Path(sys.argv[2])))
