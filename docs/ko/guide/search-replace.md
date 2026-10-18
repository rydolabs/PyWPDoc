# 검색·치환·미리보기

```python
--8<-- "examples/manual/search_replace.py"
```

- `doc.find(query)`는 텍스트 위치 정보 목록을 반환합니다.
- `doc.preview_replace(search, replacement)`는 **수정 없이** 후보를 확인하고 `count`, `matches`, `to_dict()`를 제공합니다.
- `doc.replace_text(search, replacement)`는 문서를 실제로 수정하며 치환 개수(`int`)를 반환합니다.
- `doc.find_regex(pattern)`, `doc.replace_regex(pattern, replacement)`는 정규식을 처리하지만 텍스트 필드·변경 추적 경계 등 안전하지 않은 구간은 제한합니다.

`everywhere`, `case_sensitive`, `count`는 메서드별 시그니처를 확인하세요. 미리보기의 오프셋은 화면의 좌표가 아니라 문단 논리 텍스트 기준입니다.
