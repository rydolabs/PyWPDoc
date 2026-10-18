# PyWPDoc 0.44.0rc1 릴리스 후보 점검 결과

> **상태: 로컬 릴리스 후보 / 검토용. GitHub 소스 push, GitHub Release 및 PyPI 업로드 미실행.**
> 마지막 로컬 회귀: 2026-10-18. 최종 사용자 승인 이전에는 공개하거나 게시하지 않는다.

## 준비 완료

- PART 01 `0.43.1rc2` 제품 코드를 기준으로 `src/pywpdoc/` 패키지와 `src/pywpdoc/_engine/` 내부 엔진으로 재편성. 파일 이동과 경로 수정, 버전 메타데이터·호환 import 조정 외에 문서 생성 알고리즘 변경은 없음.
- 공개 전 내부 프로젝트의 레거시 import 호환 계층은 제거. 배포 패키지는 `pywpdoc` 단일 패키지이며, 이 변경 후 재검증이 필요함.
- 테스트 디렉터리에 공통 API, 과거 회귀, 역사적 합성 픽스처, 최신 24종×2형식 업무 문서 생성/감사, 병합 표, Windows 네이티브 QA, wheel/sdist 설치 검증을 통합. 역사적 `test_*.py` 노드 ID는 유지.
- 2026-10-18 실제 Word/Hancom PDF로부터 README 대표 비교 이미지를 제작. 사진·데이터의 출처는 `docs/assets/readme/PROVENANCE.md` 참조. 제품이 출력을 양 형식에서 *동일하게* 렌더링한다는 뜻은 아님.
- 영어 README.md + README.ko.md, pyproject.toml의 `0.44.0rc1` 단일 제품 버전 선언, `.github/workflows/{ci,release-please,publish}.yml` 로컬 설정 초안.
- 한컴 네이티브 실행기의 `start_hwp()`에 사용자 등록 공식 Automation 보안 모듈 검사 및 `RegisterModule()` 사전 호출 추가. 등록 실패 시 파일 열기 전에 중단. **Windows 실기 재검증은 아직 필요**.

## 검사 결과 (검증된 범위)

| 검사 | 결과 | 한계 |
|---|---:|---|
| 로컬 공개 회귀 (`scripts/run_public_tests.py -m 'not native and not performance'`) | **1,284 PASS / 0 FAIL / 13 DESELECTED** | Linux/Python 3.13 기준. 비공개 원본을 요하는 케이스 및 native/performance 제외 |
| `tests/native` 부트스트랩·안전성, `tests/packaging` | **29 PASS** | 비Windows 경로 검사 중심. 네이티브 COM 작업 아님 |
| 역사적 QA 집중 검사 | 69 PASS / 6 SKIP | 이전 패키지 마이그레이션 후의 부분 검사 |
| 휠 빌드 | `pywpdoc-0.44.0rc1-py3-none-any.whl` 생성 | 분리된 설치 경로에서 두 형식 생성·재열기 PASS |
| 소스 배포물 | `pywpdoc-0.44.0rc1.tar.gz` 생성 | 분리된 설치 경로에서 두 형식 생성·재열기 PASS |
| GitHub Actions YAML | 로컬 파서 확인 | GitHub에서 실제 CI, 워크플로, 권한은 **미검증** |
| `twine check` | 미실행 | 로컬 네트워크로 build/twine 확보 실패; GitHub CI에서 실행 예정 |
| 신규 0.44.0rc1 Word/Hancom 네이티브 검증 | **미실행** | 이전 0.43.1rc2 QA의 48/48 PDF/재저장은 신규 구조 검증을 대체하지 않음 |
| `README` GitHub 파일 링크 | 로컬 파일 존재 확인 | 원격 저장소가 비어 있어 링크는 소스 push 전 작동하지 않음 |

## 공개·배포 전 필수 게이트

1. **공개 자료 권리 확인**: `tests/fixtures/`의 과거 원본/사용자 편집 결과/ZIP, 예제, 문서, 캡처 스크린샷을 공개 가능한지 소유자가 마지막 점검. 특히 `tests/fixtures/historical/`에 있는 네이티브 결과 ZIP은 과거 데이터이므로 권리/민감정보를 재확인.
2. **첫 GitHub 소스 push 별도 승인**: `rydolabs/PyWPDoc`는 마지막 확인 시 빈 공개 저장소. 이 ZIP은 로컬 검토/QA 패키지이므로 자동 업로드하지 않음.
3. **GitHub CI 원격 PASS**: Ubuntu/Windows × Python 3.10–3.13 매트릭스, wheel/sdist 및 `twine check`, 빌드 wheel 독립 설치. Release Please PR/버전 정책은 실제 리포지토리에서 동작 확인 필요.
4. **Windows Office/Hancom 0.44.0rc1 재검증**: 사용자 등록 공식 한컴 보안 모듈 활용, 열기/저장/PDF와 핵심 화면 재비교. 반복 접근 허용창을 자동 클릭해 우회하지 않음.
5. **버전·릴리스 승인**: 최초 태그 `v0.44.0rc1`을 수동으로 검토. `0.44.0` 정식 릴리스는 rc 검증 완료 후 별도 결정.
6. **PyPI 승인**: 사용자가 등록한 Pending Trusted Publisher는 owner `rydolabs`, repo `PyWPDoc`, workflow `publish.yml`, environment `pypi`. GitHub `pypi` 환경의 Required reviewers가 활성인지 확인할 것. 소스 push / GitHub Release / PyPI 게시에 각각 사용자 승인이 필요.
7. **최초 PyPI 등록 및 설치**: 승인된 `workflow_dispatch` → `pypi` 환경 승인 → OIDC 게시 이후 깨끗한 가상환경에서 실제 PyPI wheel 설치 및 DOCX/HWPX 열기/저장 확인.

## 파일 안내

- `README.md` / `README.ko.md`: 사용자 첫 화면 및 설치 예제
- `tests/README.md`: 테스트 체계와 비공개 픽스처 제외 이유
- `docs/assets/readme/PROVENANCE.md`: 스크린샷 증거와 유래
- `docs/maintainers/MIGRATION_0.44.0rc1_KO.md`: 호환성 및 내부 경로 이전
- `docs/maintainers/RELEASE_AUTOMATION_KO.md`: Actions 자동 버전 변경의 한계
- `docs/PUBLISHING.md`: GitHub/PyPI 승인 단계

**테스트 코드에서는 git commit/push/원격 게시 작업을 수행하지 않는다.**
