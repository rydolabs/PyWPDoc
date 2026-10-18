> **Historical QA documentation:** This file contains legacy release figures and directories. For 0.44.0rc1 source layout and current portable CI command, see [tests/README.md](https://github.com/rydolabs/PyWPDoc/blob/main/tests/README.md) and [testing evidence](testing/README.md). Historical numbers are not automatically repeated passes on the new source layout.

# Testing and verification policy

## Test tiers

1. **Public CI (automatic):** Linux/Windows Python 3.10-3.13 where configured. Runs public fixture-compatible unit and integration tests for both DOCX/HWPX, a PyPI-style wheel build, metadata (`twine check`), and fresh wheel import/write smoke. The public suite is intentionally smaller than the private-fixture suite; the exact Actions run is the authority for its test count.
2. **Historical full regression (709/709 at v0.43.0; 725/725 at v0.43.1rc1 in private-fixture environment):** includes a legacy original school announcement fixture that is not distributed publicly pending redistribution rights verification. Some tests assert its exact HWPX XML/hash and school-specific contents. Never claim those tests ran on GitHub CI without that fixture.
3. **Windows native validation (historical 18/18 pass):** requires licensed Hancom Hangul 2020 / Microsoft Word installed on Windows. GitHub-hosted runners **cannot run Hancom GUI COM tests**. The `.github/workflows/native-windows.yml` workflow targets a manually provisioned Windows self-hosted runner and is dispatch-only; if no runner is available, it remains queued.
4. **Visual QA:** real Word and Hancom GUI pagination remains environment dependent. Included screenshots represent a LibreOffice DOCX render and a Hancom HWPX embedded preview, not identical screenshots from two editors.

## Run portable tests

```bash
python -m pip install -e ".[test,unified]"
python scripts/run_public_tests.py
# Or run the complete collection: cases needing the private fixture are marked SKIP when absent.
python -m pytest -q
```

## Run the full suite with licensed/private fixture

Restore the original trusted fixture to `tests/fixtures/original_notice.hwpx`, then run `python -m pytest -q`. It must agree with the immutable original hash recorded in `tests/baseline/v0215_manifest.json`. Do not publish this proprietary fixture without the owner's permission.

### Ported python-docx tests

75 selected behavior checks (23 first-round + 52 extended) across DOCX/HWPX passed historically. These test user-visible behavior, **not** all upstream `python-docx` tests and not private upstream XML interfaces. Details: `tests/test_release_python_docx_port_v0430.py` and `tests/test_python_docx_extended_port_v0430.py`.

### Known limits

Automated package structure/semantic text tests are not the same as every Word/Hancom visual layout check. In the longer synthetic DOCX example, comparing across the same paper size and margins yielded 51 pages in LibreOffice; such counts are renderer-specific.

## v0.43.1rc2 body-only compare safety

`compare(everywhere=False)` does not silently copy changes to table borders, cell properties, merges, or images outside the selected body text. These are rejected with `compare-outside-scope-changes-unsupported` instead of being emitted as untracked changes. It is not a claim that every native format/style mutation is tracked, and genuine Word/Hancom review behavior still needs Windows GUI inspection.
