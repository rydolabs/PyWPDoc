# 0.44.0rc1 공개 전 검증 관문

이 파일은 사용자 승인 후에도 GitHub, Release, PyPI를 동시에 자동으로 게시하지 않기 위한 체크리스트입니다.

1. [ ] 공개 소스의 권리 검토(특히 tests/fixtures 및 docs/assets 이미지). 오래된 원본 수집 자료·실행 ZIP은 제외했습니다.
2. [ ] GitHub 소스 등록 완료 및 `PyWPDoc CI`의 8개 OS/Python 환경, wheel/sdist, docs PASS.
3. [ ] Windows Word/Hancom 0.44.0rc1 검증 ZIP 수령 및 버전/hash 확인, native 실패 0, 수동 스크린샷 승인.
4. [ ] GitHub Pages 매뉴얼 실제 빌드·링크 검사 후 수동 게시.
5. [ ] 최초 GitHub Release 태그 v0.44.0rc1과 pyproject.toml 버전 일치 및 별도 승인.
6. [ ] PyPI Pending Publisher/Environment 확인 후 수동 publish 승인.
7. [ ] PyPI 공개 패키지 새 환경 설치 및 DOCX/HWPX 사용 확인.

Release Please는 초기 설정에서 workflow_dispatch 전용이고 skip-github-release=true입니다. 자동 태그/Release 생성 기능은 별도 설계 검증 후 활성화하십시오.
