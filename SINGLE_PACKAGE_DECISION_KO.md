# PyWPDoc 0.44.0rc1: 단일 배포 패키지 확정(검토안)

2026-10-18 사용자 의견: `python_hwpx_next`는 공개 배포 전 개발명이므로 import 호환성 계층은 불필요함.

## 변경

- `src/python_hwpx_next/` 호환 라우터 제거.
- `pyproject.toml`의 배포 대상은 `pywpdoc*`만 설정.
- `src/pywpdoc/_engine/`는 내부 구현이며, 공개 API는 `pywpdoc.Document`.
- 과거 회귀 테스트와 생성기는 시나리오를 유지하면서 새 내부 경로로 import 정리.
- 내부 엔진의 오래된 독립 버전 `0.21.3` 제거; 외부 버전은 `pyproject.toml` 기반 `pywpdoc.__version__`만 제공.

## 검증

- 단일 소스 지정 후 패키징/코어/아키텍처 집중 테스트 51 PASS.
- 공개 회귀 테스트 (스크립트 기본 제외 정책 유지) 실행 종료 코드 0, 진행률 100% (전체 기록 `_single_package_pytest.log`).
- wheel 생성 및 별도 설치 경로에서 DOCX/HWPX 생성·재열기 PASS.
- sdist 생성 PASS; 배포물에 `python_hwpx_next` 경로 없음.
- 내부 버전 제거 후 패키징 집중 테스트 재실행 예정.

## 보류

- 새 후보의 Windows Word/Hancom 네이티브 테스트와 GitHub 원격 CI는 아직 미실행.
- 공개 자료의 배포 권리 확인 및 PyPI 업로드는 미실행.
- GitHub push / Release / PyPI 배포 모두 승인 전 보류.
