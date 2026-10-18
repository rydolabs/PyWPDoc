# PyWPDoc 0.44.0rc1 공개 API·매뉴얼 구현 점검

## 이번 변경 범위

- 소스 기준: `PyWPDoc_0.44.0rc1_단일패키지_소스테스트_검토본.zip` (기존 엔진 유지).
- 공개 진입점 `pywpdoc.Document`에 문단·표·그림·구역·저장·기본 컬렉션의 **명시적 메서드/속성**을 추가. 기존 `_engine.common.Document`는 위임만 하는 얇은 계층으로 유지. 백엔드의 expert passthrough는 기존 회귀 호환 목적상 유지하되 공식 이식성 보장은 제외.
- `doc.add_picture(...)`의 PNG/JPEG/GIF/BMP 시그니처 감지: 이미지 형식을 생략한 공통 호출 가능. 모르는 형식이면 읽기 전용 오류 `DocumentValueError(code='common-image-format-unknown')`. 포맷별 기본 너비 정책은 기존대로 유지하므로 **크기를 명시해야 결과가 일관**됨.
- `doc.add_section()`은 인자 없는 공통 계약으로 명시. DOCX `start_type`, HWPX `after`는 각 Backend 전용 API에서 사용.
- 지원/비지원 메서드를 실제 구현에서 확인한 문서에 기재. 전략 문서의 `fill`, `merge`, `validate`, `accept_changes` 등은 구현 완료로 오해하지 않게 표시.
- 영문/한국어 시작 문서, 사용자 가이드, 공통 API Reference, 형식 전용 표, 결과/예외, 제약 사항, 6개 실행 예제, `tests/api_contract/` 추가.
- `mkdocs.yml`, docs extra, docs 검사 스크립트, GitHub `ci.yml`의 docs/API job 추가. **GitHub Pages 배포는 이번 설정에서 자동 실행하지 않음**.

## 공통 API 변경 판단

| 주제 | 결론 |
|---|---|
| 문단·표·저장 | 직접 정의하여 `__getattr__`로만 보이는 문제 완화 |
| 이미지 | 형식 생략을 가능하게 해서 간단하게. 너비/높이 미지정은 형식별 기존 기본값 유지 |
| 구역 | 포맷마다 다른 인자 사용을 공통 API에 강제로 합치지 않음 |
| Native/Backend | 고급 사용자용임을 명시하고 공통 API 보장 범위에서 제외 |
| 기존 API 제거 | 하지 않음. 기존 테스트가 내부 백엔드 기능에 접근하는 경우 보존 |

## 문서 제공 정책

- GitHub README와 PyPI 설명: 짧은 제품 소개, 실제 DOCX/HWPX 출력 이미지, 매뉴얼 원문 링크.
- GitHub Pages: 배포 승인 후 `mkdocs.yml` 기반 검색 가능한 HTML (계획 주소 `https://rydolabs.github.io/PyWPDoc/`이며 현재 미게시).
- GitHub `docs/` 원문: 즉시 열람 가능. 한국어 `docs/ko`, 영어 기본 문서.
- 매뉴얼 코드의 원본은 `examples/manual/*.py`; CI에서 DOCX/HWPX 양쪽 실행.
- 상세 클래스별 전문 자동 생성은 외부 API 노출 문제 해결 후 추진. 이번 단계는 명시적인 문서 계약으로 품질 우선.

## 상태 및 남은 게이트

1. Python 회귀 및 예제 테스트 결과는 별도의 실제 실행 로그 참조.
2. `scripts/check_api_manual.py`가 상대 링크·snippets·핵심 시그니처 확인.
3. **로컬 환경에 `mkdocs-material`이 없고 외부 설치 네트워크 연결에 실패**하여 MkDocs HTML 빌드는 아직 미검증. GitHub CI에서 실제 빌드 확인 필요.
4. 변경된 `0.44.0rc1` 패키지로 Windows Word/한컴 실기 네이티브 검증은 아직 수행하지 않음.
5. GitHub push, GitHub Pages/Release 공개, PyPI 업로드 수행하지 않음.

## 사용자 검수 권장

- `README.md` 첫 화면, `docs/ko/index.md`, `docs/ko/api.md`, `docs/reference/document.md`를 먼저 검토.
- 공통 API의 이미지 크기 기본값을 향후 완전히 통일할지는 별도 설계 결정. 지금은 기존 문서 호환성을 우선.
- API 동작/용어 확정 → 원격 CI → Windows 실기 검증 → GitHub 게시·문서 사이트 승인 순서 권장.

## 실행 검증 기록 (2026-10-18, 현재 작업 환경)

- `PYTHONPATH=src python scripts/run_public_tests.py -m "not native and not performance"` → **1,304 passed, 13 deselected, 0 failed**, 종료 코드 0 (163.49초). 원본의 비공개 픽스처 4개 테스트 파일과 13개 테스트 노드는 공개 실행에서 명시적으로 제외됨.
- `PYTHONPATH=src python -m pytest -q tests/test_architecture_v013.py tests/test_metadata_modules_v020.py tests/api_contract` → **39 passed**, 종료 코드 0.
- `PYTHONPATH=src python scripts/check_api_manual.py` → 문서 Markdown, 내부 상대 링크, snippets 및 명시적 API 시그니처 PASS.
- `setuptools.build_meta.build_wheel` / `build_sdist` → **wheel + sdist 생성 성공**. Wheel에는 `pywpdoc`만 포함하고 `python_hwpx_next`, tests, docs가 없음. Sdist에도 테스트/문서는 포함되지 않음(소스 저장소에서 제공).
- 별도의 `--target` 디렉터리에 wheel 설치 → `pywpdoc.__version__` **0.44.0rc1**, DOCX/HWPX 문단·그림·구역 생성 및 재열기 성공.
- **미완료:** `mkdocs build --strict` (네트워크 차단으로 mkdocs-material 설치 불가), GitHub Actions 원격 CI, Windows Word·한컴 새 후보 네이티브 실행.
