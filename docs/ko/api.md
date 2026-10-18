# Common API 사용법

## 공통 진입점

```python
from pywpdoc import Document

doc = Document.new("hwpx")  # 또는 "docx"
doc.add_paragraph("공통 API")
doc.add_table(1, 1).cell(0, 0).text = "첫 셀"
doc.save("sample.hwpx")
```

`Document.new()` 기본 형식은 **HWPX**입니다. 형식을 명시하는 것을 권장합니다. `.open()`은 파일 확장자로 형식을 인식하며 `.save()`는 포맷 변환 기능이 아닙니다.

## 많이 사용하는 메서드

| 기능 | API | 주의 |
| --- | --- | --- |
| 새 문서 | `Document.new("docx")` / `("hwpx")` | HWPX 호환성 프로파일은 HWPX 전용 |
| 문단·표 | `add_paragraph()`, `add_table()` | 실제 객체는 포맷별 래퍼 |
| 검색 | `find()`, `find_regex()` | 읽기 전용 |
| 치환 미리보기 | `preview_replace()` | 문서를 수정하지 않음 |
| 치환 | `replace_text()`, `replace_regex()` | 원본 객체의 내용 변경 |
| 템플릿 검사 | `check_template(data)` | `TemplateCheckReport` 반환 |
| 템플릿 처리 | `render_template(data)` | 실제 텍스트 수정, 치환 개수 반환 |
| 변경 추적 | `before.compare(after)` | 일부 구조 변경은 거부 |
| 이미지 | `add_picture(bytes, width=Mm(25))` | PNG/JPEG/GIF/BMP 시그니처 판별; 너비 지정 권장 |
| 구역 | `add_section()` | 공통은 인자 없는 사용만 보장 |

그림: `pywpdoc.Mm`로 너비·높이를 명시하면 형식 간 크기 차이를 줄일 수 있습니다. 생략하면 DOCX는 원본 이미지 크기를, HWPX는 기본 너비 2인치를 사용합니다. 구역의 `start_type`(DOCX), `after`(HWPX)는 포맷 전용 API에서만 사용합니다.

## 공통 객체와 원시 엔진 구분

- `doc.backend`: 포맷별 백엔드 래퍼
- `doc.native`, `doc.unwrap()`: 원시 문서 객체
- `doc.docx` / `doc.hwpx`: **일치하는 포맷**의 원시 객체만 제공

`__getattr__`를 통해 내부 백엔드의 메서드가 추가로 보일 수 있지만 공식 Common API라고 보장하지 않습니다. 정확한 메서드 시그니처·반환값·예외는 [영어 API Reference](../reference/document.md)와 [결과·예외](../reference/results-errors.md)를 참고하세요.


[한국어 API 레퍼런스](reference.md) · [이미지·구역](guide/pictures-sections.md) · [템플릿](guide/templates.md)
