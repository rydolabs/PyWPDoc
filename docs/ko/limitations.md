# 제약 사항

- `.hwp` 바이너리는 현재 지원 형식이 아닙니다. DOCX/HWPX만 사용합니다.
- `rebuild()`는 범용 문서 변환기가 아니며, DOCX → HWPX 이식 불가능한 경로는 명시적으로 거부합니다.
- Word와 한컴은 페이지 나누기·줄바꿈을 동일하게 렌더링하지 않을 수 있습니다.
- `add_picture()`는 공통 인자지만 기본 크기가 다르므로 `Mm`로 명시적으로 크기를 지정하세요.
- 공통 `add_section()`은 인자 없는 사용만 지원합니다. `after`, `start_type`은 각각의 전용 API입니다.
- 변경 추적 비교는 모든 문서 구조 변경을 지원하지 않으며 불안전한 변경은 `DocumentUnsupportedError`를 발생시킵니다.
- `doc.fill()`, `doc.validate()`, `doc.merge()`, `doc.replace_image()`, `doc.accept_changes()` 등은 현재 공식 구현으로 보장하지 않습니다.
- 제품 소스 구조가 변경된 0.44.0rc1은 이전 Windows Word/한컴 QA 통과를 그대로 승계했다고 주장하지 않습니다. 별도 네이티브 검증이 필요합니다.

[공통 API 안내](api.md) · [영문 전체 제약](../limitations.md)
