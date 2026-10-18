> **MAINTAINER DESIGN NOTES — NOT THE PUBLIC API MANUAL.** Proposed names in this file (for example `fill`, `validate`, `merge`, `replace_image`, `accept_changes`) may not exist. For supported methods see [API Reference](reference/document.md) and [Compatibility](compatibility.md).

# HWPX / DOCX 공통 API 전략

## 목표

단순히 `HWPX용 python-docx`를 만드는 것이 아니라, 장기적으로는 **DOCX/HWPX를 동일한 개발 경험으로 다룰 수 있는 문서 자동화 API**를 만드는 것이 목표다.

초기에는:

- HWPX: 자체 native 엔진
- DOCX: `python-docx`를 backend로 활용

구조로 빠르게 시작한다.

장기적으로 우리 API 사용자가 충분히 늘어나면 `python-docx` backend를 자체 DOCX 엔진으로 점진적으로 교체할 수 있도록 설계한다.

Vite가 초기에 Rollup/esbuild를 활용하면서도 최종적으로는 **Vite의 API와 DX 자체를 사용자 진입점으로 만든 전략**과 유사하다.

---

## 핵심 전략

### 1. Backend가 아니라 API를 소유한다

사용자는 내부적으로 `python-docx`를 사용하는지 자체 HWPX/DOCX 엔진을 사용하는지 신경 쓰지 않도록 한다.

```text
User Code
    ↓
Our Common API
    ↓
Backend Layer
 ┌───────────────┐
 │ HWPX Native   │
 │ python-docx   │
 └───────────────┘
```

향후:

```text
User Code
    ↓
Our Common API
    ↓
Backend Layer
 ┌───────────────┐
 │ HWPX Native   │
 │ DOCX Native   │
 └───────────────┘
```

로 바뀌어도 사용자 코드는 최대한 유지한다.

---

## 2. python-docx의 익숙한 Object Model은 적극 활용

`python-docx`의 기본 API/mental model은 이미 오랫동안 검증되었다.

따라서 공통 API의 저수준 Object Model은 최대한 익숙하게 가져간다.

```python
doc.paragraphs
doc.tables
doc.sections

paragraph.text
paragraph.runs

table.rows
row.cells
```

목표는 기존 `python-docx` 사용자가 처음 라이브러리를 봤을 때:

> "거의 알고 있는 API인데?"

라고 느끼게 하는 것이다.

단, `python-docx`의 과거 제약이나 불편한 mutation semantics까지 그대로 복제하지 않는다.

**Conceptual compatibility를 가져가되 bug-for-bug compatibility를 목표로 하지 않는다.**

---

## 3. python-docx에서 불편했던 기능은 고수준 API로 제공

우리 라이브러리의 핵심 차별점은 Object Model 자체가 아니라 **Document Automation API**다.

예:

```python
doc.find(...)
doc.replace_text(...)
doc.replace_image(...)
doc.fill(...)
doc.validate(...)
doc.diff(...)
doc.merge(...)
doc.clone(...)

doc.accept_changes(...)
doc.reject_changes(...)
```

특히 기존 `python-docx`에서 직접 구현하기 번거로운 기능을 우선한다.

예:

- 여러 run에 걸친 문자열 검색/치환
- formatting을 보존한 text replacement
- body/table/header/footer 전체 검색
- 기존 이미지 교체
- template filling
- tracked changes 처리
- document validation
- semantic query
- diff / merge
- 안전한 대량 mutation

예:

```python
doc.replace_text(
    "{{customer}}",
    "Acme Corp",
    preserve_formatting=True,
)
```

사용자가 DOCX만 쓰더라도:

> "`python-docx`보다 이 API가 훨씬 편하니까 이 라이브러리를 쓰자"

라는 이유가 생겨야 한다.

---

## 4. HWPX/DOCX 공통 API는 공통 기능만 추상화

두 포맷을 억지로 동일하게 만들지 않는다.

공통으로 자연스러운 개념만 Common API에 둔다.

```python
doc.paragraphs
doc.tables
doc.images
doc.sections

doc.find(...)
doc.replace_text(...)
doc.fill(...)
doc.validate(...)
```

HWPX/DOCX 고유 기능은 별도의 format-specific API로 제공한다.

```python
doc.hwpx.controls
doc.hwpx.page_definitions
doc.hwpx.master_pages

doc.docx.content_controls
doc.docx.revisions
doc.docx.fields
doc.docx.custom_xml
```

원칙:

> 동일한 것은 동일하게 쓰고, 다른 것은 자연스럽게 다르게 쓴다.

Common API를 lowest common denominator로 만들지 않는다.

---

## 5. 포맷 고유 API와 backend escape hatch를 분리

안정적인 포맷별 public API:

```python
doc.hwpx...
doc.docx...
```

는 장기적으로 유지한다.

반면 현재 backend 객체에 직접 접근해야 하는 사용자를 위해 escape hatch를 제공할 수 있다.

예:

```python
doc.unwrap()
```

초기 DOCX에서는 실제 `python-docx.Document` 객체를 반환할 수 있다.

다만 이것은 장기 호환성을 강하게 보장하지 않는 backend-specific API로 명확하게 구분한다.

API 안정성은 다음 세 층으로 나눈다.

```text
1. Common API
   최고 수준의 호환성 보장

2. Format-specific API
   안정적인 public API

3. Backend escape hatch
   backend 종속 / 호환성 보장 약함
```

---

## 6. HWPX는 자체 기능을 first-class citizen으로 지원

HWPX를 DOCX 모델에 억지로 맞추지 않는다.

HWPX에만 존재하거나 HWPX에서 중요한 기능은 자체 API로 충분히 노출한다.

예:

```python
doc.hwpx.controls
doc.hwpx.fields
doc.hwpx.page_definitions
...
```

공통 API보다 HWPX 고유 기능이 필요한 사용자는 얼마든지 직접 내려가서 사용할 수 있어야 한다.

---

## 7. 사용자 adoption 경로

이상적인 사용자 이동은 다음과 같다.

```text
기존 python-docx 사용자
        ↓
우리 라이브러리 설치
        ↓
기존 backend/native API 그대로 사용
        ↓
Common Object API 사용 시작
        ↓
replace/fill/find/validate 등
고수준 API 사용
        ↓
우리 API에 익숙해짐
        ↓
향후 native DOCX backend로 교체되어도
사용자 코드는 거의 유지
```

처음부터 `python-docx`를 대체하라고 요구하지 않는다.

대신:

> 기존 방식도 그대로 쓸 수 있는데 HWPX도 지원되고, 어려운 작업은 더 쉽게 할 수 있다.

라는 가치로 진입한다.

---

## 8. 장기적으로 가장 중요한 자산

장기적인 moat는 HWPX parser나 `python-docx` wrapper 자체가 아니다.

**우리 API contract와 개발자 경험(DX)** 이 핵심 자산이다.

사용자의 코드가:

```python
doc = Document.open(path)

doc.replace_text(...)
doc.fill(...)
doc.validate(...)
doc.save(...)
```

처럼 포맷/backend에 독립적으로 작성되도록 만든다.

장기적으로는:

```text
HWPX
DOCX
ODT
...
```

같은 추가 포맷도 같은 API 아래 확장할 수 있다.

최종적인 제품 방향은:

> **Familiar Document Object Model  
> + High-level Automation API  
> + Format-specific Native API  
> + Replaceable Backend Architecture**

이다.

---

## 설계 원칙 요약

1. `python-docx`의 익숙한 Object Model은 최대한 활용한다.
2. `python-docx`의 불편한 부분까지 복제하지 않는다.
3. 실제 자동화 작업을 고수준 API로 제공한다.
4. HWPX/DOCX 고유 기능은 각각 온전히 노출한다.
5. 공통 API는 최소공통분모가 아니라 "공통으로 의미 있는 개념"만 포함한다.
6. backend는 교체 가능해야 한다.
7. 사용자가 backend가 아니라 우리 API에 의존하게 만든다.
8. native DOCX 구현은 사용량과 실제 pain point가 확인된 뒤 점진적으로 진행한다.
9. backend-independent conformance test suite를 일찍 구축한다.
10. 궁극적으로는 HWPX 라이브러리가 아니라 **문서 자동화 플랫폼/API**를 지향한다.

## 한 문장으로

> **python-docx처럼 배우기 쉽고, 기존 방식도 그대로 사용할 수 있으면서, HWPX까지 지원하고, python-docx에서 어렵던 작업은 훨씬 쉬운 고수준 API로 제공하는 문서 자동화 레이어를 만든다.**
