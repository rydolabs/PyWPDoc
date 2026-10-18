# Find, preview and replace text

```python
--8<-- "examples/manual/search_replace.py"
```

Run: `python examples/manual/search_replace.py hwpx ./output` (also `docx`).

| Method | Return | Mutates document? |
| --- | --- | --- |
| `find(query, *, everywhere=True, case_sensitive=True, count=-1)` | list of matches | No |
| `preview_replace(search, replacement, *, everywhere=True, case_sensitive=True, count=-1)` | `ReplacementPreviewReport` | **No** |
| `replace_text(search, replacement, *, everywhere=True, case_sensitive=True, count=-1)` | number replaced (`int`) | Yes |
| `find_regex(pattern, *, everywhere=True, flags=0, count=-1)` | matches | No |
| `replace_regex(pattern, replacement, *, everywhere=True, flags=0, count=-1)` | number replaced (`int`) | Yes |

`everywhere=False` limits traversal to the scope defined by the text feature; do not assume it searches all headers and nested tables. Unsafe field/revision boundaries and empty-length regex matches may be rejected. Preview offsets are **logical text positions**, not screen coordinates. See [results and errors](../reference/results-errors.md).
