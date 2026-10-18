# Create, open, edit and save

```python
from pywpdoc import Document

doc = Document.new("docx")  # or "hwpx"
p = doc.add_paragraph("First paragraph")
table = doc.add_table(1, 2)
table.cell(0, 0).text = "Key"
table.cell(0, 1).text = "Value"
doc.save("sample.docx")

reopened = Document.open("sample.docx")
print(reopened.paragraphs[0].text)
```

The extension in `Document.open(path)` chooses a backend; only `.docx` and `.hwpx` are supported. Calling `save()` does **not** convert to another format. Word/Hancom may render the same document differently.

See [Quickstart](../getting-started/quickstart.md) for the tested `.py` example and [Document reference](../reference/document.md) for argument contracts.
