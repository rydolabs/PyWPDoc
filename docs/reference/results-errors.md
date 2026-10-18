# Result types and errors

These classes are returned by high-level features. They are not all re-exported at the `pywpdoc` package root; import from the corresponding `pywpdoc.features` module when needed.

| Type | Fields / methods | Meaning |
| --- | --- | --- |
| `FindMatch` | `paragraph`, `paragraph_index`, `start`, `end`, `text` | Read-only match in logical paragraph text. |
| `ReplacementPreviewReport` | `count`, `has_matches`, `matches`, `to_dict()`, `to_json()` | Read-only candidate replacements. |
| `ReplacementPreviewMatch` | `paragraph_index`, `start`, `end`, `before`, `after`, `logical_before`, `logical_after` | Preview offsets in logical text. |
| `TemplateCheckReport` | `ok`, `tag_count`, `checked_values`, `resolved_values`, `missing_count`, `missing_keys`, `issues`, `to_dict()` | Read-only preflight summary. |
| `TemplateCheckIssue` | `code`, `message`, `paragraph_index`, `key`, `offset`, `tag` | Individual preflight finding. |

```python
from pywpdoc import Document, DocumentError, DocumentValueError, DocumentUnsupportedError

doc = Document.new("hwpx")
doc.add_paragraph("Hello {{name}}")
report = doc.check_template({})
if not report.ok:
    for issue in report.issues:
        print(issue.code, issue.key)
```

| Exception | When |
| --- | --- |
| `DocumentError` | Shared base class (`.code`, `.context`, `.suggestion`, `.to_dict()`). |
| `DocumentValueError` | Invalid format or arguments, unknown image signature, invalid text query, etc. |
| `DocumentUnsupportedError` | Unsupported feature, wrong-format expert accessor, unsafe structural comparison. |
| `DocumentStateError` | Document in invalid operation state. |

Python and backend/parser exceptions may also arise for malformed files, missing optional dependencies, and operating-system I/O errors. These exceptions are not a complete error taxonomy.
