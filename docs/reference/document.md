# `pywpdoc.Document` API Reference

**Which API fits the task?** See [AI agent / task selection](../agent-guide.md) first, then consult the explicit signatures below. These cover editable Word DOCX and Hancom Hangul HWPX, not legacy binary `.hwp` or universal format conversion.

For **0.44.0rc1**. This is the *documented common contract*; backend passthrough names are **not** guaranteed portable. All paths accept `str | pathlib.Path` where noted.

## Constructors and format

| Signature | Returns | Failure / note |
| --- | --- | --- |
| `Document.new(format="hwpx", *, compatibility=None)` | new `Document` | `format`: `"docx"` / `"hwpx"`. `compatibility` only for HWPX. Unknown format → `DocumentValueError`. |
| `Document.open(source)` | loaded `Document` | Format from `.docx`/`.hwpx` suffix; invalid extension → `DocumentValueError`; malformed file may raise parser errors. |
| `doc.format` | `str` | `"docx"` or `"hwpx"` |
| `doc.save(path)` | `None` | Save to a path; **not** cross-format conversion. |

## Document structure

| API | Returns | Notes |
| --- | --- | --- |
| `doc.paragraphs` | `list[Paragraph]` | Backend-owned wrappers, top-level paragraphs. |
| `doc.tables` | `list[Table]` | Backend-owned wrappers, top-level tables. |
| `doc.sections` | `list[Section]` | Format-specific Section wrappers. |
| `doc.pictures` | `list[Picture]` | Format-specific Picture wrappers. |
| `doc.styles` | `Styles` | Backend-owned style collection. |
| `doc.core_properties` | `CoreProperties` | Metadata wrapper. |
| `doc.add_paragraph(text="", style=None)` | `Paragraph` | Append a paragraph. `style` interpretation may differ. |
| `doc.add_table(rows, cols, style=None)` | `Table` | Positive row and column counts. |
| `doc.add_picture(image_data, image_format=None, *, width=None, height=None, treat_as_char=True)` | `Picture` | PNG/JPEG/GIF/BMP auto-detection; explicit sizing recommended. [Details](../guide/pictures-sections.md). |
| `doc.add_section()` | `Section` | Portable **no-argument** subset. Per-format controls only via backend. |

## Text and automation

| API | Returns | Mutation |
| --- | --- | --- |
| `find(query, *, everywhere=True, case_sensitive=True, count=-1)` | list of `FindMatch` | No |
| `preview_replace(search, replacement, *, everywhere=True, case_sensitive=True, count=-1)` | `ReplacementPreviewReport` | No |
| `replace_text(search, replacement, *, everywhere=True, case_sensitive=True, count=-1)` | `int` | Yes |
| `find_regex(pattern, *, everywhere=True, flags=0, count=-1)` | regex matches | No |
| `replace_regex(pattern, replacement, *, everywhere=True, flags=0, count=-1)` | `int` | Yes |
| `check_template(data, *, everywhere=True, sections=False, table_rows=False)` | `TemplateCheckReport` | No |
| `render_template(data, *, everywhere=True, missing="keep", sections=False, table_rows=False)` | `int` | Yes |
| `compare(new, *, author="PyWPDoc", date=None, everywhere=True)` | new `Document` | Original unchanged; structural constraints. |

## Expert / not portable

`doc.backend`, `doc.native`, `doc.unwrap()`, `doc.docx`, `doc.hwpx`, `Document.rebuild()`, `doc.rebuild_from()`, and `doc.export_snapshot()` are for advanced use. `rebuild()` is **not** a universal format converter. In particular, DOCX → HWPX rebuild rejects unsupported portable snapshot import.

For **runnable, CI-tested workflows** (create, preflight template, preview replacement and save/reopen) see the [agent guide](../agent-guide.md) and [quickstart](../getting-started/quickstart.md). Avoid relying on undocumented backend passthrough attributes in portable code.

See [result types and exceptions](results-errors.md), [format-specific APIs](formats.md), and [compatibility](../compatibility.md).
