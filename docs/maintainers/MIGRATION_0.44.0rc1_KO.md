# 0.44.0rc1 단일 패키지 구조 전환

- 배포하는 Python 패키지는 `pywpdoc` 하나입니다.
- 내부 엔진은 `src/pywpdoc/_engine/`에 위치합니다.
- 이전 내부 프로젝트명인 `python_hwpx_next`는 **공개 배포 이전의 내부 개발명**으로 판단하여 별도 호환 라우터를 제공하지 않습니다.
- 외부 사용자는 `from pywpdoc import Document` API를 사용합니다.
- 과거 회귀·QA 테스트는 이름만 새 엔진으로 연결하며 테스트 시나리오는 유지합니다.
- 비공개 원본은 공개 저장소에 넣지 않습니다.
- 구조 개편된 이번 후보의 Windows 네이티브 검증과 GitHub CI는 아직 대기 중입니다.
