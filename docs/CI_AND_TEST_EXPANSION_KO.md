# PyWPDoc 단계별 품질 게이트 및 `python-docx` 대비 테스트 확장

## 브랜치/저장소

- 실험: [`nssang00/chatgpt-write-test`](https://github.com/nssang00/chatgpt-write-test)의 `pywpdoc/rc2-regression-staging` 전용 브랜치, `projects/pywpdoc/` 하위 디렉터리
- 공개/정식 배포: [`rydolabs/PyWPDoc`](https://github.com/rydolabs/PyWPDoc), 모든 게이트와 심사 완료 전 업로드하지 않음
- STAGING에는 PyPI 업로드 workflow와 릴리스 트리거를 설치하지 않음.

## 비교 기준

2026-10-15 조회한 `python-openxml/python-docx` GitHub master에는 `tests/**/*.py` 87개(`__init__.py` 포함), `features/**/*.feature` 67개가 있음. PyWPDoc rc2는 `tests/test_*.py` 59개에서 이번에 60개로 증가. **테스트 파일 수·통과 건수는 서로 품질 동일성을 보장하지 않음.** `python-docx`의 BDD는 사용자 단위 행동 명세라는 점이 중요한 참고 대상.

## 필수 게이트

1. 기능 브랜치에 코드 및 문제 재현 테스트 작성. 로컬 `python -m pytest -q` 먼저 수행.
2. ChatGPT staging 브랜치 push 시 Actions로 공개 전 회귀를 실행한다. Actions가 실행되려면 소스 push는 선행되어야 함. 즉 "push 전에 Actions 실행"은 불가능하지만 **merge 전 필수 CI**를 설정할 수 있음.
3. Ubuntu + Windows × Python 3.10/3.11/3.12/3.13 8개 환경에서 전체 portable tests (`pytest -q`) PASS, 허용된 비공개 픽스처 SKIP만 존재.
4. 공개용 fixture-안전 테스트는 별도 job에서 실행하고 selection 수를 명시.
5. wheel/sdist build, `twine check`, 설치 후 DOCX/HWPX smoke.
6. 집중 안전성 테스트에 대한 coverage 보고서 생성. 이 최초 범위의 49% 커버리지를 제품 전체 커버리지 수치라고 주장하지 않음.
7. PR에서 기존 필수 체크가 녹색이어야 리뷰/merge; 테스트 기간에는 **staging 브랜치**(`pywpdoc/rc2-regression-staging`) 직접 push를 제한하고 PR 필수 체크를 지정해야 함. 다른 프로젝트의 `main` 브랜치는 변경하지 않음.
8. Windows 한글·Word COM 검증 및 비공개 소스 픽스처 전체 회귀는 별도 self-hosted 워크플로/수동 QA. 공개 Hosted 러너에서 한글 GUI는 실행되지 않음.
9. 현재 설계에서는 저장소 루트에 `src/pywpdoc/`, `tests/`, `.github/workflows/`를 두고 검증 후 릴리스 승인. `python_hwpx_next`는 배포 전 내부 이름이므로 호환 패키지를 만들지 않음. pip 패키지에 tests 포함 강제는 하지 않음(소스 GitHub에는 필수).

## 다음 테스트 목표 (목표 수치는 릴리스 승인 조건을 새로 정할 때 측정 후 확정)

- **P0/P1 수정 구간:** 분기 커버리지와 상태 불변성 확인을 필수화, 해당 모듈의 최소 커버리지를 점진적으로 85% 이상 목표
- **전체 코어:** 75~80% 이상의 의미 있는 라인 커버리지 목표를 참고하되 실제 베이스라인 확인 전 자동 Fail 기준으로 강제하지 않음
- **BDD:** Create/Edit/Template/Compare/Save/Reload/Review의 사용자 시나리오를 형식별 Given/When/Then으로 문서화
- **실기기:** Word/한글 2020 저장·열기·네이티브 변경 승인·거부의 결과물을 아카이브하고 XML, 의미, 화면 세 단계 비교
- **거부 케이스:** 미지원 구조 변경, 유효성 오류, 불완전 태그, 잘못된 참조, 원본 파일 손상 등은 실패 코드와 원본 불변성 동시 검사

## 아직 해야 할 일

- staged GitHub 소스의 실제 업로드 및 원격 Actions 실행은 아직 완료되지 않음.
- 신규 35개 독립 테스트는 Linux에서 검증됨. Windows CI, GitHub ruleset/required checks는 아직 실행·설정하지 않음.
- 비공개 33건의 합성 대체 테스트 구축 필요. 수많은 `python-docx` 내부 private implementation 테스트를 무분별하게 복제하지 않음.
