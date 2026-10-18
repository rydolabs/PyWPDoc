# 병합 격자 정규화 회귀 QA — v0.43.1rc2 (테스트만 추가)

## 판정 원칙

- **허용**: 1행 전체 병합인 단일 물리 셀의 DOCX 표에서, Word 재저장으로 `w:tblGrid`의 2열+`gridSpan=2`가 1열+단일 셀로 정규화되지만 본문 텍스트·표 수·행 수·셀 내용이 변하지 않은 경우. 사용자의 Windows COM 이전 결과 3쌍을 고정 합성 픽스처로 보존.
- **FAIL**: 독립 표 수 변화, 본문 텍스트 손실, 다중 행의 가로/세로 병합 해제, 병합 영역 손실, 행·물리 셀 수 또는 `vMerge`/`gridSpan` 변경 (1행 전체 병합 정규화 특례 제외).
- **시각 검사 별도**: PDF 출력 성공 및 문서 COM 재저장 성공만으로 화면 품질이나 사람의 육안 승인으로 선언하지 않음.

## 자동화 계층

1. `tests/common_api/regression/test_merged_grid_roundtrip.py`: Common API만 사용해 8개의 유형 × DOCX/HWPX 생성→저장→재열기→재편집. XML 물리 격자 검증과 오류 주입.
2. `tests/common_api/regression/test_word_native_merge_fixtures.py`: 이전 Windows COM 재저장 전/후 문서 3쌍으로 **실제로 Word가 수행한 정규화** 검증. 합성 자료이며 SHA-256 매니페스트 포함.
3. `qa_business_docs/windows_merged_grid.py`: Word+한글 실기기에서 16개 문서를 **각각 별도 COM 프로세스**로 재저장. 하나 실패해도 나머지는 계속 수행. 입력 원본·SHA-256·저장본·PDF·JSON을 ZIP에 포함.

## Windows 실행

`qa_business_docs\RUN_WINDOWS_MERGED_GRID.bat`를 실행하고 `merge_grid_native_results\MERGE_GRID_NATIVE_QA_RESULTS.zip` 업로드.

## Linux/CI에서도 실행 가능

```shell
python -m pytest -q tests/common_api/regression/test_merged_grid_roundtrip.py tests/common_api/regression/test_word_native_merge_fixtures.py
python -m qa_business_docs.windows_merged_grid --out merge_grid_generated --generate-only
```

Word/Hancom이 없는 Linux는 네이티브 재저장 **NOT_TESTED**. 최종 배포용 GitHub와 PyPI에 자동으로 게시하지 않음.
