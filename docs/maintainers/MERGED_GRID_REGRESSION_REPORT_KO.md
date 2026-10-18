# PyWPDoc v0.43.1rc2 — Word 병합 격자 정규화 회귀 검증 (2026-10-15)

## 결론

**Common API/자동 Python 검증 PASS; 신규 Windows COM 병합 코퍼스 검증 대기.**
PyWPDoc 제품 모듈은 수정하지 않고 테스트 및 네이티브 QA 모듈만 추가했습니다.
개발용 원격 GitHub와 최종 배포 저장소에는 새 파일을 push하지 않았습니다.

## 사건 개요

이전 업무 문서 Windows 결과 `BUSINESS_NATIVE_QA_RESULTS(1).zip`에서
`01_contract`, `11_purchase_order`, `23_complex_tables`의 단일 행 전체 병합 표가
Word 재저장 시 2열 격자와 `gridSpan=2`에서 1열/1셀로 정규화되었습니다.
문서 표 개수와 텍스트는 보존됐으며, 이 예외를 허용하되 병합 영역이 손상되는
경우까지 PASS 처리해서는 안 됩니다.

## 이번 추가 케이스

- 병합 7유형(1행 전체 병합, 부분 가로, 3열 가로, 2행 세로, 3행 세로, 2×2·2×3 복합)과 비병합 대조군 1유형
- DOCX 및 HWPX 문서 생성→재열기→재편집, OOXML `gridSpan`·`vMerge`와 테이블 셀 보존
- 병합 셀 세로 정렬 및 Table Grid 스타일 저장 검사
- 조용한 텍스트 변경, 세로 병합 마커 삭제를 오류로 잡아내는 음성 테스트
- 실제 Word COM 전후 합성 DOCX 3쌍의 SHA-256 검증 및 1행 전체 병합 예외 인정
- 새 Windows 원클릭: 위 8종 × 2형식 = 16개를 Word/Hancom에서 실제 재저장해 전후 비교; 파일별 타임아웃과 결과 보존

## 재검증 수치

| 구분 | 결과 | 판정 |
|---|---:|---|
| 신규 병합 격자 pytest | 78 PASS / 0 FAIL | PASS |
| 신규 합성 문서 생성 (8×2) | 16 PASS / 0 FAIL | PASS |
| 기존 전체 + 신규 통합 (4그룹 분할 실행) | 1,228 PASS / 33 SKIP / 0 FAIL | PASS (분할) |
| 전체 수집 가능한 pytest 항목 | 1,261 | 수집 가능 |
| Windows Word/Hancom 신규 16건 COM | 0건 실행 | NOT_TESTED |
| 사람의 시각적 승인 | 미실시 | NOT_TESTED |

33 SKIP은 비공개 원본 HWPX fixture 기반 테스트이며 PASS로 계산하지 않았습니다.
4그룹 실행은 독립 프로세스로 끝까지 수행하였고 모든 그룹이 정상 종료했습니다.
완전 단일 pytest 실행 1,261건은 **이번 변경분에 대해 별도로 수행하지 않았습니다**.

## 기존 COM 합성 예제 재현

- `01_contract`: 단일 행 전체 병합 표의 2열→1열 정규화, 본문 보존
- `11_purchase_order`: 같은 정규화, 본문 보존
- `23_complex_tables`: 같은 정규화, 다른 일반 표는 유지
- 실측 이전 Windows 결과의 입력 DOCX/Word 저장 DOCX 쌍은
  `tests/fixtures/word_merge_regression/`에 보관하고 원본 SHA-256으로 검사
- **허용하지 않음:** 다중 행 가로/세로 병합 해제, 다른 표 수로 결합, 텍스트 유실, 셀 수 손상

## 파일 구조

- `qa_business_docs/merge_grid.py`: 순수 Common API 문서 생성 및 Word OOXML 의미 비교
- `tests/common_api/regression/test_merged_grid_roundtrip.py`: 직접 생성·왕복·음성 검사
- `tests/common_api/regression/test_word_native_merge_fixtures.py`: 이전 실제 Word 저장본 3쌍 검사
- `tests/fixtures/word_merge_regression/`: 재배포 가능한 합성 원본/저장본+체크섬
- `qa_business_docs/windows_merged_grid.py`: Windows QA 감독자
- `qa_business_docs/windows_merged_grid_worker.py`: 개별 Word/Hancom COM 워커
- `qa_business_docs/RUN_WINDOWS_MERGED_GRID.bat`: 원클릭 `.venv`·pytest·16건 실행
- `.github/workflows/pywpdoc-regression.yml`: 기존 push/PR 회귀에 새 전용 게이트 추가
- `.github/workflows/pywpdoc-merged-grid-native-windows.yml`: 별도 수동 네이티브 QA (배포 없음)

## 차기 검증

Windows Word와 한글 2020 설치 환경에서 `qa_business_docs\RUN_WINDOWS_MERGED_GRID.bat`를
실행한 뒤 생성되는 `merge_grid_native_results\MERGE_GRID_NATIVE_QA_RESULTS.zip`을
제공받아 실제 결과를 추가 검수해야 합니다. 원본·저장본·PDF·SHA-256과
케이스별 PASS/FAIL이 ZIP에 포함됩니다.

## 배포 상태

정식 `rydolabs/PyWPDoc`, PyPI, GitHub Release는 변경하지 않았습니다.
`nssang00/chatgpt-write-test`의 원격 staging 브랜치에도 이번 변경은 아직 push하지 않았습니다.
