# 설치와 빠른 시작

정식 PyPI 최초 배포 **이후**:

```bash
python -m pip install "pywpdoc[unified]"
```

현재는 검토본 소스 폴더에서:

```bash
python -m pip install -e ".[unified]"
```

- Python 3.10 이상 필요.
- HWPX만 사용한다면 `pywpdoc` 기본 설치로 충분하며, DOCX에는 `python-docx`가 필요합니다.
- Word나 한컴오피스는 일반 문서 생성·편집에 필요하지 않지만, 각각의 프로그램에서 열기·PDF 출력 검증을 할 때는 필요합니다.

[전체 실행 예제: `examples/manual/quickstart.py`](https://github.com/rydolabs/PyWPDoc/blob/main/examples/manual/quickstart.py)

```python
--8<-- "examples/manual/quickstart.py"
```

실행: `python examples/manual/quickstart.py ./output` → `quickstart.docx`, `quickstart.hwpx` 생성.
