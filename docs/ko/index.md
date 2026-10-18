# PyWPDoc 한국어 API 매뉴얼

**Python 코드 하나로 DOCX와 HWPX 파일 생성·편집.**

![Microsoft Word와 한컴오피스의 실제 업무 문서 비교](../assets/readme/docx-hwpx-contract-comparison.png)

*2026-10-18 Windows 네이티브 QA 문서 기반. 두 제품의 렌더링을 픽셀 수준으로 동일하게 보장하지 않습니다. 새로 구성한 0.44.0rc1의 Windows 재검증은 아직 필요합니다.*

```python
from pywpdoc import Document
for fmt in ("docx", "hwpx"):
    doc = Document.new(fmt)
    doc.add_paragraph("안녕하세요, PyWPDoc!")
    doc.save(f"hello.{fmt}")
```

[설치·빠른 시작](quickstart.md) · [공통 API](api.md) · [제한 사항](limitations.md) · [한국어 API 레퍼런스](reference.md) · [기능별 사용법](guide/document.md) · [전체 영어 API Reference](../reference/document.md)

> 현재 문서 대상 버전은 **0.44.0rc1 검토 후보**이며, GitHub Pages와 PyPI는 아직 공개하지 않았습니다.
