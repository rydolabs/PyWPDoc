# Template preflight and rendering

```python
--8<-- "examples/manual/template.py"
```

Run: `python examples/manual/template.py docx ./output` (also `hwpx`).

- `check_template(data, *, everywhere=True, sections=False, table_rows=False)` is **read-only**, returning `TemplateCheckReport`.
- `report.ok`, `tag_count`, `missing_keys`, `missing_count`, and `issues` let you decide whether to render.
- `render_template(data, *, everywhere=True, missing="keep", sections=False, table_rows=False)` **modifies the document**, returning the number of processed substitutions.
- Section and table-row repetition are more advanced: enable `sections=True`/`table_rows=True` **only** for templates designed for the corresponding syntax. Test real documents before bulk processing.

Run preflight before modifying customer files. For read-only analysis, call only `check_template`, not `render_template`.
