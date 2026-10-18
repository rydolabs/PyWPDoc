# PyWPDoc 0.43.1rc1 수정사항과 재검증

2026-10-15 · 배포 후보, 아직 PyPI/GitHub Release 게시하지 않음

## 수정 경위

두 개의 독립 검수 보고서에서 확인된 결함을 기준으로 기존 0.43.0 구현을 수정했습니다. 제품 구현 변경 5개 파일, 신규 테스트 16개입니다.

## 수정 내용

1. DOCX → DOCX `rebuild`: `docx_package` native payload를 열어 데이터 손실을 막음.
2. DOCX → HWPX 재구축: 포터블 변환 미구현을 명시적 `DocumentUnsupportedError(rebuild-docx-to-hwpx-unsupported)`로 차단.
3. `compare(everywhere=False)`: 미비교 영역의 내용·run 서식·표 기본 구조가 달라지면 `compare-outside-scope-changes-unsupported`로 실패. 원본/신본 모두 보존.
4. `render_template(..., missing="error")`: 전체 문서 preflight 후 렌더링 시작. 누락 값으로 인한 앞 문단 부분 변경 방지.
5. HWPX Run.text: 이미 연결된 부모 문단을 캐시해 매 변경마다 문서 전체를 재탐색하지 않음.
6. HWPX → DOCX: 아직 계산되지 않은 작은 표 높이를 Word의 `EXACTLY` 행 높이로 강제하지 않도록 수정. 실제 LibreOffice PDF에서 표시되지 않던 셀 문구 복원 확인.

## 검증

- 기존 709건 + 신규 16건 = 725/725 PASS (격리한 Linux 테스트 환경)
- HWPX 250/500/1000/2000문단 치환 벤치마크에서 O(n²) 문제가 제거됨 (환경 종속 수치)
- 한글·Word 실기기 테스트와 복잡한 HWPX → DOCX 변환 시각 품질은 아직 검증되지 않음
- GitHub/PyPI 외부 배포는 아직 수행하지 않음

## 배포 판정

**배포 승인 보류** — 수정된 제품 구현에 대한 Windows Word·한글 네이티브 회귀 및 사용 예제 검수가 필요합니다.
