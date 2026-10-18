# Format-specific APIs

Common objects and **native** objects are different:

```python
from pywpdoc import Document

doc = Document.new("docx")
backend = doc.backend      # PyWPDoc DOCX backend wrapper
raw_docx = doc.docx       # raw python-docx Document
assert raw_docx is doc.unwrap()
```

For backend constructors, you may also use `from pywpdoc.docx import Document` or `from pywpdoc.hwpx import Document`. These are format-specific wrappers, *not* the unified facade. `doc.hwpx` on a DOCX document, or `doc.docx` on an HWPX document, raises `DocumentUnsupportedError`.

| Operation | DOCX backend | HWPX backend | Portable common API |
| --- | --- | --- | --- |
| Insert picture | `add_picture(image_data, image_format=None, *, width=None, height=None, treat_as_char=True)` | `add_picture(image_data, image_format, *, width=14400, height=None, treat_as_char=True)` | Signature sniffing + explicit size; see [guide](../guide/pictures-sections.md). |
| Section insertion | `add_section(start_type=None)` | `add_section(*, after=None)` | `add_section()` only |
| Native document | `doc.docx` / `doc.unwrap()` | `doc.hwpx` / `doc.unwrap()` | Expert escape hatch |

For portable projects, do not rely on object identity, XML ordering, default picture sizing or formatting behavior being the same across backends. See [compatibility](../compatibility.md).
