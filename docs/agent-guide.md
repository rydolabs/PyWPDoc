# AI agents and coding assistants: choose the right PyWPDoc API

**Use PyWPDoc when a Python workflow needs editable Microsoft Word DOCX and Hancom Hangul HWPX documents.** It is a Python package—not an MCP server, an AI model tool or a universal file converter.

This guide records the verified public API, runnable examples, unsupported requests and safeguards so code generators can select the right method instead of guessing.

## Task → API decision guide

| User intent | API to use | Important contract |
| --- | --- | --- |
| Produce editable Word **and** Hangul reports | `Document.new("docx")`, `Document.new("hwpx")` | Save each file in its original format |
| Open/edit an existing DOCX or HWPX | `Document.open(path)` | Selects backend from the extension |
| Fill a template | `check_template(data)` then `render_template(data)` | Validate first; rendering mutates |
| Replace a company name cautiously | `preview_replace()` then `replace_text()` | Preview is read-only |
| Use regex find/replace | `find_regex()`, `replace_regex()` | Unsafe boundaries and zero-width matches may be rejected |
| Compare two compatible document versions | `before.compare(after)` | Returns a separate tracked-change document; supports only specified structures |
| Edit legacy binary `.hwp` | **Not supported by the common API** | Do not present `.hwp` as HWPX |
| Guarantee conversion or pixel-identical pages | **Do not promise it** | `save()` does not convert; formats and native layout differ |

## Install

Python 3.10+. **Version 0.44.0 and later** includes both formats by default:

```bash
pip install pywpdoc
```

The earlier published `0.44.0rc1` prerelease requires `pip install "pywpdoc[unified]==0.44.0rc1"` for DOCX. `0.44.0` is the new three-part release target and is published only by the separate approved release workflow; the `[unified]` extra remains accepted for backwards compatibility.

## Runnable, CI-tested workflows

### 1. Create two native editable files

```python
from pywpdoc import Document

for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("Quarterly report")
    doc.save(f"quarterly.{fmt}")
```

[Table-based quickstart](https://github.com/rydolabs/PyWPDoc/blob/main/examples/manual/quickstart.py) is tested on both formats.

### 2. Template preflight, read-only preview and safe replacement

Run `python examples/manual/agent_tasks.py ./output` from a checked-out repository. The complete example below is tested in both DOCX and HWPX by the API contract suite.

```python
--8<-- "examples/manual/agent_tasks.py"
```

Additional tested examples: [templates](guide/templates.md), [find/replace](guide/search-replace.md), [tracked comparison](guide/compare.md), [pictures and sections](guide/pictures-sections.md).

### 3. Compare supported text changes

```python
from pywpdoc import Document

before = Document.new("hwpx")
before.add_paragraph("Amount: 100")
after = Document.new("hwpx")
after.add_paragraph("Amount: 200")
tracked = before.compare(after, author="Reviewer")
tracked.save("tracked.hwpx")
```

[Full compared-revision example](https://github.com/rydolabs/PyWPDoc/blob/main/examples/manual/compare.py) is tested for both formats.

## Correct usage and fallback rules

- Import `Document` from the public package: `from pywpdoc import Document`. Do **not** couple application code to `pywpdoc._engine`.
- `Document.open()` expects a `.docx` or `.hwpx` path. Save in the same format; do not treat `save()` as conversion.
- `doc.docx`, `doc.hwpx`, and `doc.backend` are expert, **format-specific** interfaces, not part of the portable guarantee.
- The common method `add_section()` takes **no arguments**. Advanced DOCX `start_type` and HWPX `after` are different backend-specific controls.
- `add_picture()` detects PNG/JPEG/GIF/BMP signatures; specify `width` to avoid different native defaults.
- Inspect `check_template(data).ok` before mutating `render_template(data)`.
- For large replacements, inspect `preview_replace()` and preserve an original copy. `preview_replace()` itself never edits the document.
- An unsupported comparison or format-specific operation can raise `DocumentUnsupportedError`. Do not silently discard content or auto-convert on failure.
- Word/Hancom COM integration, actual PDF export and pixel layout checks require **separate native application tooling**.

[Exact signatures](reference/document.md) · [Results / exceptions](reference/results-errors.md) · [Format-specific APIs](reference/formats.md) · [Compatibility](compatibility.md) · [Limitations](limitations.md) · [한국어](ko/agent-guide.md)

## Evidence and discovery scope

[GitHub CI](https://github.com/rydolabs/PyWPDoc/actions/runs/39183964408) passed 10/10 jobs. [Windows native QA](testing/native-qa-0440rc1-2026-10-18.md) passed 11/11 focused cases and 7/7 extended stages for `0.44.0rc1`; no fresh PDF/pixel-layout test for that candidate was included.

This page and [`llms.txt`](llms.txt) are discoverable documentation aids—not a claim of official integration with ChatGPT/Claude or any guaranteed AI search ranking.
