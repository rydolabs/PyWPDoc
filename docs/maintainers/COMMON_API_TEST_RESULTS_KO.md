# PyWPDoc 0.43.1rc2 Common API 계층 테스트 실행 기록

작성일: 2026-10-15. Linux / Python 3.13.5. pytest를 소스 폴더에서 실행. Microsoft Word/Hancom GUI는 이번 계층 테스트에 포함되지 않음.

## 신규 Common API tests

- 경로: `tests/common_api/`
- 공통 DOCX/HWPX fixture: `tests/common_api/conftest.py`
- 범주: 문서·문단·Run·표 / 검색·치환·템플릿·정규식 / ZIP·XML 저장 재열기 / python-docx 공개 API 관찰 동등성 / 독립 검수 결함 재발 방지 / 잘못된 입력
- 명령: `python -m pytest -q tests/common_api --strict-markers`
- 실제 결과: **240 passed**, 0 failed. 경고는 외부 라이브러리/기존 API 관련이며 이 결과에 실패로 집계하지 않음.

## 기존 테스트까지 합친 전체 실행 및 분할 검증

- 전체 수집: **1,016 항목** (새 240 + 이전 776). `TEST_CASE_CATALOG.csv` 참조.
- 원본 의존 33개는 `tests/fixtures/original_notice.hwpx`가 없으면 명시적 SKIP.
- 실행 A: `python -m pytest -q --strict-markers --ignore=tests/test_roundtrip.py` → **925 passed, 20 skipped, 0 failed**.
- 실행 B: `python -m pytest -vv tests/test_roundtrip.py --strict-markers` → **58 passed, 13 skipped, 0 failed**.
- 이 두 실행의 수집 집합은 겹치지 않음. 분할 합계: **983 passed, 33 skipped, 0 failed**.
- **단일 전체 재시도 완료:** `python -m pytest -q --strict-markers --junitxml=.test-results/final-full.xml` → **983 passed, 33 skipped, 0 failed, 36.51초**. 앞선 단일 시도는 제한시간으로 완료되지 않았지만 재시도는 정상 종료함.

## 해석과 한계

- 이 240개 항목은 파라미터를 전개한 수이며 **240개의 서로 다른 독립 구현 기능**을 의미하지 않음.
- python-docx 원본 tests 복제 또는 upstream 완전 호환성 인증이 아님. 공통 API로 노출되는 지원 기능 교집합을 검증함.
- 새 테스트는 GUI/COM 변형, 구조적으로 복잡한 실문서 포맷, 시각 배치, 독점 원본 문서의 비공개 회귀를 대체하지 못함.
- Windows 및 Python 3.10~3.12의 실제 GitHub Actions는 **아직 실행되지 않음**.
- 테스트 성능 측정은 해당 코드를 실행한 환경에서의 측정만 대표. CI에서 시간 기준을 설정하기 전에 반복 샘플 필요.

## 저장소 반영 상태

- `nssang00/chatgpt-write-test`: 전용 브랜치 `pywpdoc/rc2-regression-staging`은 있으나 이번 테스트 소스는 로컬 staging overlay 상태.
- `rydolabs/PyWPDoc`: 변경하지 않음.
- PyPI: 게시·연결·Release 생성 없음.

## 공개 선택 테스트 재검증

- `python scripts/run_public_tests.py` → **914 passed, 13 deselected, 0 failed (32.29초)**.
