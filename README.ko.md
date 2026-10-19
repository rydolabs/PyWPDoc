<div align="center">

# PyWPDoc

### 문서 자동화에 검증과 변경 추적까지.

**Word 문서의 템플릿 태그를 검사하고, 치환 내용을 미리 보고, 변경 추적 문서를 생성하세요.**

**설치는 한 번, API는 하나.** Word **DOCX**를 중심으로, 필요한 경우 한컴 한글 **HWPX**까지 지원합니다.

[**빠른 시작**](#설치와-빠른-시작) · [**공통 API 문서**](https://rydolabs.github.io/PyWPDoc/reference/document/) · [**템플릿 처리**](https://rydolabs.github.io/PyWPDoc/ko/guide/templates/) · [**변경 추적**](https://rydolabs.github.io/PyWPDoc/ko/guide/compare/) · [**English**](https://github.com/rydolabs/PyWPDoc/blob/main/README.md)

Python 3.10 이상 · MIT 라이선스

</div>

## 설치와 빠른 시작

```bash
pip install pywpdoc
```

**`0.44.0`부터** 이 명령만으로 DOCX와 HWPX를 모두 사용할 수 있습니다. 기존 PyPI의 `0.44.0rc1`을 사용하는 경우 DOCX 지원을 위해 `pip install "pywpdoc[unified]==0.44.0rc1"`이 필요합니다. 호환성을 위해 `[unified]` 옵션은 계속 사용할 수 있습니다.

```python
from pywpdoc import Document

doc = Document.new("docx")
doc.add_paragraph("Quarterly business report")
doc.save("report.docx")
```

![이전 Windows QA에서 실제 Microsoft Word로 출력한 DOCX 계약 문서](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/contract-word.png)

*기존 Windows Word 출력 기록으로 신규 0.44.0 스크린샷은 아닙니다. [이미지 출처](https://github.com/rydolabs/PyWPDoc/blob/main/docs/assets/readme/PROVENANCE.md).*

## 문서 생성 이상의 세 가지 기능

### 1. 템플릿 태그를 확인하고 실제 데이터로 치환

```python
from pywpdoc import Document

doc = Document.new("docx")
doc.add_paragraph("고객: {{customer.name}}")
data = {"customer": {"name": "Acme Corp"}}

report = doc.check_template(data)  # 읽기 전용 검사
if not report.ok:
    raise ValueError(f"누락·오류 태그: {report.missing_keys}")

doc.render_template(data)
doc.save("contract.docx")
```

**처리 전:** `고객: {{customer.name}}` → **처리 후:** `고객: Acme Corp`

[템플릿 가이드](https://rydolabs.github.io/PyWPDoc/ko/guide/templates/)

### 2. 비교 결과를 변경 추적 문서로 생성

```python
from pywpdoc import Document

before = Document.new("docx")
before.add_paragraph("Contract amount: $1,000")

after = Document.new("docx")
after.add_paragraph("Contract amount: $1,200")

review = before.compare(after, author="Reviewer")
review.save("contract-review.docx")
```

지원되는 텍스트 변경을 별도 문서의 네이티브 변경 추적 구조로 생성합니다. 모든 구조 변경을 비교하는 범용 diff 엔진은 아닙니다. [변경 추적 가이드](https://rydolabs.github.io/PyWPDoc/ko/guide/compare/)

### 3. 수정하기 전에 치환 대상을 미리 확인

```python
from pywpdoc import Document

doc = Document.open("report.docx")
preview = doc.preview_replace("Draft", "Approved")
print(preview.count)

if preview.has_matches:
    doc.replace_text("Draft", "Approved")
    doc.save("report-approved.docx")
```

`preview_replace()`는 실제 문서를 변경하지 않습니다. [검색·치환 가이드](https://rydolabs.github.io/PyWPDoc/ko/guide/search-replace/)

## 실제 문서 출력 이미지

**템플릿 처리 및 변경 추적의 실제 Word 출력 이미지가 필요하다면** [Windows 원클릭 스크린샷 도구](https://github.com/rydolabs/PyWPDoc/blob/main/tests/showcase/README.md)를 실행하세요. 저장소 ZIP을 풀고 `tests/showcase/RUN_SCREENSHOTS_WINDOWS.bat`를 더블클릭하면 테스트 문서와 가능한 네이티브 PDF·PNG 출력이 ZIP으로 묶입니다.


아래 이미지는 **이전 Windows 네이티브 Word/한컴 테스트에서 생성한 PDF 페이지 렌더링**입니다. 화면을 임의로 그린 목업이 아니며, 위 변경 추적·템플릿 예제의 실행 화면도 아닙니다.

**Microsoft Word DOCX 복잡한 표**

![실제 Windows Word로 출력한 DOCX 표 QA 이미지](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/complex-tables-docx.png)

**Word와 한컴 양쪽 형식 비교**

![Windows Word DOCX와 한컴 HWPX 출력 비교](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/docx-hwpx-contract-comparison.png)

*출처: [이미지 검증 기록](https://github.com/rydolabs/PyWPDoc/blob/main/docs/assets/readme/PROVENANCE.md). DOCX/HWPX 출력 레이아웃의 완전 일치는 보장하지 않습니다. 이 이미지를 새로운 0.44.0 PDF 시각 검증이라고 주장하지 않습니다.*

## 바로 가는 API 문서

| 필요한 기능 | 설명서 |
| --- | --- |
| 설치·빠른 시작 | [설치](https://rydolabs.github.io/PyWPDoc/ko/quickstart/) |
| 공통 `Document` API | [정확한 메서드 명세](https://rydolabs.github.io/PyWPDoc/reference/document/) |
| 템플릿 태그 검사·렌더링 | [템플릿 처리](https://rydolabs.github.io/PyWPDoc/ko/guide/templates/) |
| 검색·미리보기·치환 | [안전한 텍스트 수정](https://rydolabs.github.io/PyWPDoc/ko/guide/search-replace/) |
| 변경 추적 | [문서 비교](https://rydolabs.github.io/PyWPDoc/ko/guide/compare/) |
| 결과·예외 | [반환값과 오류](https://rydolabs.github.io/PyWPDoc/ko/errors/) |
| AI 코딩 도우미 | [에이전트 가이드](https://rydolabs.github.io/PyWPDoc/ko/agent-guide/) |

[테스트된 전체 예제](https://github.com/rydolabs/PyWPDoc/tree/main/examples/manual) · [공식 영문 API 레퍼런스](https://rydolabs.github.io/PyWPDoc/reference/document/) · [CI](https://github.com/rydolabs/PyWPDoc/actions/workflows/ci.yml)

## 지원 범위

DOCX와 HWPX 문서 생성·편집·검색·템플릿과 지원되는 텍스트 변경 비교를 제공합니다. **레거시 `.hwp` 직접 읽기, DOCX↔HWPX 범용 무손실 변환, 모든 구조적 변경의 추적, Word·한컴의 픽셀 단위 동일 출력은 보장하지 않습니다.** [호환성](https://rydolabs.github.io/PyWPDoc/compatibility/) · [제한 사항](https://rydolabs.github.io/PyWPDoc/ko/limitations/)

[PyPI](https://pypi.org/project/pywpdoc/) · [GitHub](https://github.com/rydolabs/PyWPDoc) · [한국어 설명서](https://rydolabs.github.io/PyWPDoc/ko/) · [라이선스](https://github.com/rydolabs/PyWPDoc/blob/main/LICENSE)

**버전: 0.44.0.**
