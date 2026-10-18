# Common API behavior suite

All new tests exercise the **public `pywpdoc.Document` facade**. DOCX/HWPX are parametrized in `conftest.py`; tests assert observable output, exceptions and persistence. Some test setup intentionally uses a backend-specific `docx` object to construct a border-only change because that property is not exposed by the Common API. The behavior under test remains `Document.compare(...)`.

| Layer | Directory | Oracle | Gate |
|---|---|---|---|
| L1 Unit facade | `unit/` | Public object properties, errors and document model | Every PR |
| L2 Integration | `integration/` | Save-open equality, XML/ZIP, template, regex, search | Every PR |
| L3 Reference parity | `parity/` | Only the feature intersection with `python-docx` 1.2.x | Every PR |
| L4 Historical regression | `regression/` | Concrete independent-review incidents, fail-closed | Every PR |
| L5 Negative inputs | `negative/` | Corrupted packages, invalid regex, atomic error behavior | Every PR |
| L6 Native editors | existing `qa_windows/` + native workflow | Word/Hancom COM acceptance/rejection and save | Self-hosted Windows manual/release gate |
| L7 Performance & visuals | separately controlled benchmark + screenshots | Time trends, page breaks, table & image placement | Nightly/release, manual approval |

Run `python -m pytest -q tests/common_api` to focus on this suite. Run `python scripts/run_local_qa.py` before *any* staging push. Remote Actions still executes on push/PR, and merge into the protected branch should require all configured checks to pass.

These are **original PyWPDoc API tests**, organized after a review of public upstream `python-docx` categories; they do not copy upstream test source code. Case counts come from pytest's parameter expansion, not unique test functions, and do not measure full upstream equivalence.
