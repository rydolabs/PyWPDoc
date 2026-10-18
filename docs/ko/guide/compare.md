# 변경 추적과 문서 비교

```python
--8<-- "examples/manual/compare.py"
```

`old.compare(new, author="PyWPDoc")`는 처리 가능한 **변경 추적을 포함한 새 문서 객체**를 반환합니다. 원본은 수정하지 않습니다. 기본적인 텍스트 변경은 두 포맷에서 지원되지만, 문단 삽입·삭제, 표 이동, 구조 차이가 큰 변경 등은 `DocumentUnsupportedError`로 거부될 수 있습니다.

**중요:** 범용 문서 diff/merge 엔진이나 모든 유형의 변경 추적을 의미하지 않습니다. 실제 Word/한컴에서의 표시는 별도 네이티브 QA로 검증해야 합니다.
