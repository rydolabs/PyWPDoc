<div align="center">

# PyWPDoc

### Automate Microsoft Word DOCX **and** Hancom Hangul HWPX with one Python API.

**Create editable reports, fill document templates, update tables and compare supported revisions in both file formats—without maintaining two document automation codebases.**

[**English / 한국어 API manual**](https://rydolabs.github.io/PyWPDoc/) · [**한국어 README**](README.ko.md) · [API reference](https://rydolabs.github.io/PyWPDoc/reference/document/) · [AI agent guide](https://rydolabs.github.io/PyWPDoc/agent-guide/) · [Tested examples](examples/manual/)

Python 3.10+ · DOCX + HWPX · MIT License

</div>

## One script. Two editable Office documents.

If your workflow needs a Word report **and** a Korean Hangul document, the same Python code can create both:

```python
from pywpdoc import Document

for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("Monthly report / 월간 보고서")
    doc.save(f"report.{fmt}")
```

**Output:** `report.docx` + `report.hwpx`—editable files, not PDF screenshots or renamed extensions. Desktop Word or Hancom is **not required** for ordinary creation and editing; native rendering/COM validation requires those applications.

![DOCX and HWPX business-document example rendered by Microsoft Word and Hancom](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/docx-hwpx-contract-comparison.png)

*Real native Windows PDF rendering of a **historical synthetic test case**. This is not a fresh 0.44.0rc1 visual-QA screenshot and does not imply identical Word/Hancom pagination. [Image provenance](docs/assets/readme/PROVENANCE.md) · [Current candidate QA evidence](docs/testing/native-qa-0440rc1-2026-10-18.md).*

## Why use PyWPDoc?

| Your real-world task | PyWPDoc approach |
| --- | --- |
| Produce reports and forms for Word and Korean Hangul users | `Document.new("docx")` / `Document.new("hwpx")` |
| Fill contracts, certificates, applications or purchase orders | `check_template()` before `render_template()` |
| Replace names, dates, or amounts in existing documents | `Document.open()` → `preview_replace()` → `replace_text()` |
| Build paragraphs, tables, images and sections | A portable common subset plus format-specific expert APIs |
| Review supported edits with tracked changes | `before.compare(after)` without mutating the originals |

**What makes it different?** [`python-docx`](https://github.com/python-openxml/python-docx) is a mature DOCX-specific library. PyWPDoc focuses on **workflows that must handle both DOCX and HWPX**; it does not replace every editor-specific feature.

## Install

**Until the first PyPI publication**, use the public source checkout:

```bash
git clone https://github.com/rydolabs/PyWPDoc.git
cd PyWPDoc
python -m pip install -e ".[unified]"
```

**After** `0.44.0rc1` has actually been published to PyPI:

```bash
python -m pip install "pywpdoc[unified]==0.44.0rc1"
```

The `[unified]` extra installs `python-docx` for DOCX; `pywpdoc` alone suffices for HWPX-only work. [Installation details](https://rydolabs.github.io/PyWPDoc/getting-started/installation/).

## Quickstart: a report with a table

```python
from pywpdoc import Document

for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("Purchase request / 구매 요청서")
    table = doc.add_table(2, 2)
    table.cell(0, 0).text = "Item"
    table.cell(0, 1).text = "Quantity"
    table.cell(1, 0).text = "Notebook"
    table.cell(1, 1).text = "12"
    doc.save(f"purchase-request.{fmt}")
```

The [runnable quickstart](examples/manual/quickstart.py) is exercised for both formats by API-contract CI tests.

### Safer template filling

```python
from pywpdoc import Document

doc = Document.open("template.hwpx")  # .docx works too
data = {"customer": {"name": "Example Ltd"}}
report = doc.check_template(data)       # read-only
if not report.ok:
    raise ValueError(f"Unresolved variables: {report.missing_keys}")
doc.render_template(data)
doc.save("filled.hwpx")
```

[Template example](examples/manual/template.py) · [Preview and replace](examples/manual/search_replace.py) · [Tracked comparison](examples/manual/compare.py) · [Agent workflow example](examples/manual/agent_tasks.py)

## Supported features and boundaries

| Feature | DOCX | HWPX |
| --- | --- | --- |
| Create, open, edit and save | Yes | Yes |
| Paragraphs, tables, pictures and sections | Common supported subset | Common supported subset |
| Literal/regex search, replacements and templates | Supported cases | Supported cases |
| Tracked text comparisons | Supported structures | Supported structures |
| Table-row insertion/deletion tracking | Supported cases | **Unsupported** |
| Pixel-identical Word/Hancom layout | **Not guaranteed** | **Not guaranteed** |

`save()` **does not convert file formats**; `rebuild()` is not a universal lossless DOCX↔HWPX converter, and binary legacy `.hwp` input is not supported by `Document.open()`. Native expert APIs differ by backend. [Compatibility](https://rydolabs.github.io/PyWPDoc/compatibility/) · [Known limitations](https://rydolabs.github.io/PyWPDoc/limitations/).

## Verified, with clearly stated limits

- **Hosted CI:** 10/10 jobs passed across Ubuntu/Windows Python 3.10–3.13, wheel/sdist and MkDocs checks. [CI run](https://github.com/rydolabs/PyWPDoc/actions/runs/39183964408).
- **0.44.0rc1 Windows native validation:** 11/11 focused Word/Hancom cases, 7/7 extended QA stages, including long/stress documents. [Evidence and exact scope](docs/testing/native-qa-0440rc1-2026-10-18.md).
- **Historical visual outputs:** a *previous build* passed 48/48 native PDF exports. The 0.44.0rc1 results archive has **no new PDF/pixel-layout comparison**.
- **Public test suite:** fixtures, omissions and skips are documented in [tests/README.md](tests/README.md). Hosted CI does not run desktop COM validation.

## For AI coding assistants and agents

Use `from pywpdoc import Document` for portable operations. Pick the document format, preflight edits, and save in the same format. Treat `doc.backend`, `doc.docx`, `doc.hwpx` as **expert-only** APIs.

[Task → API selection guide](https://rydolabs.github.io/PyWPDoc/agent-guide/) · [Exact signatures](https://rydolabs.github.io/PyWPDoc/reference/document/) · [Machine-readable document index](https://rydolabs.github.io/PyWPDoc/llms.txt)

PyWPDoc is a Python library—not a built-in MCP server or a native model tool. Publication does not guarantee ranking or selection by AI assistants.

---

[한국어](README.ko.md) · [Documentation](https://rydolabs.github.io/PyWPDoc/) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [MIT License](LICENSE)

**Version:** `0.44.0rc1` release candidate (GitHub Release and PyPI publication pending).
