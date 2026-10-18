# 이미지와 구역

공통 `add_picture()`는 PNG/JPEG/GIF/BMP 시그니처를 인식하므로 알려진 이미지에서는 `image_format`을 생략할 수 있습니다. 모르는 형식은 명시해야 하며 포맷 엔진에서 지원하지 않는 형식은 거부될 수 있습니다.

```python
--8<-- "examples/manual/pictures.py"
```

실행 예: `python examples/manual/pictures.py hwpx ./output` (`docx`도 가능).

**이미지 크기를 명시하세요.** `width=Mm(25.4), height=Mm(12.7)`을 주면 두 포맷에서 물리적 크기를 맞출 수 있습니다. 너비 생략 시 DOCX는 이미지 원본 크기를 사용하고 HWPX는 기존 기본 너비 2인치를 사용합니다. DOCX의 현재 그림 삽입 API는 인라인만 지원합니다.

```python
--8<-- "examples/manual/sections.py"
```

공통 구역 API는 `doc.add_section()`입니다. DOCX의 `start_type`과 HWPX의 `after`는 의미와 시그니처가 다르므로 공통 호출에서 받지 않습니다. 각 포맷별 전용 API가 필요합니다.
