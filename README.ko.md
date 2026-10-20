<div align="center">

# PyWPDoc

### 검토 가능한 Word 문서 자동화, Python으로.

**수정 전후 문서를 비교해 변경 추적 파일로 저장하고, 템플릿 누락값과 치환 대상을 실제 수정 전에 확인하세요.**

**Word DOCX 중심** · 한컴 HWPX 추가 지원 · Python 3.10 이상 · MIT

[**시작하기**](#설치) · [**공통 API**](https://rydolabs.github.io/PyWPDoc/reference/document/) · [**변경 추적**](https://rydolabs.github.io/PyWPDoc/ko/guide/compare/) · [**템플릿**](https://rydolabs.github.io/PyWPDoc/ko/guide/templates/) · [**English**](https://github.com/rydolabs/PyWPDoc/blob/main/README.md)

</div>

## 설치

```bash
pip install pywpdoc
```

**0.44.0부터** DOCX/HWPX를 모두 기본 설치로 사용할 수 있습니다. 이미 게시된 **0.44.0rc1**은 DOCX용 추가 의존성을 설치하기 위해 `pip install "pywpdoc[unified]==0.44.0rc1"`을 사용하세요. 기존 `[unified]` 옵션은 호환성을 위해 계속 지원합니다.

## PyWPDoc가 다른 이유

### 1. 수정 전 + 수정 후 → 변경 추적 문서

최종 파일만 덮어쓰지 않고, 지원되는 문서 변경을 **Word에서 검토할 수 있는 변경 추적 문서**로 생성합니다.

| 수정 전 (Before) | 수정 후 (After) |
| --- | --- |
| 계약금액 **USD 10,000** | **USD 12,500** |
| 납기일 **11월 15일** | **12월 1일** |
| 지원기간 **3개월** | **6개월** |

`compare()`는 두 원본을 수정하지 않고 별도 변경 추적 파일을 만듭니다.

```python
from pywpdoc import Document

before = Document.open("agreement-before.docx")
after = Document.open("agreement-after.docx")

review = before.compare(after, author="Reviewer")
review.save("agreement-reviewed.docx")
```

[16개 문단 중 13개를 수정하는 테스트 샘플](https://github.com/rydolabs/PyWPDoc/tree/main/tests/showcase)을 제공합니다. 실제 Word의 **검토 → 모든 변경 내용 표시(All Markup)** 화면을 캡처한 대표 이미지는 가독성을 검토한 뒤 추가할 예정입니다. 기존 PDF에서 변경 표시가 겹친 이미지를 정상적인 Word 스크린샷으로 소개하지는 않습니다.

[**변경 추적 API 및 지원 범위 →**](https://rydolabs.github.io/PyWPDoc/ko/guide/compare/)

### 2. 템플릿 태그 누락을 먼저 검사

```python
from pywpdoc import Document

doc = Document.open("template.docx")
data = {"customer": {"name": "Acme Corp"}}
report = doc.check_template(data)  # 문서를 변경하지 않음
if not report.ok:
    raise ValueError(report.missing_keys)
doc.render_template(data)
doc.save("agreement-filled.docx")
```

`Customer: {{customer.name}}` → **`Customer: Acme Corp`**

문서를 수정하기 전에 누락 변수와 태그 검증 결과를 확인합니다. [**템플릿 API →**](https://rydolabs.github.io/PyWPDoc/ko/guide/templates/)

### 3. 안전한 텍스트 치환 미리보기

```python
doc = Document.open("draft.docx")
preview = doc.preview_replace("Draft", "Approved")
if preview.has_matches:
    doc.replace_text("Draft", "Approved")
    doc.save("approved.docx")
```

`preview_replace()`는 실제 문서를 수정하지 않고 후보 변경 내역을 구조화된 결과로 반환합니다. [**검색·치환 API →**](https://rydolabs.github.io/PyWPDoc/ko/guide/search-replace/)

## 간단한 사용법

```python
from pywpdoc import Document

doc = Document.new("docx")
doc.add_paragraph("Quarterly business report")
doc.save("report.docx")
```

문서를 Python에서 생성·편집할 때 Word/한컴 데스크톱 앱은 필요하지 않습니다. 실제 Word/한컴 프로그램에서의 렌더링 검증은 별도 작업입니다.

## 실제 출력 이미지

아래는 **이전 Windows Word/한컴 실기 QA에서 생성한 진짜 PDF 페이지 출력**입니다. 새 변경 추적 예제의 화면이라고 주장하지 않습니다.

![이전 Windows Word 계약 문서 PDF 출력](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/contract-word.png)

[복잡한 Word 표 이미지 보기](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/complex-tables-docx.png) · [Word DOCX / 한컴 HWPX 출력 비교](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/docx-hwpx-contract-comparison.png) · [원본 출처](https://github.com/rydolabs/PyWPDoc/blob/main/docs/assets/readme/PROVENANCE.md)

## API 문서 바로가기

| 작업 | 공식 문서 |
| --- | --- |
| 공통 메서드·인수·반환값 | [**Document API Reference**](https://rydolabs.github.io/PyWPDoc/reference/document/) |
| 비교 및 변경 추적 | [변경 추적](https://rydolabs.github.io/PyWPDoc/ko/guide/compare/) |
| 템플릿 태그 검사·치환 | [템플릿](https://rydolabs.github.io/PyWPDoc/ko/guide/templates/) |
| 찾기·미리보기·치환 | [텍스트 수정](https://rydolabs.github.io/PyWPDoc/ko/guide/search-replace/) |
| 설치 및 실행 예제 | [빠른 시작](https://rydolabs.github.io/PyWPDoc/ko/quickstart/) |
| 반환값·예외와 AI 에이전트 | [오류·결과](https://rydolabs.github.io/PyWPDoc/ko/errors/) · [에이전트 가이드](https://rydolabs.github.io/PyWPDoc/ko/agent-guide/) |

**지원 범위:** DOCX와 HWPX의 검증된 공통 기능을 제공합니다. `compare()`는 모든 문서 구조 변경을 비교하는 범용 diff가 아니며, 레거시 바이너리 `.hwp`, 무손실 DOCX↔HWPX 변환, 픽셀 단위 출력 일치와 자체 MCP 서버는 제공하거나 보장하지 않습니다. [호환성](https://rydolabs.github.io/PyWPDoc/compatibility/) · [제한 사항](https://rydolabs.github.io/PyWPDoc/ko/limitations/)

[PyPI](https://pypi.org/project/pywpdoc/) · [GitHub](https://github.com/rydolabs/PyWPDoc) · [기존 RC 실기 QA 근거](https://github.com/rydolabs/PyWPDoc/blob/main/docs/testing/native-qa-0440rc1-2026-10-18.md) · [MIT 라이선스](https://github.com/rydolabs/PyWPDoc/blob/main/LICENSE)

**버전: 0.44.0.**
