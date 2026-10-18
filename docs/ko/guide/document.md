# 문서 생성과 편집

`pywpdoc.Document`는 DOCX와 HWPX를 공통 진입점으로 제공합니다.

```python
from pywpdoc import Document

doc = Document.new("docx")
doc.add_paragraph("보고서")
table = doc.add_table(2, 2)
table.cell(0, 0).text = "품목"
table.cell(1, 0).text = "노트북"
doc.save("report.docx")

reopened = Document.open("report.docx")
print(reopened.tables[0].cell(1, 0).text)
```

DOCX/HWPX 모두 `Document.new("포맷")`, `Document.open(path)`, `doc.save(path)`를 사용합니다. `open()`은 확장자를 확인하며, `save()`로 다른 포맷으로 자동 변환하지는 않습니다. 데이터의 배치와 줄바꿈은 Word/한컴에서 차이가 있을 수 있습니다.

[공통 API 레퍼런스](../reference.md) · [완전한 예제](../../getting-started/quickstart.md)
