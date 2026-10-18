# 표와 셀

두 포맷 모두 `doc.add_table(rows, cols, style=None)`로 표를 만들고 `table.cell(row, col).text`로 값을 설정합니다.

```python
from pywpdoc import Document

doc = Document.new("hwpx")
t = doc.add_table(2, 2)
t.cell(0, 0).text = "품목"
t.cell(0, 1).text = "수량"
t.cell(1, 0).text = "노트북"
t.cell(1, 1).text = "12"
doc.save("order.hwpx")
```

병합된 셀, 중첩 표, 테두리 및 열 폭은 공통 메서드와 별개로 포맷별 고급 API와 렌더 검증이 필요할 수 있습니다.

![DOCX/HWPX 복잡 표](../../assets/readme/complex-tables-comparison.png)

*과거 Word/한컴 네이티브 QA 이미지. 픽셀 단위 일치를 뜻하지 않습니다.*
