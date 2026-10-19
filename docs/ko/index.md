# PyWPDoc — 문서 자동화와 변경 추적

**Word DOCX의 템플릿 태그를 미리 검사하고, 치환 대상을 확인하고, 지원되는 변경 내용을 추적 가능한 문서로 저장합니다.** 동일한 공통 API는 한컴 HWPX에서도 사용할 수 있습니다.

## 간단한 설치와 사용법

`0.44.0`부터:

```bash
pip install pywpdoc
```

이미 PyPI에 게시된 이전 `0.44.0rc1` 시험 버전은 DOCX 처리를 위해 `pip install "pywpdoc[unified]==0.44.0rc1"`을 사용해야 합니다. 안정 버전 `0.44.0`의 실제 게시에는 별도 승인 절차가 있습니다.

```python
from pywpdoc import Document

doc = Document.new("docx")
doc.add_paragraph("Customer: {{customer.name}}")
data = {"customer": {"name": "Acme Corp"}}
report = doc.check_template(data)
if not report.ok:
    raise ValueError(report.missing_keys)
doc.render_template(data)
doc.save("contract.docx")
```

[템플릿 API](guide/templates.md) · [변경 추적 API](guide/compare.md) · [검색·치환 미리보기](guide/search-replace.md)

## 실제 문서 출력 이미지

![기존 Windows Word DOCX 계약서 출력 이미지](../assets/readme/contract-word.png)

![기존 Windows Word DOCX 복잡한 표 출력 이미지](../assets/readme/complex-tables-docx.png)

![기존 Word DOCX 및 한컴 HWPX 출력 비교](../assets/readme/docx-hwpx-contract-comparison.png)

*이 이미지는 기존 Word·한컴의 PDF 페이지 출력 기록으로, 신규 `0.44.0` 테스트나 Track Changes 화면은 아닙니다. [이미지 출처](../assets/readme/PROVENANCE.md) · [과거 RC 실기 QA](../testing/native-qa-0440rc1-2026-10-18.md).*

## API 문서 바로가기

[전체 공통 `Document` API](../reference/document.md) · [템플릿](guide/templates.md) · [변경 추적](guide/compare.md) · [검색·치환](guide/search-replace.md) · [결과·예외](errors.md) · [설치](quickstart.md) · [AI 에이전트 가이드](agent-guide.md)

`save()`는 형식 변환이 아니며, 레거시 바이너리 `.hwp`는 지원하지 않습니다. 모든 구조적 변경의 추적과 Word·한컴의 완전 동일한 페이지 배치도 보장하지 않습니다. [제한 사항](limitations.md)
