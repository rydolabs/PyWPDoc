# 반환값·오류 처리

| 결과 객체 | 주요 필드 / 동작 |
|---|---|
| `FindMatch` | `paragraph`, `paragraph_index`, `start`, `end`, `text` |
| `ReplacementPreviewReport` | `count`, `has_matches`, `matches`, `to_dict()`, `to_json()` |
| `TemplateCheckReport` | `ok`, `tag_count`, `checked_values`, `resolved_values`, `missing_count`, `missing_keys`, `issues` |
| `TemplateCheckIssue` | `code`, `message`, `paragraph_index`, `key`, `offset`, `tag` |

```python
from pywpdoc import Document, DocumentError, DocumentUnsupportedError

doc = Document.new("hwpx")
doc.add_paragraph("{{name}}")
report = doc.check_template({})
if not report.ok:
    print(report.missing_keys)
```

- `DocumentValueError`: 허용되지 않는 형식·인자·빈 검색어·식별 불가 이미지 등의 입력 오류.
- `DocumentUnsupportedError`: 포맷의 미지원 기능이나 안전하지 않은 구조 변경.
- `DocumentStateError`: 잘못된 문서 상태에서 호출.
- `DocumentError`: 위 계열의 공통 기반 예외. `code`, `context`, `suggestion`, `to_dict()` 이용.

파일이 손상됐거나 선택 의존성이 없을 때는 표준 Python 예외나 백엔드 예외도 발생할 수 있습니다. 위 표가 가능한 모든 예외의 전부는 아닙니다.
