# PyWPDoc API Manual

**One Python API. Two editable document formats.** Create and automate Microsoft Word DOCX and Hancom HWPX files with the same public `Document` entry point.

![DOCX and HWPX business document rendered by their native desktop applications](assets/readme/docx-hwpx-contract-comparison.png)

*Verified synthetic contract PDF output from Microsoft Word and Hancom on Windows (2026-10-18); shown as illustrative QA evidence. Pixel-level layout parity is not guaranteed. The reorganized 0.44.0rc1 package passed focused Word/Hancom native QA; the historical screenshot shown here is not a screenshot from that new RC-specific run. See [native QA evidence](testing/native-qa-0440rc1-2026-10-18.md).*

```python
from pywpdoc import Document
for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("Hello / 안녕하세요")
    doc.save(f"hello.{fmt}")
```

The **same public entry point** supports portable document creation, tables, supported text automation and template operations. Some expert operations are format-specific; see [compatibility](compatibility.md).

Start with [installation](getting-started/installation.md), [quickstart](getting-started/quickstart.md), [AI agent task selection](agent-guide.md), or [한국어 가이드](ko/index.md). [API Reference](reference/document.md) describes exact signatures, return values, and limits.

!!! info "Status"
    Version `0.44.0rc1` is a **release candidate**, not yet published to PyPI. The [first successful GitHub CI](https://github.com/rydolabs/PyWPDoc/actions/runs/39132701860) passed across Ubuntu/Windows (Python 3.10–3.13), package builds and the MkDocs strict documentation build. The 0.44.0rc1 wheel also passed focused Windows Word/Hancom native roundtrip and long-document acceptance checks ([evidence](testing/native-qa-0440rc1-2026-10-18.md)). The current archive does not provide a new PDF-layout QA run, and PyPI publishing remains a separate manual release step.
