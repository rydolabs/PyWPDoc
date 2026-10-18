# Test suite / 검증 체계

- `common_api/` — shared DOCX/HWPX API unit, parity, integration, regression, negative tests
- Root `test_*.py` — historical regression contracts retained at their stable node IDs
- `business_docs/` — deterministic business document acceptance tests
- `generators/business_docs/` — deterministic 24-scenario document generator and audit tools
- `fixtures/` — approved redistributable fixtures and historical synthetic QA corpora with manifests
- `native/` — Word/Hancom Windows COM validation (requires installed desktop applications)
- `quality/` — offline verification tools; *not* run as part of ordinary pytest

## Portable tests

```bash
python -m pip install -e ".[test,unified]"
python scripts/run_public_tests.py -ra -m "not native and not performance"
```

Private original document fixture `tests/fixtures/original_notice.hwpx` is **not** shipped. Public CI explicitly excludes its tests. A skip is not a pass.

## Native visual evidence

Windows Word/Hancom render/PDF evidence is stored outside Git; 2026-10-18 validation records are historical, not a promise of visual pixel parity. GitHub-hosted CI does not supply Word/Hancom licenses.

## 2026-10-18 local release candidate check

`python scripts/run_public_tests.py -m "not native and not performance"`:
**1,304 passed, 13 deselected, 0 failed** on the local complete review ZIP before public-fixture filtering. The public staging branch deliberately excludes historical native result archives and therefore additionally SKIPs two fixture-dependent cases. Re-run after posting. on the local Linux Python 3.13 environment. This is not a claim of Windows Office COM coverage or GitHub-hosted CI success. See `docs/maintainers/RELEASE_AUDIT_KO.md`.

Windows native QA requires the user's Hancom official Automation security module to be registered first. A missing or invalid module stops before opening a file; the runner never clicks away access-control dialogs.

## API reference and manual regression (0.44.0rc1)

- `tests/api_contract/test_document_portable_contract.py`: explicit common methods, picture-size and format sniffing, section-specific opt-out.
- `tests/api_contract/test_manual_examples.py`: run all six documented `examples/manual/*.py` workflows on DOCX/HWPX.
- `scripts/check_api_manual.py`: offline links, example existence, snippets and portable signature check.
- `mkdocs.yml`: Markdown docs site configuration. GitHub CI builds with `mkdocs build --strict`; Pages publishing is a separate decision.
