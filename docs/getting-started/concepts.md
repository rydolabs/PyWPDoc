# Three API layers

| Layer | Import / accessor | When to use | Stability |
| --- | --- | --- | --- |
| Common facade | `from pywpdoc import Document` | Portable create/open/save, paragraphs, tables, text automation | Documented contract |
| Format-specific backend | `from pywpdoc.docx import Document` or `from pywpdoc.hwpx import Document` | Options unique to DOCX/HWPX | Format-specific, not portable |
| Native escape hatch | `doc.docx`, `doc.hwpx`, `doc.unwrap()` | Advanced operations with the raw engine object | Expert-only |

`doc.backend` is the selected backend wrapper; `doc.native` is its **raw document**. `doc.docx` and `doc.hwpx` return the raw document for the matching format, and raise `DocumentUnsupportedError` for the wrong format.

A legacy `__getattr__` passthrough exposes additional backend names for expert use. **The existence of an attribute via passthrough does not make it a supported Common API.** Only methods in the [reference](../reference/document.md) are promised as portable for this release candidate.

`Document.new()` defaults to **HWPX**. For clarity, write `Document.new("docx")` or `Document.new("hwpx")` explicitly.
