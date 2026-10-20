<div align="center">

# PyWPDoc

### Reviewable Word document automation in Python.

**Compare document versions with native tracked changes. Check template tags before filling. Preview edits before modifying files.**

**Microsoft Word DOCX first** · Hancom Hangul HWPX also supported · Python 3.10+ · MIT

[**Quickstart**](#quickstart) · [**Document API**](https://rydolabs.github.io/PyWPDoc/reference/document/) · [**Tracked Changes**](https://rydolabs.github.io/PyWPDoc/guide/compare/) · [**Templates**](https://rydolabs.github.io/PyWPDoc/guide/templates/) · [**한국어**](https://github.com/rydolabs/PyWPDoc/blob/main/README.ko.md)

</div>

## Install

```bash
pip install pywpdoc
```

Starting with **0.44.0**, one default installation supports both DOCX and HWPX. For the already-published **0.44.0rc1**, use `pip install "pywpdoc[unified]==0.44.0rc1"` to enable DOCX. The old `[unified]` extra remains accepted.

## See what makes it different

### 1. Before + After → one document with tracked changes

Change an agreement, then keep the edits **reviewable in Word**, instead of delivering only a silently overwritten file.

| BEFORE | AFTER |
| --- | --- |
| Amount: **USD 10,000** | Amount: **USD 12,500** |
| Delivery: **Nov 15** | Delivery: **Dec 1** |
| Support: **3 months** | Support: **6 months** |

**TRACKED REVIEW:** supported text changes are saved as native DOCX revisions, including inserted and deleted text. The original documents remain unchanged.

```python
from pywpdoc import Document

before = Document.open("agreement-before.docx")
after = Document.open("agreement-after.docx")

review = before.compare(after, author="Reviewer")
review.save("agreement-reviewed.docx")
```

The tested [16-paragraph example](https://github.com/rydolabs/PyWPDoc/tree/main/tests/showcase) changes 13 paragraphs. A genuine Word **Review → All Markup** screenshot, cropped to the most readable edits, will accompany this example after human visual acceptance. We intentionally do **not** present an unverified or reconstructed redline image as a Word screenshot.

[**Compare API and limitations →**](https://rydolabs.github.io/PyWPDoc/guide/compare/)

### 2. Check templates before filling them

```python
from pywpdoc import Document

doc = Document.open("template.docx")
data = {"customer": {"name": "Acme Corp"}}
check = doc.check_template(data)  # Read-only preflight
if not check.ok:
    raise ValueError(check.missing_keys)
doc.render_template(data)
doc.save("agreement-filled.docx")
```

`Customer: {{customer.name}}` → **`Customer: Acme Corp`**

Catch missing or malformed template data **before** rendering. [**Template API →**](https://rydolabs.github.io/PyWPDoc/guide/templates/)

### 3. Preview replacements before making changes

```python
doc = Document.open("draft.docx")
preview = doc.preview_replace("Draft", "Approved")  # No mutation
if preview.has_matches:
    doc.replace_text("Draft", "Approved")
    doc.save("approved.docx")
```

The preview includes a structured report of candidate edits. [**Search and replace API →**](https://rydolabs.github.io/PyWPDoc/guide/search-replace/)

## Quickstart

Create an editable Word file in three steps:

```python
from pywpdoc import Document

doc = Document.new("docx")
doc.add_paragraph("Quarterly business report")
doc.save("report.docx")
```

DOCX and HWPX use the documented common `Document` API; save each document in its own format. Word/Hancom desktop apps are not needed for normal Python file creation and editing.

## Actual native-rendered document previews

The following images are **real Windows Word/Hancom PDF-page renders from earlier QA**. They demonstrate document output, not the specific tracked-review example above.

![Genuine earlier Windows Word contract PDF page](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/contract-word.png)

![Genuine earlier Windows Word complex-table PDF page](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/complex-tables-docx.png)

**Additional format: Hancom Hangul HWPX**

![Earlier Windows Word DOCX and Hancom HWPX PDF output comparison](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/docx-hwpx-contract-comparison.png)

*Image provenance: [native asset evidence](https://github.com/rydolabs/PyWPDoc/blob/main/docs/assets/readme/PROVENANCE.md). This does not demonstrate new 0.44.0 pixel-layout QA or guarantee identical pagination between formats.*

## Jump straight to the API

| Need | Documentation |
| --- | --- |
| Exact `Document` signatures | [**Document API Reference**](https://rydolabs.github.io/PyWPDoc/reference/document/) |
| Compare and tracked revisions | [Tracked Changes](https://rydolabs.github.io/PyWPDoc/guide/compare/) |
| Template tags and validation | [Templates](https://rydolabs.github.io/PyWPDoc/guide/templates/) |
| Find, preview, replace | [Text editing](https://rydolabs.github.io/PyWPDoc/guide/search-replace/) |
| Runnable examples and installation | [Quickstart](https://rydolabs.github.io/PyWPDoc/getting-started/quickstart/) · [Installation](https://rydolabs.github.io/PyWPDoc/getting-started/installation/) |
| Errors and agent workflows | [Results & Errors](https://rydolabs.github.io/PyWPDoc/reference/results-errors/) · [Agent Guide](https://rydolabs.github.io/PyWPDoc/agent-guide/) |
| Korean manual | [한국어 API 매뉴얼](https://rydolabs.github.io/PyWPDoc/ko/) |

**Scope:** PyWPDoc supports a documented common subset of editable DOCX and HWPX operations. `compare()` is not a generic diff/merge engine and can reject unsupported structural changes. The library does not open legacy binary `.hwp`, guarantee lossless DOCX↔HWPX conversion, provide a built-in MCP server or promise pixel-identical layouts. [Compatibility](https://rydolabs.github.io/PyWPDoc/compatibility/) · [Known limitations](https://rydolabs.github.io/PyWPDoc/limitations/).

[Source](https://github.com/rydolabs/PyWPDoc) · [PyPI](https://pypi.org/project/pywpdoc/) · [Native QA evidence for the earlier RC](https://github.com/rydolabs/PyWPDoc/blob/main/docs/testing/native-qa-0440rc1-2026-10-18.md) · [MIT License](https://github.com/rydolabs/PyWPDoc/blob/main/LICENSE)

**Version: 0.44.0.**
