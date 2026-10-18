# 한글 2020 배치 검증 안내

1. `01_BATCH_BASE.hwpx`를 한글 2020에서 엽니다.
2. **변경 내용 추적을 켠 다음**, 아래 표를 **각각 독립적으로** 편집합니다.
3. 문제가 발생한 표는 그대로 두고 **다음 표**로 넘어갑니다. 첫 칸의 T01/S06 식별자는 건드리지 않습니다.
4. 변경 내용을 승인하거나 거부하지 말고 `02_BATCH_TRACKED.hwpx`라는 이름으로 **HWPX 저장**합니다.
5. `02_BATCH_TRACKED.hwpx` **한 파일만 업로드**하면 나머지는 제가 일괄 분석합니다.
6. 선택 사항: 같은 파일에서 '모두 승인'/'모두 거부'를 각각 복사 저장하면 후속 GUI 판정을 추가할 수 있습니다.

## 실험 10개

| ID | 표에서 수행할 작업 |
|---|---|
| T01_INSERT | 본문 2행 오른쪽 셀 ABC 끝에 D 추가 (ABCD) |
| T02_DELETE | 본문 2행 오른쪽 셀 ABCD에서 마지막 D만 삭제 (ABC) |
| T03_REPLACE | 본문 2행 오른쪽 셀 OLD를 NEW로 교체 |
| T04_CHAR | 본문 2행 오른쪽 셀 BOLDME 전체를 굵게(Ctrl+B) |
| T05_PARA | 본문 2행 오른쪽 셀 ALIGNME 문단 가운데 정렬 |
| S06_ROW_INSERT | A/1 행과 B/2 행 사이에 1행 삽입, 새 행에 X/9 입력 |
| S07_ROW_DELETE | B/2 전체 행만 삭제 (표제 행은 유지) |
| S08_COL_INSERT | 표 맨 오른쪽에 1열 삽입 (기존 첫 열은 유지) |
| S09_COL_DELETE | 마지막(세 번째) 열 전체 삭제 (첫 열 표제 유지) |
| S10_CELL_MERGE | 표 2행(본문 첫 행)의 오른쪽 두 셀 LEFT와 RIGHT를 병합 |

## 판정의 한계

HWPX 파일에서 변경 이력이 탐지돼도 **한글 GUI의 승인/거부 의미까지 자동으로 검증되지는 않습니다.**
행/열 삽입·삭제 및 병합은 실제 구조 변경과 revision 앵커를 별도로 검사하며, 구조 변화만으로 변경 추적이 지원된다고 판정하지 않습니다.
텍스트 변경은 구체적인 마커/메타데이터를 판정하고, 서식 변경은 해당 표의 paraTcId/charTcId 앵커를 확인합니다.

## 독립 실행 로그

`python -m quality.native_batch_suite run --suite native_batch_suite --tracked 02_BATCH_TRACKED.hwpx --out qa_results`
명령을 실행하면 JSON, CSV, Markdown, issues.log를 생성합니다. HWPX가 아직 없으면 모든 항목을 SKIP으로 보고합니다.
