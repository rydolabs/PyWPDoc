# PyWPDoc 업무 문서 24종 실기기 검증 (v0.43.1rc2)

- **생성 방식:** `pywpdoc.Document.new()` 등 공개 Common API로만 문서 생성, DOCX/HWPX 24종씩 총 48개
- **파일 검증:** 재열기 문단, 셀, 중첩 표, 병합, 메타데이터, 템플릿 치환, 이미지 바이트, CRC 및 XML 파싱, 원본 불변 재저장
- **별도 실기기:** Windows의 설치된 Microsoft Word/한글 2020 COM으로 열고 새 이름으로 저장한 뒤 PyWPDoc이 다시 열어 검증. 가능한 경우 각 편집기가 PDF도 출력
- **별도 육안:** PDF/화면의 글자 잘림, 행 넘침, 페이지 나눔, 이미지 크기·위치 확인은 사람이 `VISUAL_REVIEW_CHECKLIST.csv`에 기록. COM 저장 성공만으로 시각 승인으로 처리하지 않음
- **데이터:** 모든 본문·표·이미지는 합성 자료; 외부 원본 피처나 개인정보 없음

## Linux/macOS/일반 CI

```bash
python -m pip install -e '.[test,unified]'
python -m pytest -q tests/business_docs
python -m qa_business_docs.generate --out business_qa_results/generated
```

## Windows (Word·한글 설치 환경)

프로젝트의 `qa_business_docs/RUN_WINDOWS_BUSINESS_QA.bat`를 실행. `.venv-business` 생성 및 pywin32 설치 후 48개 생성·실기기 저장·검증합니다. `business_qa_results/native_windows/BUSINESS_NATIVE_QA_RESULTS.zip`을 전달하면 저장본과 로그를 검토할 수 있습니다.

`windows_review.py`는 파일마다 별도 COM 프로세스를 실행하며 1개가 실패해도 다음 문서를 계속 처리합니다. 타임아웃과 PDF 미지원은 누락시키지 않고 `windows_results.json`에 기록합니다. 일부 Office 환경에서는 HWPX→PDF가 지원되지 않을 수 있습니다.

### 현재 Linux 기준 판정

생성·재열기/구조/ZIP 테스트는 현 환경에서 실행. Windows COM·한글 렌더·사람의 육안 승인 상태는 **NOT_TESTED**입니다. Windows 실기기 결과 파일이 도착하기 전에는 시각 품질이나 릴리스 승인을 선언하지 않습니다.


## Word 표 결합 회귀 (2026-10-15)

기존 Windows QA에서는 `01_contract`, `11_purchase_order`, `23_complex_tables`, `24_long_form`의
인접 DOCX 표가 Word 재저장 후 합쳐져 표 개수가 각각 2→1, 2→1, 4→1, 13→2로 변경됐습니다.
시나리오 생성기는 서로 독립된 표 앞에 **빈 문단**을 추가합니다. `tests/business_docs/test_independent_table_separators.py`는
`word/document.xml`의 최상위 `w:tbl` 사이에 `w:p`가 존재하는지 검사하여 재발을 막습니다.
이는 시나리오 생성기 수정이며, `Document.add_table()`의 공용 동작을 임의로 변경하지 않습니다.

Windows에서 실패한 DOCX 4건만 다시 실행하려면 `qa_business_docs/RUN_WINDOWS_FAILED4.bat`를 사용하세요.
출력 ZIP에는 해당 실행의 **원본 입력 DOCX 및 manifest, 파일 SHA-256**, Word 재저장본과 PDF가 함께 포함됩니다.
실행 중 하나가 실패하더라도 나머지 케이스를 수행하며 실패는 그대로 기록합니다.
이 ZIP에서 네 시나리오의 표 개수가 유지되는지 확인하기 전에는 Windows PASS라고 보고하지 않습니다.

## 병합 격자 정규화 전용 검증

Word의 1행 전체 병합 표 정규화 문제를 대상으로 한 Common API 회귀 테스트와
16개 DOCX/HWPX 네이티브 재저장 코퍼스를 제공합니다.
- 자동 테스트: `python -m pytest -q tests/common_api/regression/test_merged_grid_roundtrip.py tests/common_api/regression/test_word_native_merge_fixtures.py`
- 합성 문서만 생성: `python -m qa_business_docs.windows_merged_grid --generate-only`
- Windows 실기기: `qa_business_docs\RUN_WINDOWS_MERGED_GRID.bat`
- 판정 및 한계: `qa_business_docs/MERGED_GRID_QA_KO.md`

한 행의 모든 열이 병합된 표의 격자 정규화만 명시적으로 허용하며, 다중 행의
병합 구조나 내용 변경은 실패로 처리합니다. 기존 Word 재저장 자료는
`tests/fixtures/word_merge_regression/`의 합성 DOCX 3쌍으로 보관합니다.
