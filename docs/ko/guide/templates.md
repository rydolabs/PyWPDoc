# 템플릿 자동화

```python
--8<-- "examples/manual/template.py"
```

1. `doc.check_template(data)`로 원본을 수정하지 않고 태그를 검사합니다.
2. 반환 객체의 `report.ok`, `missing_keys`, `issues`, `tag_count`로 치환 가능 여부를 판단합니다.
3. 문제가 없으면 `doc.render_template(data)`를 실행하고 저장합니다.

조건/반복 블록은 `sections=True`, 반복 표 행은 `table_rows=True` 설정이 필요할 수 있습니다. 이러한 템플릿은 간단한 변수 치환보다 구조 제약이 커서 실제 포맷별 문서로 검증해야 합니다. `render_template()`은 원본 문서 객체를 수정합니다.
