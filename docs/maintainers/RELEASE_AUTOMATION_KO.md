# 릴리스 자동화 운영 지침 (0.44.0rc1 초안)

1. `main`에 Conventional Commit이 들어오면 `release-please.yml`이 버전/CHANGELOG PR을 제안합니다. **PR을 자동 병합하지 않습니다.** 릴리스 PR을 확인하고 승인 병합해야 GitHub Release가 만들어질 수 있습니다.
2. `googleapis/release-please-action`에 사용한 기본 GITHUB_TOKEN은 그 토큰이 만든 PR에 CI `pull_request` 워크플로가 자동으로 연결되지 않는 제약이 있습니다. GitHub App token을 별도 설정하거나, `ci.yml`의 `workflow_dispatch`로 릴리스 PR 브랜치에 대해 CI를 수동 실행해 점검해야 합니다. 미검증 릴리스 PR은 병합하지 않습니다.
3. `release-please`의 Python prerelease(`rcN`) 전환 정책은 **실제 GitHub에서 아직 검증하지 않았습니다**. 첫 `0.44.0rc1`과 정식 `0.44.0` 태그·버전은 의도한 번호인지 검토 후 진행하세요. 태그·Release를 자동으로 게시하는 첫 실행 전에 워크플로를 별도 승인하세요.
4. `publish.yml`은 **workflow_dispatch 전용**입니다. 릴리스 태그, GitHub Release published, 소스 버전, 동일 커밋의 성공한 `PyWPDoc CI`를 확인한 뒤 wheel/sdist를 빌드합니다.
5. 별도 `publish` job만 GitHub 환경 `pypi`와 `id-token: write` 권한을 사용합니다. 환경 승인 없이는 PyPI에 업로드되지 않습니다 (Required reviewers 보호 설정 필수).
6. `PyPI Pending Publisher`: GitHub owner `rydolabs`, repo `PyWPDoc`, file `publish.yml`, environment `pypi`. 첫 PyPI 배포 성공 후 활성화됩니다.
7. 파일은 **로컬 준비용**. GitHub Actions는 원격 workflow가 등록되기 전까지 존재/실행하지 않습니다.

## 신규 릴리스의 권한 범위

- CI: 읽기 전용 (`contents: read`), 병합 전 테스트·wheel 검사.
- release-please: `contents: write`, `pull-requests: write`가 필요하며, 테스트 프로젝트 코드에서 git 명령을 자동 실행하지 않습니다.
- publish: `id-token: write`는 배포 job에만 사용. API 토큰을 보관하지 않습니다.
- `0.44.0rc1` 최초 게시, GitHub Release, PyPI 업로드는 매번 별도 사용자 승인 사항입니다.
