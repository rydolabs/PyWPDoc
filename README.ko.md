[**API 매뉴얼 (한국어)**](https://github.com/rydolabs/PyWPDoc/blob/main/docs/ko/index.md) · [**전체 API Reference**](https://github.com/rydolabs/PyWPDoc/blob/main/docs/reference/document.md)

<div align="center">

# PyWPDoc

### Python API 하나로 DOCX와 HWPX 모두.

**Microsoft Word 문서와 한컴 한글 문서를 같은 Python 코드로 생성·수정·자동화하세요.**

[English](https://github.com/rydolabs/PyWPDoc/blob/main/README.md) · [빠른 시작](#빠른-시작) · [실제 출력 화면](#실제-word--한컴-출력-화면) · [호환성](#지원-기능과-제한)

*Python 3.10 이상 · DOCX + HWPX · MIT 라이선스*

</div>

## 실제 Word · 한컴 출력 화면

![Windows Word DOCX 출력과 한컴 HWPX 출력 비교](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/docx-hwpx-contract-comparison.png)

*2026-10-18 Windows 네이티브 QA에서 저장·PDF 출력된 실제 문서입니다. DOCX는 Microsoft Word, HWPX는 한컴오피스에서 출력했습니다. 기밀 자료가 아닌 합성 계약서이며 프로그램별 줄바꿈과 페이지 배치는 다를 수 있습니다.*

```python
from pywpdoc import Document

for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("분기 업무 보고서")
    doc.save(f"report.{fmt}")
```

한 번 작성한 코드로 편집 가능한 `report.docx`, `report.hwpx` 두 문서를 만듭니다.

## 설치

PyPI에 **첫 배포가 완료된 후**에는 다음처럼 설치합니다.

```bash
python -m pip install "pywpdoc[unified]"
```

`unified` 옵션은 DOCX 처리에 필요한 `python-docx`를 포함합니다. HWPX만 사용할 경우 `pip install pywpdoc`로 설치할 수 있습니다. 현재 `0.44.0rc1`은 **검토용 후보이며 아직 PyPI에 게시하지 않았습니다.**

## 다른 라이브러리와 차별점

| 작업 | 포맷 전용 도구 | PyWPDoc |
| --- | --- | --- |
| Word + 한글 동시 생성 | 서로 다른 문서 API를 따로 연결 | `Document.new(fmt)` 공통 호출 |
| 문단·표 자동화 | 포맷별 코드 작성 | 지원 범위 내에서 공통 인터페이스 |
| 템플릿 | 포맷별 치환 로직 필요 | 공통 템플릿 검사·치환 |
| 검색·교체·비교 | 포맷별 구현 차이 | 공통 검색·정규식·비교 API |
| 출력 품질 확인 | 외부 QA 구성 필요 | Windows Word/한컴 검증 시나리오 제공 |

[`python-docx`](https://github.com/python-openxml/python-docx)는 DOCX 전문 라이브러리이며 HWPX 전문 도구와는 역할이 다릅니다. **PyWPDoc의 장점은 두 문서 형식에 공통으로 사용하는 업무 흐름을 만든다는 점**입니다. 기존 도구의 모든 고급 기능을 대체한다고 주장하지 않습니다.

## 빠른 시작

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

### 복잡한 표도 실제 출력으로 확인했습니다

![병합된 표 DOCX와 HWPX 출력](https://raw.githubusercontent.com/rydolabs/PyWPDoc/main/docs/assets/readme/complex-tables-comparison.png)

*2026-10-17 Windows 네이티브 QA의 합성 자산 관리 대장 예제입니다. 화면의 `QA` 표기는 검증용으로 삽입한 문자열입니다.*

## 지원 기능과 제한

| 기능 | DOCX | HWPX |
| --- | --- | --- |
| 생성·열기·수정·저장 | 지원 | 지원 |
| 문단·표·템플릿·검색·정규식 | 검증한 범위에서 지원 | 검증한 범위에서 지원 |
| 변경 추적 | 지원 사례 있음 | 지원 사례 있음 |
| 표 행 변경 추적 | 지원 사례 있음 | 미지원, 명시적으로 거부 |
| Word와 한컴의 완전히 동일한 페이지 배치 | 보장하지 않음 | 보장하지 않음 |

`DOCX → HWPX` 완전한 무손실 변환기는 아니며, 각 형식의 고급 기능과 호환 범위는 다릅니다. [호환성 설명](https://github.com/rydolabs/PyWPDoc/blob/main/docs/COMPATIBILITY.md)과 [알려진 제약](https://github.com/rydolabs/PyWPDoc/blob/main/KNOWN_ISSUES.md)을 참고하세요.

## 테스트와 검증

2026-10-18 이전 소스의 Windows 네이티브 검증에서 업무 문서 **48/48건 열기·재저장, PDF 48/48건**을 확인했습니다. 이는 이번 폴더 개편 후보가 Windows에서 다시 통과했다는 의미는 아닙니다. [테스트 구성](https://github.com/rydolabs/PyWPDoc/blob/main/tests/README.md) · [검증 이력](https://github.com/rydolabs/PyWPDoc/blob/main/docs/testing/README.md).

```bash
python -m pip install -e ".[test,unified]"
python scripts/run_public_tests.py -q -m "not native and not performance"
```

## 문서 및 참여

[사용법](https://github.com/rydolabs/PyWPDoc/blob/main/docs/USAGE.md) · [API 전략](https://github.com/rydolabs/PyWPDoc/blob/main/docs/API_STRATEGY.md) · [변경 내역](https://github.com/rydolabs/PyWPDoc/blob/main/CHANGELOG.md) · [기여](https://github.com/rydolabs/PyWPDoc/blob/main/CONTRIBUTING.md) · [보안](https://github.com/rydolabs/PyWPDoc/blob/main/SECURITY.md)

**후보 버전: `0.44.0rc1` / 아직 GitHub Release 및 PyPI 미게시.** 라이선스: [MIT](https://github.com/rydolabs/PyWPDoc/blob/main/LICENSE).
