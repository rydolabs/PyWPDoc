# PyWPDoc 로컬 테스트 전용 패키지 (Git 처리 코드 제거)

이 패키지는 PyWPDoc v0.43.1rc2 제품 소스와 기존 테스트를 보존하면서,
Git 저장소 초기화·복제·브랜치 관리·커밋·push·릴리스 관련 실행 코드를 제외한 **로컬 테스트 전용** 구성입니다.
**이 ZIP 자체에는 GitHub Actions 워크플로도 포함하지 않았습니다.**

## 실행 방법

1. ZIP을 새 위치에 압축 해제합니다.
2. Windows: `PyWPDoc\RUN_LOCAL_TESTS.bat` 실행.
   PowerShell 직접 실행: `PyWPDoc\RUN_LOCAL_TESTS.ps1`.
   macOS/Linux: `cd PyWPDoc && bash RUN_LOCAL_TESTS.sh`.
3. 전용 `.venv`를 만들고 테스트 의존성을 설치한 다음 ① 전체 분할 회귀,
   ② public selector, ③ 소스 컴파일을 순서대로 실행합니다.
4. 결과는 `PyWPDoc/.test-results/`의 JSON·LOG·JUnit XML에서 확인합니다.
   실패해도 코드나 파일을 GitHub에 전송하지 않습니다.

반복 실행으로 설치 시간을 줄이려면 PowerShell에서 `./RUN_LOCAL_TESTS.ps1 -SkipInstall`을 사용하세요.
의존성이 설치되어 있지 않으면 첫 실행에는 `-SkipInstall`을 사용하지 마세요.

## 분리한 항목

- 프로젝트 `scripts/publish_github.ps1`, `scripts/publish_github.sh` 제거
- `scripts/prepush_gates.py` 제거 → `scripts/run_local_qa.py`로 **로컬 검사 기능만** 대체
- `scripts/check_release_tag.py` 제외 (배포 절차 전용)
- `.github/workflows/` 및 `.gitignore` 제외
- 이전 `PUSH_STAGING_WINDOWS.*`는 포함되지 않으며 사용하지 마세요

제품 API와 본래 테스트의 판단 조건은 변경하지 않았습니다. 다만 테스트 실행기 명칭과 안내만 바뀌었습니다.

## 별도 합의가 필요한 일

개발용 GitHub 업로드, 브랜치/PR 구성, 워크플로 반영, 최종 공개 배포는
테스트 실행과 별개로 **사용자와 범위를 정한 뒤** 진행합니다.
이 패키지를 실행하는 것 자체로 GitHub push나 PyPI 업로드는 발생하지 않습니다.
