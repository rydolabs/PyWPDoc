# v0.43.1rc2 병합 격자 정규화 테스트 추가분

- **스테이징용 전체 ZIP**: 기존 `nssang00/chatgpt-write-test`의 `projects/pywpdoc/`와 `.github/workflows`에 덮어쓰기. 최종 배포용 저장소에 올리지 말 것.
- **테스트만 ZIP**: 프로젝트 소스 루트로 테스트/QA 파일들을 합칠 때 사용. `.github/workflows`는 저장소 최상단으로 옮길 것.
- **Windows 전체 키트 ZIP**: `PyWPDoc/qa_business_docs/RUN_WINDOWS_MERGED_GRID.bat` 실행 후 결과 ZIP 회신.
- 제품 라이브러리 코드는 바꾸지 않았고 버전은 **v0.43.1rc2 그대로**입니다.
- 로컬 신규 pytest **78 PASS**, 전체 분할 회귀 **1,228 PASS / 33 SKIP**입니다. 신규 16건 실제 Windows COM은 미실시.
