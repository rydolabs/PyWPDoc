<div align="center">

# PyWPDoc

### One Python API. Two document formats.

**Create, edit, and automate Microsoft Word (DOCX) and Hancom Hangul (HWPX) documents—without maintaining two separate codebases.**

**[API Manual (English / 한국어)](https://github.com/rydolabs/PyWPDoc/blob/main/docs/index.md)** · [API Reference](https://github.com/rydolabs/PyWPDoc/blob/main/docs/reference/document.md) · **[한국어](https://github.com/rydolabs/PyWPDoc/blob/main/README.ko.md)** · [Quick start](#quick-start) · [Real documents](#see-real-outputs) · [Feature support](#feature-support-and-limits) · [Examples](https://github.com/rydolabs/PyWPDoc/tree/main/examples) · [Testing](https://github.com/rydolabs/PyWPDoc/blob/main/tests/README.md)

*Python 3.10+ · DOCX + HWPX · MIT License*

</div>

## See real outputs

![The same PyWPDoc business-document scenario rendered by Microsoft Word (DOCX) and Hancom Hangul (HWPX), as PDFs on Windows](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/docx-hwpx-contract-comparison.png)

*Actual native Windows QA output, 2026-10-18. DOCX PDF: Microsoft Word; HWPX PDF: Hancom Office. These are synthetic test contracts, not customer data. The two editors may paginate or space content differently; pixel-identical layout is not promised.*

### From Python to both files

```python
from pywpdoc import Document

for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("Quarterly report / 분기 보고서")
    doc.save(f"report.{fmt}")
```

**One workflow, two native file formats.** `report.docx` and `report.hwpx` are real editable documents, not PDF screenshots.

## Install

After the first PyPI publication:

```bash
python -m pip install "pywpdoc[unified]"
```

`[unified]` installs the optional `python-docx` package required for the DOCX backend. For HWPX-only use, `pip install pywpdoc` is sufficient. **PyPI installation is not available until the first release is published.** Until then, install the reviewed wheel or source checkout.

## Why PyWPDoc?

| Your task | With a format-specific library | With PyWPDoc |
| --- | --- | --- |
| Generate both Word and Hangul files | Typically maintain different document libraries and adapters | Use the same `Document.new(fmt)` API |
| Work with paragraphs and tables | Each SDK exposes format-specific types | Shared methods for supported operations |
| Fill repeatable business templates | Separate integration for each file type | Common template checking and rendering |
| Compare or safely replace content | Format-dependent mutation handling | Shared search / replace / compare entry points |
| Validate output in real editors | Build a separate QA flow | Includes reproducible Word/Hancom QA scenarios |

**How is this different?** [`python-docx`](https://github.com/python-openxml/python-docx) is a mature DOCX-focused library. HWPX-specific tools focus on Hangul files. PyWPDoc is for **workflows that must handle both DOCX and HWPX** using a shared high-level interface. This is a design distinction—not a claim that PyWPDoc replaces every expert feature of other tools.

## Quick start

### Paragraphs and tables

```python
from pywpdoc import Document

for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("Purchase request")
    table = doc.add_table(2, 2)
    table.cell(0, 0).text = "Item"
    table.cell(0, 1).text = "Quantity"
    table.cell(1, 0).text = "Notebook"
    table.cell(1, 1).text = "12"
    doc.save(f"purchase-request.{fmt}")
```

### Open a template, preview, then edit

```python
from pywpdoc import Document

doc = Document.open("template.hwpx")
report = doc.check_template({"customer": {"name": "Example Ltd"}})
print(report)
doc.render_template({"customer": {"name": "Example Ltd"}})
doc.save("filled.hwpx")
```

### Business documents and merged tables

![Real native DOCX and HWPX complex-table output](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/complex-tables-comparison.png)

*Asset register / nested merged-table scenario from the Windows native QA corpus (2026-10-17). The scenario includes visible QA markers. See [capture provenance](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/PROVENANCE.md).*

## Feature support and limits

| Capability | DOCX | HWPX |
| --- | --- | --- |
| Create / open / edit / save | Supported | Supported |
| Paragraphs, tables, shared document facade | Supported | Supported |
| Literal / regex search and replacement | Supported cases | Supported cases |
| Template preflight and rendering | Supported cases | Supported cases |
| Compare / tracked text changes | Supported cases | Supported cases |
| Tracked character / paragraph formatting | Verified cases | Verified Hancom 2020 cases |
| Tracked table-row insertion / deletion | Supported cases | Not supported; explicitly rejected |
| Identical Word/Hancom pagination | **Not guaranteed** | **Not guaranteed** |

Some expert/backend APIs differ. Direct DOCX access may use `python-docx`. HWPX behavior and layout vary by Hancom version. See [compatibility](https://github.com/rydolabs/PyWPDoc/blob/main/docs/COMPATIBILITY.md) and [limitations](https://github.com/rydolabs/PyWPDoc/blob/main/KNOWN_ISSUES.md). Cross-format `rebuild()` is **not** a full-fidelity converter; unsupported paths reject rather than silently changing content.

## Tested in practice, not only against XML

The project has documented regression tests and Windows native Office validation. The 2026-10-18 Windows QA recorded **48/48 document open-save validations and 48/48 PDF exports** for 24 synthetic business scenarios × 2 formats. These were run on the supplied historical build; they **are not a claim that this reorganized release candidate has passed Windows native validation**.

[Portable test tiers](https://github.com/rydolabs/PyWPDoc/blob/main/tests/README.md) · [Test evidence](https://github.com/rydolabs/PyWPDoc/blob/main/docs/testing/README.md) · [Windows QA](https://github.com/rydolabs/PyWPDoc/tree/main/tests/native) · [QA generators](https://github.com/rydolabs/PyWPDoc/tree/main/tests/generators/business_docs)

```bash
python -m pip install -e ".[test,unified]"
python scripts/run_public_tests.py -q -m "not native and not performance"
```

The legacy private source fixture is not included in this public repository. Tests requiring it are explicitly excluded or skipped. Native COM and visual checks require locally installed Word/Hancom and are not run on generic hosted CI.

## One package, one public API

Only the `pywpdoc` Python package is distributed. The unified API lives at
`pywpdoc.Document`; format-specific backends and shared implementation reside
under `pywpdoc` (including the private `pywpdoc._engine` package).

The engine is an **implementation detail**, not a second product to install.
Use `from pywpdoc import Document` for application code. The reorganized package
has not yet undergone its own Windows native Office acceptance test.

## More information

[User guide](https://github.com/rydolabs/PyWPDoc/blob/main/docs/USAGE.md) · [API strategy](https://github.com/rydolabs/PyWPDoc/blob/main/docs/API_STRATEGY.md) · [Quality gates](https://github.com/rydolabs/PyWPDoc/blob/main/QUALITY_GATES.md) · [Changelog](https://github.com/rydolabs/PyWPDoc/blob/main/CHANGELOG.md) · [Security](https://github.com/rydolabs/PyWPDoc/blob/main/SECURITY.md) · [Contributing](https://github.com/rydolabs/PyWPDoc/blob/main/CONTRIBUTING.md)

This repository is source and test code. It does not include Microsoft Word or Hancom Office. **Current release candidate: `0.44.0rc1` (review build; not yet published).** There is no live CI badge until the Actions workflow runs successfully.

**License:** [MIT](https://github.com/rydolabs/PyWPDoc/blob/main/LICENSE) · © 2026 Rydolabs · [Third-party notices](https://github.com/rydolabs/PyWPDoc/blob/main/THIRD_PARTY_NOTICES.md)
