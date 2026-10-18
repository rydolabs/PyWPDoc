# PyWPDoc API Manual

**One Python API. Two editable document formats.** Create and automate Microsoft Word DOCX and Hancom HWPX files with the same public `Document` entry point.

![DOCX and HWPX business document rendered by their native desktop applications](assets/readme/docx-hwpx-contract-comparison.png)

*Verified synthetic contract PDF output from Microsoft Word and Hancom on Windows (2026-10-18); shown as illustrative QA evidence. Pixel-level layout parity is not guaranteed. The reorganized 0.44.0rc1 package still needs its own Windows native validation.*

```python
from pywpdoc import Document
for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("Hello / 안녕하세요")
    doc.save(f"hello.{fmt}")
```

The **same public entry point** supports portable document creation, tables, supported text automation and template operations. Some expert operations are format-specific; see [compatibility](compatibility.md).

Start with [installation](getting-started/installation.md), [quickstart](getting-started/quickstart.md), or [한국어 가이드](ko/index.md). [API Reference](reference/document.md) describes exact signatures, return values, and limits.

!!! info "Status"
    Version `0.44.0rc1` is a **review candidate**, not yet available from PyPI. Published documentation and remote CI are also pending approval. This directory is ready for local MkDocs preview.
