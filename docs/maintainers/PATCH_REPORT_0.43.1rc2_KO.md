# PyWPDoc v0.43.1rc2 — 결함 수정·통합 테스트 결과

검증일: 2026-10-15. 제품 공개 배포 미실행 / Windows Word·한글 2020 GUI 미실행.

## 수정 이유

v0.43.1rc1의 `compare(everywhere=False)`는 DOCX 표 셀 텍스트가 동일하고 표 테두리(`w:tblBorders`)만 바뀌면 변경 추적 마커 없이 새 테두리를 포함했습니다. 안전하지 않은 비교 결과이므로 수정했습니다.

## 수정 결과

- DOCX: 테이블 `tblPr`/`tblGrid`, 행 `trPr`, 셀 `tcPr` 등 서식·테두리·셀 병합·높이/폭을 비교하여 차이가 있으면 `DocumentUnsupportedError(code='compare-outside-scope-changes-unsupported')`로 차단합니다. 표 내용을 추적했다는 뜻이 아닙니다.
- DOCX: 관계별 그림 XML·객체 위치·크기·임베디드 이미지 SHA-256도 비교하여 추적 없는 변경을 차단합니다. 삭제 문단에 있는 비텍스트 인라인 요소는 기존 `compare-unsafe-inline-structure` 오류로 우선 분류합니다.
- HWPX: 표 객체의 지오메트리·셀 속성과 보이는 그림 객체 및 실제 연결된 미디어 바이트를 비교합니다. 문단 서식의 이미지 글머리표는 별도 변경 추적 경로에서 처리하도록 제외해 기존 기능을 보존했습니다.
- 안전성 검사는 `everywhere=False` 범위 밖 변경을 **거부**하는 것이며, 표 서식의 완전한 native Track Changes를 새로 구현한 것은 아닙니다. 간접 스타일 리소스 변경 등 모든 변형을 빠짐없이 검사한다고 보장할 수 없습니다.
- Windows QA: 새 버전 wheel 이름으로 동적 선택하고, 신규 16건 안전성 테스트를 네이티브/확장 QA와 독립적으로 함께 실행합니다. 자동 생성된 `.venv`만 사용합니다.
- 공개 테스트: 비공개 문서 `tests/fixtures/original_notice.hwpx`가 없는 경우 일반 `pytest`의 정확히 해당하는 33개를 SKIP 처리하며, 원본이 있으면 실제로 실행합니다.

## 실제 실행 결과

| 실행 | 결과 | 구분 |
|---|---:|---|
| `python scripts/run_public_tests.py` | **639 PASS / 13 DESELECTED / 0 FAIL** | 공개 Actions 선택자와 동일한 명령, Linux Python 3.13 |
| `python -m pytest -q` (비공개 원본 없음) | **708 PASS / 33 SKIP / 0 FAIL** | 741개 전부 수집; 비공개 자료 의존 33건 제외 |
| 비공개 원본 임시 복원 + 해당 33개 케이스만 실행 | **33/33 PASS** | 원본 즉시 제거, 공개 ZIP 비포함 |
| 기존 결함 16 + 신규 변경 추적 안전성 16 + Windows 부트스트랩 테스트 8 | **40/40 PASS** | 위 708건 내 첫 32건이 포함되므로 중복 합산 금지 |
| 신규 안전성 테스트 Windows 키트 사본 | **16/16 PASS** | Linux에서 Python으로 실행한 결과; Windows GUI 검증 아님 |
| 별도 wheel 설치와 DOCX/HWPX 생성·재열기, 표 테두리 차단 | **PASS** | 격리된 import 경로 확인 |
| wheel / sdist 빌드 | **PASS** | setuptools.build_meta 로컬 빌드 |

**중요:** 비공개 원본을 포함한 `pytest -q` 단일 741건 실행은 진행률 약 97%에서 실행 제한시간에 도달했습니다. 따라서 **741/741 단일 실행 통과라고 주장하지 않습니다.** 대신 비공개 자료 없이 실행한 708건과 비공개 자료가 필요한 나머지 33건을 서로 다른 실행에서 모두 통과한 기록을 남겼습니다. 원본 픽스처는 최종 소스 ZIP에 없습니다.

## 테스트에서 발견·수정된 문제

1. 처음 추가한 HWPX 서식 서명 검사에서 속성 자료형 오류 3건 발생 → 모델 속성 리스트 처리로 수정, 해당 16건 재통과.
2. 신규 테스트 3건은 비교 결과의 `.text`가 native 변경 추적 중간 상태를 반환해 기대값과 불일치 → 저장 문서의 revision 마커를 확인하도록 테스트 자체 수정.
3. 공개 회귀 최초 실행 4건 실패 → 이미지 글머리표 리소스를 본문 그림으로 오인하고 특수 문단 오류를 선점한 문제. 실제 그림 참조만 검사하고 삭제/삽입 문단의 특수 인라인 오류 판정을 우선하게 변경. **공개 회귀 최종 639건 통과.**
4. Windows 부트스트랩 단위 검사 2건 불일치 및 추가 안전성 파일 복사 뒤 목 설정 미비 → 스크립트와 테스트 환경을 수정, **40건 집중 검사 통과.**

## 남은 배포 승인 조건

- 한글 2020 / Microsoft Word에서 v0.43.1rc2의 native 재열기·저장·승인/거부 및 표·이미지 시각 검수. 기존 v0.43.0 실기기 통과 이력과 구분해야 합니다.
- GitHub Actions의 Ubuntu/Windows Python 3.10~3.13 실행 결과 확인. 실제 Actions 실행은 이 환경에서 하지 않았습니다.
- 필요 시 비공개 원본이 있는 Windows/Linux 러너에서 741건 단일 회귀 완주.
- 간접 스타일 리소스 변경, 매우 복잡한 오피스 문서 등 범위 확대 검증.
- 실제 GitHub push, GitHub Release, PyPI 업로드 **미수행**. MIT 공개 결정은 반영되어 있습니다.

## 핵심 파일

- `pywpdoc/features/compare/api.py` (검사 확장 및 오류 우선순위)
- `python_hwpx_next/docx/backend.py`, `docx/comparison_safety.py`
- `python_hwpx_next/hwpx/backend.py`, `hwpx/comparison_safety.py`
- `tests/test_compare_scope_safety_v0431rc2.py` (새 16개)
- `tests/conftest.py`, `_private_fixture_nodeids.txt` (공개 환경 SKIP 관리)
- `.github/workflows/native-windows.yml`, `qa_windows/bootstrap_qa.py`, `run_rc_windows.py`, `test_compare_scope_safety_v0431rc2.py`

본 문서는 이번 환경에서 수행한 테스트만 기록합니다. 배포 승인은 보류 상태입니다.
