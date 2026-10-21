# GitHub Actions로 PyWPDoc Release 자동 생성

**GitHub Release를 수동으로 만들지 않아도 됩니다.** Release용 Actions 워크플로는 검증된 소스와 배포 파일을 확인한 뒤 새 태그와 GitHub Release를 자동 생성합니다.

단, **코드 Push나 CI 통과만으로 Release가 게시되지는 않습니다.** 사용자가 직접 Actions에서 실행해야 하고, PyPI 배포도 독립된 승인 단계로 유지됩니다.

## 실행 전에

- 변경사항이 모두 `main`에 병합됐는지, **현재 `main` 커밋에 대한 CI 10개 작업이 전부 성공**했는지 확인합니다.
- 릴리스 버전은 `pyproject.toml`의 `[project].version`과 같아야 합니다.
- 동일한 태그 또는 Release가 이미 있다면 기존 게시물을 덮어쓰지 않습니다.
- 기존 시험 배포 `0.44.0rc1`의 Word·한컴 실기 검증은 [QA 보고서](../testing/native-qa-0440rc1-2026-10-18.md)에 기록됐습니다. 이 결과를 **새 `0.44.0`의 최종 실기 승인**이나 신규 PDF 시각 검증으로 과장하면 안 됩니다.

## Actions 실행

1. [**Create PyWPDoc GitHub Release**](https://github.com/rydolabs/PyWPDoc/actions/workflows/release.yml)를 엽니다.
2. 오른쪽 **Run workflow**에서 브랜치 **`main`**을 선택합니다.
3. 다음 입력값을 넣습니다.

| 항목 | 첫 릴리스에서 입력할 값 |
| --- | --- |
| `release_tag` | `v0.44.0` (안정 버전 승인 및 재검증 완료 후) |
| `expected_sha` | **최신 `main` 커밋 전체 40자리 SHA**. 이 자동화 PR이 병합된 뒤 CI를 통과한 새 커밋을 사용하세요. |
| `confirm_release` | 정확히 `PUBLISH` |

4. **Run workflow**를 클릭합니다.
5. **Settings → Environments → github-release**에서 Required reviewers를 설정해 두었다면, 빌드 검증 후 추가로 배포 승인이 필요합니다. 이 보호 규칙을 설정하지 않은 경우 별도 승인 화면은 나오지 않습니다.

검증 과정에서는 해당 커밋의 성공한 `main` Push CI, 버전 일치, 동일 태그 부재, `twine check --strict`, DOCX/HWPX wheel 스모크 테스트를 확인합니다. 배포 직전에도 커밋·태그를 재검사합니다.

정상 완료 시 태그와 GitHub Release, **wheel·sdist·SHA256SUMS**가 생성됩니다. `rc` 버전은 자동으로 **Pre-release**로 표시되며 Latest로 지정하지 않습니다. 실패 시 기존 태그를 강제 변경하거나 덮어쓰지 않습니다.

## PyPI는 별도로 게시

GitHub Release를 확인한 다음 [**Publish PyWPDoc to PyPI**](https://github.com/rydolabs/PyWPDoc/actions/workflows/publish.yml)에서 같은 `release_tag`를 입력해 실행합니다. `pypi` 환경에 리뷰 승인이 설정된 경우에만 해당 승인 화면이 나타납니다. PyPI Trusted Publisher 설정도 별도로 필요합니다.

현재 [Prepare PyWPDoc Release](https://github.com/rydolabs/PyWPDoc/actions/workflows/release-please.yml)는 Release PR 준비 전용이며, 실제 GitHub Release를 만드는 워크플로는 **Create PyWPDoc GitHub Release**입니다.

**주의:** GitHub의 일반 CI는 실제 Windows Word·한컴 COM 렌더링 검증을 대체하지 않습니다. 새 버전의 검증 기록을 확인하고 Release를 승인해야 합니다.
