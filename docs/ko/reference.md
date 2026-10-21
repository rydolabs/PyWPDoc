# 한국어 공개 API 레퍼런스

기준 버전: **0.44.0**. 이 페이지는 `from pywpdoc import Document`의 공통 API를 설명합니다. 아래 `backend`의 자동 위임 기능은 모두 공식 지원 대상이라는 뜻이 아닙니다.

## 생성·저장

| 메서드 / 속성 | 반환 | 조건 |
|---|---|---|
| `Document.new(format="hwpx", *, compatibility=None)` | `Document` | `format`: `docx`/`hwpx`, `compatibility`는 HWPX 전용 |
| `Document.open(path)` | `Document` | `.docx` 또는 `.hwpx` 확장자 필요 |
| `doc.format` | `str` | `docx` / `hwpx` |
| `doc.save(path)` | `None` | 다른 형식으로 변환하지 않음 |

## 문서·구조

| 메서드 / 속성 | 반환 | 설명 |
|---|---|---|
| `doc.paragraphs`, `doc.tables`, `doc.sections` | 리스트 | 실제 요소는 포맷별 래퍼 |
| `doc.pictures` | 리스트 | 그림 래퍼 |
| `doc.styles`, `doc.core_properties` | 포맷별 래퍼 | 스타일·속성 |
| `doc.add_paragraph(text="", style=None)` | 문단 객체 | 새 문단 |
| `doc.add_table(rows, cols, style=None)` | 표 객체 | 새 표 |
| `doc.add_picture(image_data, image_format=None, *, width=None, height=None, treat_as_char=True)` | 그림 객체 | PNG/JPEG/GIF/BMP 자동 판별; 크기 명시 권장 |
| `doc.add_section()` | 구역 객체 | **인자 없는 공통 호출만 지원** |

## 텍스트·템플릿·비교

| 메서드 | 반환 | 원본 변경 |
|---|---|---|
| `find(query, *, everywhere=True, case_sensitive=True, count=-1)` | 검색 결과 목록 | 없음 |
| `preview_replace(search, replacement, *, everywhere=True, case_sensitive=True, count=-1)` | `ReplacementPreviewReport` | 없음 |
| `replace_text(search, replacement, *, everywhere=True, case_sensitive=True, count=-1)` | `int` | 있음 |
| `find_regex(pattern, *, everywhere=True, flags=0, count=-1)` | 검색 결과 | 없음 |
| `replace_regex(pattern, replacement, *, everywhere=True, flags=0, count=-1)` | `int` | 있음 |
| `check_template(data, *, everywhere=True, sections=False, table_rows=False)` | `TemplateCheckReport` | 없음 |
| `render_template(data, *, everywhere=True, missing="keep", sections=False, table_rows=False)` | `int` | 있음 |
| `compare(new, *, author="PyWPDoc", date=None, everywhere=True)` | 새 `Document` | 없음 |

고급 원시 접근: `doc.backend`는 포맷별 Backend 래퍼, `doc.native`/`doc.unwrap()`은 원시 객체입니다. `doc.docx`, `doc.hwpx`는 **자기 포맷에서만** 지원합니다. `rebuild()`는 범용 형식 변환기가 아닙니다.

[결과와 예외](errors.md) · [형식별 차이 (영문)](../reference/formats.md) · [제약 사항](limitations.md)
