# Compare with tracked changes

```python
--8<-- "examples/manual/compare.py"
```

Run: `python examples/manual/compare.py hwpx ./output` (or `docx`).

`before.compare(after, *, author="PyWPDoc", date=None, everywhere=True)` returns a **new** document with supported tracked text changes. It is *not* a generic diff/merge engine. Both sources must be compatible in format and structure. Some paragraph insertion/deletion, table movement, structural changes and unsupported revisions deliberately raise `DocumentUnsupportedError` instead of silently dropping content. See [limitations](../limitations.md).

Native Word/Hancom visual verification remains separate from unit tests.
