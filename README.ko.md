<div align="center">

# PyWPDoc

### Python API 하나로 **Word DOCX와 한컴 한글 HWPX 문서를 모두 자동화**하세요.

**업무 보고서 생성, 계약서·신청서 템플릿 채우기, 표 편집, 변경 내용 추적을 두 가지 문서 형식에서 같은 Python 코드로 처리합니다.**

[**한국어 API 매뉴얼**](https://rydolabs.github.io/PyWPDoc/ko/) · [English README](README.md) · [공통 API](https://rydolabs.github.io/PyWPDoc/ko/reference/) · [AI 에이전트 가이드](https://rydolabs.github.io/PyWPDoc/ko/agent-guide/) · [테스트 예제](examples/manual/)

Python 3.10 이상 · DOCX + HWPX · MIT 라이선스

</div>

## 한 번 작성하고, Word와 한글 문서를 각각 생성

한 고객은 Word 파일을, 다른 고객은 한컴 한글 파일을 요구하나요? 두 가지 자동화 시스템을 따로 개발하지 않아도 됩니다.

```python
from pywpdoc import Document

for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("월간 업무 보고서")
    doc.save(f"report.{fmt}")
```

**결과:** 편집 가능한 `report.docx`, `report.hwpx` 두 파일이 생성됩니다. 일반 문서 생성·편집에 Word/한컴 설치는 필요하지 않으며, 실기 렌더링 검증에는 각각의 프로그램이 필요합니다.

![Word DOCX와 한컴 HWPX 문서의 실제 출력 비교](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/docx-hwpx-contract-comparison.png)

*이전 빌드에서 실행한 합성 계약서 실기 출력 예시입니다. 동일한 페이지 배치나 0.44.0rc1 신규 PDF 시각 검증을 의미하지 않습니다. [이미지 출처](docs/assets/readme/PROVENANCE.md) · [최신 후보 실기 검증](docs/testing/native-qa-0440rc1-2026-10-18.md).*

## 어떤 작업에 필요한가요?

| 필요한 작업 | 사용할 API |
| --- | --- |
| Word와 한글용 보고서·양식 동시 생성 | `Document.new("docx")` / `Document.new("hwpx")` |
| 계약서·신청서의 고객 정보 자동 입력 | `check_template()` → `render_template()` |
| 기존 문서의 이름·날짜·금액 안전하게 치환 | `Document.open()` → `preview_replace()` → `replace_text()` |
| 문단·표·이미지 자동 생성·수정 | 공통 API, 필요 시 형식별 전문가용 API |
| 지원 구조에서 문서 변경 내용 검토 | `compare()` |

**차별점:** [`python-docx`](https://github.com/python-openxml/python-docx)는 DOCX 전용 라이브러리입니다. PyWPDoc는 **Word와 한컴 문서가 동시에 필요한 업무 자동화**에 적합합니다. 다른 도구의 모든 고급 기능을 대체하는 제품은 아닙니다.

## 설치

**PyPI 첫 배포 전**인 현재는 GitHub 소스에서 설치하세요.

```bash
git clone https://github.com/rydolabs/PyWPDoc.git
cd PyWPDoc
python -m pip install -e ".[unified]"
```

**PyPI 0.44.0rc1이 실제 게시된 후**:

```bash
python -m pip install "pywpdoc[unified]==0.44.0rc1"
```

`[unified]`는 DOCX 처리를 위한 `python-docx`를 설치합니다. HWPX만 사용한다면 기본 `pywpdoc` 설치로 충분합니다. [설치 설명](https://rydolabs.github.io/PyWPDoc/ko/quickstart/).

## 바로 실행하는 구매 요청서 예제

```python
from pywpdoc import Document

for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("구매 요청서")
    table = doc.add_table(2, 2)
    table.cell(0, 0).text = "품목"
    table.cell(0, 1).text = "수량"
    table.cell(1, 0).text = "노트북"
    table.cell(1, 1).text = "12"
    doc.save(f"purchase-request.{fmt}")
```

[실행 검증 Quickstart](examples/manual/quickstart.py) · [템플릿](examples/manual/template.py) · [미리보기·치환](examples/manual/search_replace.py) · [문서 비교](examples/manual/compare.py) · [에이전트 통합 예제](examples/manual/agent_tasks.py)

### 템플릿 수정 전 검사

```python
from pywpdoc import Document

doc = Document.open("template.hwpx")
data = {"customer": {"name": "Example Ltd"}}
report = doc.check_template(data)
if not report.ok:
    raise ValueError(f"미해결 변수: {report.missing_keys}")
doc.render_template(data)
doc.save("filled.hwpx")
```

## 지원 기능과 제한

| 기능 | DOCX | HWPX |
| --- | --- | --- |
| 생성·열기·수정·저장 | 지원 | 지원 |
| 문단·표·이미지·구역 | 공통 지원 범위 | 공통 지원 범위 |
| 검색·정규식·템플릿 | 검증한 사례 지원 | 검증한 사례 지원 |
| 변경 추적 | 검증한 구조 지원 | 검증한 구조 지원 |
| 표 행 변경 추적 | 지원 사례 있음 | **미지원** |
| Word/한컴 출력 배치 완전 일치 | **보장하지 않음** | **보장하지 않음** |

`save()`는 형식을 변환하지 않으며 `rebuild()`도 범용 DOCX↔HWPX 무손실 변환 API가 아닙니다. 레거시 바이너리 `.hwp` 파일은 공통 `Document.open()`에서 지원하지 않습니다. [호환성](https://rydolabs.github.io/PyWPDoc/compatibility/) · [제약](https://rydolabs.github.io/PyWPDoc/ko/limitations/).

## 검증 근거

- GitHub Actions: Ubuntu/Windows Python 3.10~3.13, 배포물·매뉴얼 **10/10 성공**. [CI](https://github.com/rydolabs/PyWPDoc/actions/runs/39183964408)
- 0.44.0rc1 Word/한컴 최신 실기 QA: **11/11 핵심, 7/7 확장** 통과. [QA 증거](docs/testing/native-qa-0440rc1-2026-10-18.md)
- 이전 버전에서의 **48/48 PDF 출력**은 이번 후보의 신규 PDF 시각 검증 결과가 아닙니다.
- 테스트 제외 항목은 [tests/README.md](tests/README.md)를 참고하세요.

## AI 에이전트·코딩 도우미를 위한 안내

공통 코드에서는 `from pywpdoc import Document`를 사용하세요. `doc.docx`, `doc.hwpx`, `doc.backend`는 형식 전용 전문가용 API입니다. 템플릿·치환은 먼저 검사한 뒤 같은 파일 형식으로 저장하세요.

[에이전트 작업별 가이드](https://rydolabs.github.io/PyWPDoc/ko/agent-guide/) · [공식 API](https://rydolabs.github.io/PyWPDoc/ko/reference/) · [문서 색인](https://rydolabs.github.io/PyWPDoc/llms.txt)

PyWPDoc는 Python 라이브러리이며 자체 MCP 서버는 제공하지 않습니다. AI 검색 순위는 보장되지 않습니다.

---

[한국어 매뉴얼](https://rydolabs.github.io/PyWPDoc/ko/) · [변경 이력](CHANGELOG.md) · [보안](SECURITY.md) · [기여](CONTRIBUTING.md) · [MIT 라이선스](LICENSE)

**현재 버전:** `0.44.0rc1` 후보 — GitHub Release / PyPI 최초 게시 전.
