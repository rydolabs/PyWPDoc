# PyWPDoc v0.43.1rc2 회귀 테스트 카탈로그 (2026-10-15)

## 테스트 운영 원칙

- 제품 결함마다 **최소 1개 실패 재현 테스트**, **정상 허용 경로**, **원본 불변성 검증**을 `tests/`에 추가합니다.
- DOCX/HWPX 공통 API는 두 형식으로 파라미터화합니다. 특정 형식만 지원되면 SKIP/명시적 unsupported 오류를 검증합니다.
- 예외 발생만 검사하는 대신 원본이 보존됐는지, 저장 후 재열기·XML/ZIP이 유효한지 검사합니다.
- 회귀가 추가되면 `pytest` 전체 테스트와 Actions를 통과하기 전에는 기존 브랜치로 병합하지 않습니다.
- 테스트 오류를 무조건 삭제하거나 기대값을 완화하지 않습니다. 실패의 원인을 제품 결함/환경/잘못된 기대값으로 구분해 기록합니다.

## 발견 결함의 회귀 추적

| 문제 ID | 과거 결함 | 관련 테스트 | 현재 판정 |
|---|---|---|---|
| BUG-001 | DOCX→DOCX rebuild 내용 소실 | `test_release_safety_defects_v0431.py`, `test_contract_matrix_v0431rc2.py` | 수정 회귀 포함 |
| BUG-002 | DOCX→HWPX rebuild 모호한 예외 | 같은 파일 2개 | 미지원 명시적 거부 검증 |
| BUG-003 | HWPX→DOCX 너무 작은 exact 행 높이로 표 텍스트 숨김 | `test_release_safety_defects_v0431.py` | XML 행 높이 검사; 렌더 시각 검사는 별도 |
| BUG-004 | compare(everywhere=False) 범위 밖 표 텍스트/행 변경 무추적 반영 | `test_release_safety_defects_v0431.py` + `test_contract_matrix_v0431rc2.py` | 수정 회귀 포함 |
| BUG-005 | HWPX 원시 텍스트 수정 O(n²) | `test_release_safety_defects_v0431.py`, `test_contract_matrix_v0431rc2.py` | 대량 정확성 검사; 시간 성능 임계값은 별도 벤치마크 |
| BUG-006 | render_template 누락 키 오류 후 부분 수정 | `test_release_safety_defects_v0431.py` + `test_contract_matrix_v0431rc2.py` | 본문 및 표 내 preflight 원자성 검사 |
| BUG-007 | compare(everywhere=False) 표 테두리 무추적 변경 | `test_compare_scope_safety_v0431rc2.py` | 수정 회귀 포함 |
| BUG-008 | 표 셀 음영/병합/열 너비 변경 감지 누락 | `test_compare_scope_safety_v0431rc2.py` | 수정 회귀 포함 |
| BUG-009 | 이미지 교체/삭제/크기변경 감지 누락 | `test_compare_scope_safety_v0431rc2.py` | 수정 회귀 포함 |
| BUG-010 | 엄격 검사 추가 시 기존 이미지 글머리표·특수문단 회귀 | 기존 `test_hwpx_image_bullet_import_v0380.py`, `test_compare_paragraph_structure_v0320.py` 등 | 전체 회귀 필수 |
| INFRA-001 | 비공개 원본 없을 때 33 FileNotFoundError | `tests/conftest.py`와 `tests/_private_fixture_nodeids.txt` | 33건의 명시적 SKIP 유지 |
| INFRA-002 | Windows QA가 이전 버전 wheel 고정 | `qa_windows`, `.github/workflows/native-windows.yml` | 버전 동적 빌드/검증; 자체 러너 필요 |

## 기능별 부족한 테스트 계층 (추가 목표, 현재 완료라고 주장하지 않음)

1. 문서 OPC/리소스/관계: 매체 추가/삭제·중복 제거, 중첩/누락 관계, 손상된 ZIP/부품 검사
2. DOCX 및 HWPX 문단·run 서식: 스타일 상속, 번호/글머리표, 장문 하이퍼링크, section/header/footer
3. 표: 다양한 병합·중첩·반복·쪽 나눔, 행높이/테두리/음영/그리드
4. 변경 추적: 모든 지원 편집의 승인·거부 후 내용 동일성; 미지원 작업 fail-closed; Word/Hancom 원격/실기기 확인
5. 템플릿/정규식: 중첩 조건, 반복·누락, 잘못된 태그, 파편화된 run, 텍스트 보호 경계
6. 보존: 임의의 기존 문서 수정 후 이미지/주석/헤더/스타일/관계/커스텀 part 손실 여부
7. 대량 문서: 파일 크기/시간/메모리 경향 회귀. CPU 차이에 따라 불안정한 고정 벽시계 시간 검사는 피함
8. public-private: 공개 합성 픽스처로 점차 대체하여 비공개 33건의 외부 재현성을 확보
9. python-docx 대비 테스트: public user-visible API 비교만 선별. 소스 직접 복제 시 MIT 저작권 고지 유지

**숫자 추적:** rc2 공개 기준 639 PASS/13 제외; 이번 신규 블랙박스 35건 추가 후 674 PASS/13 제외. 일반 pytest 743 PASS/33 SKIP. 새 35건은 기존 카테고리를 강화한 것이며 기능 커버리지 완성을 의미하지 않음.
