# PyWPDoc Common API 테스트 계층 설계 (2026-10-15)

**현재 대상:** PyWPDoc 0.43.1rc2, 개발 전용 `nssang00/chatgpt-write-test`의 `projects/pywpdoc/`에서 실행. `rydolabs/PyWPDoc`와 PyPI는 아직 변경하지 않음.

## 참고: python-docx 공개 테스트

공식 `python-openxml/python-docx`의 `master`에서 파일 및 실제 테스트 코드를 확인했다. `tests/**/*.py` 87개(초기화 파일 포함), `features/**/*.feature` 67개를 확인했다. 특히 `tests/test_document.py`(22개 `it_` 함수), `test_table.py`(51), `text/test_paragraph.py`(16), `text/test_run.py`(18), `test_section.py`(38), `opc/test_package.py`(15), `image/test_image.py`(20)를 참고했다. 이 수치는 각 파일에 정의된 테스트 함수 이름을 센 것이며, 실제 pytest 파라미터 전개 수 또는 모든 upstream 테스트의 총계는 아니다.

`python-docx`는 **model API + OOXML package internals + behavior (`features/`)**을 분리한다. PyWPDoc은 DOCX와 HWPX가 있으므로 하나의 API 검증을 두 형식에 반복하고 내부 네이티브 검증을 분리해야 한다.

## 제안 계층과 Oracle

| 계층 | 기준 | 주기/필수 | 샘플 시나리오 |
|---|---|---|---|
| L0 배포·설치 | clean wheel, sdist, Python 3.10–3.13 | PR 필수 | 설치/import, 두 확장자 생성/재열기, 라이선스 메타데이터 |
| L1 Common API 단위 | `Document.new/open`, 문단/Run, 표, 메타데이터 | PR 필수 | Empty, Unicode, bold/italic, nested table, merge |
| L2 공통 통합·파일 | DOCX/HWPX 저장 재열기·변경 후 재저장 | PR 필수 | ZIP CRC, XML parse, 레이아웃 포함 데이터 보존 |
| L3 `python-docx` 관찰 동등성 | 공개 기능 교집합의 결과 비교 | PR 필수 | add_paragraph/run/table, add_row, metadata; 지원 차이 명시 |
| L4 독립 검수 결함 회귀 | 과거 실패 입력과 기대 실패 코드 | PR 필수 | rebuild 소실, compare 추적 누락, 템플릿 원자성, 표 높이 |
| L5 입력 검증/안전 | 형식 오류·malformed·부분 변경 방지 | PR 필수 | regex zero-width, 잘못된 캡처, ZIP corruption |
| L6 파일 형식별 내부 | HWPX XML, DOCX OPC, 리소스 링크·파트 보존 | PR 필수/표본 확대 | revision XML, relationships, styles, images |
| L7 Windows 네이티브 | Word/Hancom COM | 별도 self-hosted / 출시 게이트 | 변경 추적 Accept/Reject, 수정 후 저장 |
| L8 시각·성능 | 실제 렌더, 다회 측정, 대용량 QA | 정기/출시 게이트 | 페이지 분리·이미지·표 표시·복잡도 추세 |

## 기존 독립 검수 사고와 테스트 매핑

| 결함 | 기존 회귀 | 이번 Common API 추가 |
|---|---|---|
| DOCX `rebuild()` 본문·표 데이터 유실 | `test_release_safety_defects_v0431.py` | `regression/test_historical_defect_contract.py` |
| DOCX→HWPX 지원되지 않는 변환 | 위 파일 | 동일 신규 파일 |
| `compare(everywhere=False)` 표 내용·행 무추적 | 위 파일 | 동일 신규 파일 및 `integration` 정상 사용 |
| 테두리·셀 속성·이미지 무추적 반영 | `test_compare_scope_safety_v0431rc2.py` | `regression` 테두리 2종 |
| 템플릿 누락 키 이후 부분 수정 | `test_release_safety_defects_v0431.py` | `integration`, `regression`, `negative` |
| HWPX→DOCX 작은 행 높이로 셀 숨김 | `test_release_safety_defects_v0431.py` | `regression` XML 행 높이 검사 (실제 시각은 별도) |
| HWPX 대량 치환 비효율 | `test_release_safety_defects_v0431.py` | `regression` 500문단 동작 검증 (속도 임계치는 별도) |
| 정규식 오류에서 원본 보존 | 기존 regex 테스트 | `integration`, `negative` |

**중요:** 테스트 수가 많다고 `python-docx`와 동등한 지원 범위를 의미하지 않는다. 미지원되는 DOCX→HWPX 전체 변환, HWPX의 네이티브 표 구조 변경 추적, 형식별 일부 API 차이를 문서에 계속 명시한다.

## 기능별 다음 확대 계획 (원본 없이 합성 테스트로 구축)

1. **패키지 관계 검증:** DOCX relationship 참조 무결성, HWPX manifest·미디어·이미지 다중 삽입, 손상 ZIP 탐지.
2. **서식 및 레이아웃:** 스타일 상속·타입, 섹션/머리글/바닥글, 페이지 번호, 문단 간격, 복합 표 폭·병합.
3. **리비전:** 삽입/삭제/형식 변화의 승인/거부 결과 전체 비교; 표·이미지·병합은 지원 불가 시 예외 확인.
4. **정규식·템플릿:** Unicode·중첩 태그·표 행 반복·조건 분기·count=0·한글/영문 혼합 문단.
5. **복구/안전/보안:** malformed XML, 중복 ZIP 경로, 비정상 메타데이터, 고의적 템플릿 오입력.
6. **BDD 사용자 시나리오:** 계약서 변경 추적, 표준 공문 일괄 편집, 템플릿 100건 생성, 실제 한컴/Word 시각 샘플.
7. **분기 커버리지:** 위험도가 높은 `compare`, `replace`, `template`, `snapshot`, `OPC/HWPX import`부터 측정하고 커버리지 기준을 단계적으로 강화.

## 브랜치 및 Actions 규칙

- 개발 저장소: `nssang00/chatgpt-write-test`, 작업 브랜치 `pywpdoc/rc2-regression-staging` 및 PR용 하위 feature branch.
- 디렉터리: `projects/pywpdoc/tests/`(이름 변경·배포 시에는 최종 저장소의 루트 `tests/`로 동일 구조 이동).
- **코드 변경 PR마다 해당 버그의 실패 입력으로 새 테스트를 먼저 추가**, 전체 suite를 로컬에서 실행. 실패하면 push 스크립트 중단. 성공해도 원격 Actions를 기다려야 하고 모든 필수 job이 성공해야 병합.
- GitHub Actions는 push **뒤에** 실행된다. 실질적인 강제력은 required status checks, PR required 및 branch protection/ruleset이다.
- 원격 Actions 최소 검증: Linux/Windows × Python 3.10~3.13, 공개 pytest, 변환·패키지 무결성, 수동 native test(전용 러너), wheel/sdist smoke.
- 비공개 `original_notice.hwpx`는 공유/업로드하지 않고 관련 33건은 공개 환경에서 SKIP; 내부 실행 결과는 별도 기록.
- PyPI 게시 워크플로는 개발 저장소에 등록하지 않는다.

## 인수 기준

- 새로운 변경으로 인한 **실패 0**, 공개 원본 제외 건은 식별된 skip만 허용.
- 모든 신규 Common API 계약은 가능한 경우 DOCX/HWPX 두 형식의 저장·재열기까지 검증.
- 새 결함 발생 시 **회귀 ID 및 재현용 합성 데이터**를 추가하고 테스트를 먼저 실패시킨 뒤 구현을 수정.
- 릴리스 후보는 GitHub Actions 결과와 Windows 한글/Word 실기기 승인/거부, 실제 문서 시각 검수를 별도 승인.

## 2026-10-15 Word 병합 격자 정규화 추가 검증

- 테스트 계층: `tests/common_api/regression/test_merged_grid_roundtrip.py`, `test_word_native_merge_fixtures.py`
- 신규 수집 항목: 78건, Linux Common API 테스트 78 PASS
- 고정 독립 네이티브 증거: 3개 합성 DOCX의 Word 재저장 전/후 각 1쌍
- 동적 COM 코퍼스: 병합 7유형 + 병합하지 않은 대조군 1유형 × DOCX/HWPX = 16개
- 통합 regression 그룹 실행: 1,228 PASS / 33 SKIP / 0 FAIL. 비공개 원본이 필요한 SKIP 33개를 통과로 취급하지 않음
- Word·한글 신규 16개 실기기 재저장은 Windows COM 환경에서 별도로 검증해야 하며, PDF 출력 성공만으로 육안 합격으로 선언하지 않음
