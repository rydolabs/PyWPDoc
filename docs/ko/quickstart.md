# 설치와 빠른 시작

**`0.44.0`부터는 한 번의 설치로 Word DOCX와 한컴 HWPX 둘 다 사용할 수 있습니다.**

```bash
pip install pywpdoc
```

기존 PyPI 시험 버전 `0.44.0rc1`에서 DOCX를 사용하려면 `pip install "pywpdoc[unified]==0.44.0rc1"`을 실행합니다. `0.44.0` 새 버전의 실제 게시 여부는 [PyPI](https://pypi.org/project/pywpdoc/)에서 확인하세요.

```python
from pywpdoc import Document

doc = Document.new("docx")
doc.add_paragraph("Hello, PyWPDoc!")
doc.save("hello.docx")
```

- Python 3.10 이상이 필요합니다.
- 기본 의존성에 `python-docx`가 포함되며 기존 `[unified]` 설치 옵션도 계속 허용합니다.
- Word·한컴 데스크톱 프로그램이 없어도 일반 문서 생성·편집이 가능합니다. 해당 프로그램에서 실제 PDF/레이아웃 검증 시에는 설치가 필요합니다.

[전체 실행 예제: `examples/manual/quickstart.py`](https://github.com/rydolabs/PyWPDoc/blob/main/examples/manual/quickstart.py)

```python
--8<-- "examples/manual/quickstart.py"
```

`python examples/manual/quickstart.py ./output`으로 `quickstart.docx`와 `quickstart.hwpx`를 생성할 수 있습니다.

[전체 공통 API](../reference/document.md) · [템플릿 처리](guide/templates.md) · [변경 추적](guide/compare.md)
