# PyWPDoc v0.43.1rc2 — 배포 전 체크리스트 (2026-10-15)

## 검증된 항목

- MIT 라이선스 적용 및 wheel 메타데이터 확인.
- 공개 소스 Actions 선택자: 639 PASS / 13 DESELECTED / 0 FAIL.
- 일반 `python -m pytest -q`: 708 PASS / 33 SKIP / 0 FAIL. 33건은 재배포 불가능한 원본 HWPX 문서에 의존합니다.
- 비공개 원본을 일시 복원한 33건: 33/33 PASS (검사 후 원본 제거).
- 전체 741개 동시 실행은 시간 제한으로 완료되지 않아 단일 전체 PASS라고 주장하지 않습니다.
- 패치 회귀 16건 + 추가 scope 안전성 16건 + Windows 부트스트랩 단위 검사 8건: 40/40 PASS.
- wheel 독립 설치·두 형식 문서 재열기 및 표 테두리 차단 스모크 PASS.

## 게시 전 미완료

1. Microsoft Word 및 한글 2020에서 **이번 수정판**의 비교·저장·승인/거부·화면 출력 재검증.
2. 실제 GitHub Actions Ubuntu/Windows 3.10–3.13 실행 확인. 자체 Windows 러너 필요.
3. 사설 원본이 있는 환경에서 전체 회귀 단일 실행 완료 권장.
4. MIT 권리자·테스트 예제 자료의 재배포 권리 최종 확인.
5. GitHub 푸시와 PyPI Trusted Publisher 설정; 현재 실제 푸시/업로드는 완료되지 않음.

## 게시 시 주의

- 저장소: https://github.com/rydolabs/PyWPDoc
- 버전은 기존 v0.43.0을 덮어쓰지 말고 rc2를 명시합니다.
- `publish.yml`은 GitHub Release 게시 후 PyPI 배포를 시도하므로, 배포 승인 전에 릴리스를 게시하지 않습니다.
- 변경 추적의 지원 범위는 `KNOWN_ISSUES.md`와 `docs/COMPATIBILITY.md`에서 확인합니다.
