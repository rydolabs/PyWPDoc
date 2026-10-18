# Common API 업무 문서 24종 생성·실기기 검증 계획

PyWPDoc v0.43.1rc2 / 2026-10-15. **배포하지 않음.** 시험용 데이터는 모두 합성 자료.

## 목적

1. 동일한 사용자 시나리오 24개를 DOCX와 HWPX 각각에서 생성하고, 저장·재열기·편집·재저장·메타데이터·이미지·병합·중첩 표를 검증한다.
2. 네이티브 편집기(Word / 한글 2020)의 별도 저장본에서 같은 구조가 보존되는지 확인한다.
3. 렌더링의 텍스트 누락 및 페이지 범위 검사와, 육안 품질 확인을 **분리**한다.
4. 모든 PR/push에서 공용 테스트가 실패하면 병합을 차단한다. 실제 Word/Hancom은 자체 Windows 러너에서만 수행한다.

## 계층

| 단계 | 검사 | 실행 | 완료 판정 |
|---|---|---|---|
| B1 | 24종 × DOCX/HWPX 생성·저장·재열기 | CI 자동 | 48개 파일 내용·표 보존 |
| B2 | ZIP CRC, XML, PNG 바이트·패키지 관계 표본 | CI 자동 | 손상 없음 |
| B3 | 재열기 후 추가 편집·저장, 원본 불변성 | CI 자동 | 내용·구조 보존 |
| B4 | LibreOffice DOCX PDF 렌더 | Linux QA | 제목·끝 마커·경계·빈 페이지 검사. **Word 자체가 아님** |
| B5 | Word/Hancom COM 실제 열기·재저장 | 자체 Windows | 문서별 PASS/FAIL·아카이브 |
| B6 | Word/Hancom PDF 출력·시각 검수 | 자체 Windows/수동 | 페이지나눔·이미지·표 잘림·폰트 직접 확인 후 서명 |

## 테스트 명령

```bash
python -m pytest -q tests/business_docs
python -m qa_business_docs.generate --out business_qa_results/generated
python scripts/run_ci_regression_groups.py
```

Windows: `qa_business_docs/RUN_WINDOWS_BUSINESS_QA.bat` 사용. 실패가 나도 후속 문서를 계속 검증하고 JSON/CSV에 오류를 기록한다. 결과 ZIP은 `business_qa_results/native_windows/BUSINESS_NATIVE_QA_RESULTS.zip`.

## 결함 회귀와의 연계

기존 `tests/common_api/regression` 및 `tests/test_release_safety_defects_v0431.py`, `tests/test_compare_scope_safety_v0431rc2.py`를 삭제하거나 대체하지 않는다. B1~B6는 실제 문서 작성 계층을 추가한 것이다. 결함이 발생하면 문제가 된 업무 문서 ID와 재현 입력을 단독 테스트에 추가한다.

## 제한

- 샘플은 **자동 테스트를 위한 합성 문서**이며 실제 계약서 법률 양식이나 회계 증빙으로 사용하면 안 된다.
- HWPX→DOCX 포맷 변환은 구조적 제한이 있고, DOCX→HWPX `rebuild`는 지원되지 않는다.
- Linux에서 HWPX를 Hancom 엔진으로 렌더링하거나 COM을 실행한 것은 아니다.
- Word/Hancom에서 보이는 글자·표·이미지의 시각 검증은 Windows 결과·육안 검토가 필요하다.
- 공개되지 않는 골든 HWPX 픽스처 33건은 공개 CI에서 SKIP된다.


## 2026-10-15 Word 독립 표 병합 회귀 수정

Windows COM에서 네 DOCX 문서의 독립 표가 Word 재저장 후 결합되는 이슈를 확인했습니다:
`01_contract` (2→1), `11_purchase_order` (2→1), `23_complex_tables` (4→1),
`24_long_form` (13→2). 업무 문서 생성기만 수정해 별개 최상위 표마다 DOCX의
`w:p` 구분 문단을 삽입합니다. HWPX 생성 경로와 PyWPDoc `Document.add_table()`
제품 코드는 변경하지 않았습니다.

새 회귀 테스트는 `tests/business_docs/test_independent_table_separators.py`,
`test_business_word_preservation.py`, `test_native_qa_evidence.py`에 있습니다.
원본과 재저장본 간 `w:t` 텍스트 순서, 미디어 바이트, 최상위 표 개수를 각각
검사합니다. 전체 Windows QA 결과 ZIP은 이제 동일 Windows 실행에서 사용한
`generated_inputs/` 원본과 SHA-256 해시도 보관합니다.

빠른 Word 실기기 재검증: `qa_business_docs/RUN_WINDOWS_FAILED4.bat`를 실행한 후
`business_qa_results/native_failed4/BUSINESS_NATIVE_QA_RESULTS.zip`을 제공하세요.
**Word COM 재저장 전에는 표 구조 문제가 해결됐다고 확정하지 않습니다.**
