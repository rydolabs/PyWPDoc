<div align="center">

# PyWPDoc

### Document automation with validation and tracked changes.

**Fill Word templates, preview text edits, and create reviewable document revisions in Python.**

**One install. One API.** Microsoft Word **DOCX**, with **Hancom Hangul HWPX** support when you need it.

[**Install**](#install) · [**Quickstart**](#quickstart) · [**API Reference**](https://rydolabs.github.io/PyWPDoc/reference/document/) · [**Templates**](https://rydolabs.github.io/PyWPDoc/guide/templates/) · [**Tracked Changes**](https://rydolabs.github.io/PyWPDoc/guide/compare/) · [**한국어**](https://github.com/rydolabs/PyWPDoc/blob/main/README.ko.md)

Python 3.10+ · MIT License

</div>

## Install

```bash
pip install pywpdoc
```

**Starting with version 0.44.0**, the default installation includes both DOCX and HWPX support. If you are using the *already published* `0.44.0rc1` prerelease instead, DOCX requires `pip install "pywpdoc[unified]==0.44.0rc1"`. The former `[unified]` extra remains accepted for compatibility.

## Quickstart

Create an editable Word document in a few lines:

```python
from pywpdoc import Document

doc = Document.new("docx")
doc.add_paragraph("Quarterly business report")
doc.save("report.docx")
```

The same `Document` interface can also create `.hwpx` files; desktop Microsoft Word or Hancom is not needed for ordinary file generation or editing.

## Three workflows that go beyond document creation

### 1. Check template tags before filling them

```python
from pywpdoc import Document

doc = Document.new("docx")
doc.add_paragraph("Customer: {{customer.name}}")
data = {"customer": {"name": "Acme Corp"}}

report = doc.check_template(data)  # Read-only validation
if not report.ok:
    raise ValueError(f"Missing/invalid tags: {report.missing_keys}")

doc.render_template(data)
doc.save("customer-contract.docx")
```

**Before:** `Customer: {{customer.name}}` → **After:** `Customer: Acme Corp`

Avoid silently filling an incomplete template: inspect `report.ok`, `missing_keys`, and `issues` before changing a real document. [Template API and tested example](https://rydolabs.github.io/PyWPDoc/guide/templates/).

### 2. Generate a document with tracked revisions

```python
from pywpdoc import Document

before = Document.new("docx")
before.add_paragraph("Contract amount: $1,000")

after = Document.new("docx")
after.add_paragraph("Contract amount: $1,200")

review = before.compare(after, author="Reviewer")
review.save("contract-review.docx")
```

**Review concept:** `$1,000` → `$1,200`, recorded as supported native tracked text changes in the resulting document. This is **not** a universal Word diff or merge engine: unsupported structural changes raise errors. [Tracked Changes guide and runnable test](https://rydolabs.github.io/PyWPDoc/guide/compare/).

### 3. Preview replacements before editing

```python
from pywpdoc import Document

doc = Document.open("report.docx")
preview = doc.preview_replace("Draft", "Approved")  # Does not mutate
print(preview.count, preview.has_matches)

if preview.has_matches:
    doc.replace_text("Draft", "Approved")
    doc.save("report-approved.docx")
```

Preview reports include structured match information. For bulk edits, verify the scope and keep an untouched source copy. [Find, preview and replace API](https://rydolabs.github.io/PyWPDoc/guide/search-replace/).

## Real document previews

These are **actual PDF page renders from historical Windows Microsoft Word/Hancom QA**, not fabricated UI screenshots or newly generated `0.44.0` outputs.

**Word DOCX: contract page**

![A business contract DOCX rendered with native Microsoft Word during historical Windows QA](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/contract-word.png)

**Word DOCX: complex table layout**

![A complex-table DOCX page rendered with native Microsoft Word during historical Windows QA](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/complex-tables-docx.png)

**DOCX and HWPX: same document workflow, two editable formats**

![Historical Microsoft Word DOCX and Hancom Hangul HWPX rendered document comparison](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/docx-hwpx-contract-comparison.png)

*Image provenance: [README screenshot evidence](https://github.com/rydolabs/PyWPDoc/blob/main/docs/assets/readme/PROVENANCE.md). Native output and pagination can differ by app, font and version. These screenshots are historical QA illustrations, **not** screenshots of the template/Track Changes examples above or fresh 0.44.0 visual validation.*

## When should you use PyWPDoc?

| Task | Key APIs |
| --- | --- |
| Validate and populate contracts or forms | `check_template()` → `render_template()` |
| Review two compatible document versions | `compare()` → a separate tracked-revision document |
| Preview and apply safe text edits | `preview_replace()`, `replace_text()`, `replace_regex()` |
| Generate structured Word documents | `Document.new("docx")`, `add_table()`, `add_picture()` |
| Automate Korean Hangul documents too | `Document.new("hwpx")`, the same documented common subset |

PyWPDoc works with **editable DOCX and HWPX**. It does **not** open legacy binary `.hwp`, guarantee DOCX↔HWPX conversion, provide pixel-identical layout or promise that every structural edit can be tracked. [Compatibility](https://rydolabs.github.io/PyWPDoc/compatibility/) · [Known limitations](https://rydolabs.github.io/PyWPDoc/limitations/).

## API documentation — open directly

| Learn | Reference |
| --- | --- |
| Installation and first document | [Installation](https://rydolabs.github.io/PyWPDoc/getting-started/installation/) · [Quickstart](https://rydolabs.github.io/PyWPDoc/getting-started/quickstart/) |
| Exact `Document` method signatures | [Document API Reference](https://rydolabs.github.io/PyWPDoc/reference/document/) |
| Return types and exceptions | [Results & Errors](https://rydolabs.github.io/PyWPDoc/reference/results-errors/) |
| Templates, find/replace, tracked revisions | [Templates](https://rydolabs.github.io/PyWPDoc/guide/templates/) · [Search/Replace](https://rydolabs.github.io/PyWPDoc/guide/search-replace/) · [Compare](https://rydolabs.github.io/PyWPDoc/guide/compare/) |
| Coding agents: choose the correct API | [Agent Guide](https://rydolabs.github.io/PyWPDoc/agent-guide/) |
| Korean documentation | [한국어 매뉴얼](https://rydolabs.github.io/PyWPDoc/ko/) |

The examples use public methods and are based on the tested DOCX/HWPX workflows. [Executable examples on GitHub](https://github.com/rydolabs/PyWPDoc/tree/main/examples/manual) · [Automated CI](https://github.com/rydolabs/PyWPDoc/actions/workflows/ci.yml) · [0.44.0rc1 native QA scope](https://github.com/rydolabs/PyWPDoc/blob/main/docs/testing/native-qa-0440rc1-2026-10-18.md). The prior prerelease passed focused Word/Hancom native checks; new 0.44.0-specific visual QA has **not** been claimed.

---

[GitHub](https://github.com/rydolabs/PyWPDoc) · [PyPI](https://pypi.org/project/pywpdoc/) · [Documentation](https://rydolabs.github.io/PyWPDoc/) · [Changelog](https://github.com/rydolabs/PyWPDoc/blob/main/CHANGELOG.md) · [License](https://github.com/rydolabs/PyWPDoc/blob/main/LICENSE)

**Version: 0.44.0.** Stable-release publication is a separate, explicitly approved step; the previous `0.44.0rc1` is already on PyPI.
