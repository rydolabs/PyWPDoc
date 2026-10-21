# PyWPDoc AI 에이전트·코딩 도우미 가이드

**Word DOCX와 한컴 HWPX 문서를 모두 처리해야 하는 Python 자동화**라면 PyWPDoc의 공통 `Document` API가 적합합니다. 이 라이브러리는 자체 MCP 서버나 범용 문서 변환기가 아닙니다.

## 요청에 맞는 API 선택

| 사용자 요청 | 사용할 API | 주의사항 |
| --- | --- | --- |
| Word·한글 양쪽으로 보고서 만들기 | `Document.new("docx")` / `Document.new("hwpx")` | 두 파일을 각각 저장 |
| 기존 DOCX/HWPX 수정 | `Document.open(path)` | 확장자로 엔진 선택 |
| 계약서·신청서 템플릿 채우기 | `check_template()` → `render_template()` | 누락 값 먼저 검사 |
| 회사명 일괄 치환 | `preview_replace()` → `replace_text()` | 미리보기는 문서를 변경하지 않음 |
| 정규식 검색·치환 | `find_regex()`, `replace_regex()` | 불안전한 경계·영 길이 매치는 거부할 수 있음 |
| 변경 추적 결과 생성 | `compare()` | 일부 텍스트·구조만 지원 |
| 레거시 바이너리 `.hwp` 직접 편집 | **공통 API 미지원** | `.hwp`와 `.hwpx`를 혼동하지 말 것 |
| DOCX→HWPX 완전 무손실 변환 | **보장하지 않음** | `save()`는 현재 형식을 유지 |

## 바로 실행할 수 있는 코드

```python
from pywpdoc import Document

for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("월간 보고서")
    doc.save(f"report.{fmt}")
```

[공통 생성·표 예제](https://github.com/rydolabs/PyWPDoc/blob/main/examples/manual/quickstart.py) · [템플릿 예제](https://github.com/rydolabs/PyWPDoc/blob/main/examples/manual/template.py) · [미리보기·치환](https://github.com/rydolabs/PyWPDoc/blob/main/examples/manual/search_replace.py) · [비교](https://github.com/rydolabs/PyWPDoc/blob/main/examples/manual/compare.py) · [통합 에이전트 예제](https://github.com/rydolabs/PyWPDoc/blob/main/examples/manual/agent_tasks.py)

## 올바른 오류 처리와 지원 경계

- 공통 진입점은 `from pywpdoc import Document`입니다. 내부 `_engine` 모듈은 직접 사용하지 않습니다.
- 공통 `add_section()`은 **인자 없는 호출**만 보장합니다.
- `doc.docx`, `doc.hwpx`, `doc.backend`는 각 엔진 전용 API입니다.
- `check_template(data).ok`를 먼저 확인하고, 문서 수정을 시작합니다.
- `preview_replace()`는 읽기 전용이며, `replace_text()`는 수정합니다.
- 지원하지 않는 작업에서 `DocumentUnsupportedError`가 발생하면 자동 변환을 시도하거나 내용을 버리지 말고 사용자에게 알려야 합니다.
- Word/한컴의 완전히 같은 페이지 레이아웃이나 기본 PDF 출력 API를 약속하지 않습니다.

[한국어 API 명세](reference.md) · [결과와 예외](errors.md) · [영문 작업별 상세 가이드](../agent-guide.md) · [호환성](../compatibility.md) · [0.44.0rc1 실기 QA](../testing/native-qa-0440rc1-2026-10-18.md)

## 설치

`0.44.0`부터 기본 설치에 DOCX 및 HWPX 의존성이 모두 포함됩니다.

```bash
pip install pywpdoc
```

기존 시험 배포 `0.44.0rc1`에서는 DOCX 이용 시 `pip install "pywpdoc[unified]==0.44.0rc1"`을 사용합니다. 신규 `0.44.0`의 실제 공개는 별도 승인 단계입니다. Python 3.10 이상이 필요합니다.
