# Quickstart

The high-level API is `from pywpdoc import Document`. Both formats support the same creation, paragraph, table, text find/replace and template entry points.

```python
from pywpdoc import Document

fmt = "docx"  # or "hwpx"
doc = Document.new(fmt)
doc.add_paragraph("Hello / 안녕하세요")
doc.add_table(2, 2).cell(0, 0).text = "Column A"
doc.save(f"hello.{fmt}")

reopened = Document.open(f"hello.{fmt}")
reopened.replace_text("Hello", "Updated")
reopened.save(f"updated.{fmt}")
```

For preview without writing, use `preview_replace(...)` or `check_template(...)`. For regular expressions, `find_regex(...)` and `replace_regex(...)` work inside safe text boundaries; they refuse unsafe cross-field/revision spans and zero-length matches. For conditional or repeated table rows, see `render_template(data, sections=True, table_rows=True)`.

To construct review revisions, use `old.compare(new, author="Name").save("review.hwpx")`, with both inputs of the same format and within the verified feature scope.

For unsupported format-specific operations, use `Document.unwrap()` or `pywpdoc.hwpx` / `pywpdoc.docx`. Those are backend-specific and not guaranteed portable.
