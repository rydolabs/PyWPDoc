# Current release candidate: 0.44.0rc1 — quality gates

- Source and install smoke locally passed on Python 3.13 before public-fixture pruning.
- **Required**: published GitHub CI green on supported Python/OS matrix.
- **Required**: 0.44.0rc1 Windows Word/Hancom native open-save/PDF visual review.
- **Required**: MkDocs HTML build and actual Pages deployment.
- **Required**: confirm redistribution rights for all remaining test fixtures and README screenshots.
- **Required**: PyPI Trusted Publisher approved and isolated post-publish install smoke.
- Test deselections/skips never count as PASS.
- GitHub Release and PyPI publication are separate approval gates.

---

# Previous quality gates — historical archive (not evidence for this candidate)

# Quality gates — PyWPDoc v0.43.0 (2026-10-14)

## Release candidate gates

- **PASS**: Python regression and representative `python-docx` public-behavior ports, **709/709** (657 prior + 52 new) from the extended long-document QA cycle.
- **PASS**: Windows native RC 11/11 and extended 7/7 (long/stress Word + Hancom round trips and QA verifier tests); submitted results independently audited.
- **PASS**: DOCX/HWPX long and stress semantic preservation, including text, table content, embedded image hashes, and explicit bold runs.
- **PASS (cross-renderer proxy only)**: long 51/51 pages and stress 109/109 pages (LibreOffice rendering before/after Word save), with page-wise extracted text equality; sampled pages checked for gross shifts.
- **PASS**: 0 unexpected blank pages and no text blocks beyond PDF page bounds in those DOCX renders.
- **PASS**: current wheel's package code matched the candidate source; final metadata-only wheel must be rebuilt/smoke-checked.
- **REVIEW**: native Microsoft Word / Hancom GUI page-break, table split, fonts and image placement sign-off is not established by LibreOffice/PDF or package thumbnails.
- **PASS (licensing metadata)**: MIT selected and root `LICENSE`/`pyproject.toml` license metadata added. License adoption assumes Rydolabs holds the necessary rights.
- **REVIEW (public GitHub readiness)**: native Word/Hancom full layout sign-off and initial GitHub publish have not been completed by this local package preparation.
- **SUPPORTED-BY-DESIGN-LIMIT**: native HWPX table-row/column/merge structural change tracking is not claimed; keep fail-closed.
- Metadata / dependency contract: `pywpdoc[unified]` required for DOCX backend use when python-docx is not otherwise installed.

For evidence, see `RELEASE_FINAL_QA_V0430_KO.md`. Do not promote any previous 'SKIP' into a PASS without a real Windows result.

---

## Historical v0.40.0 gates (archived)

# Quality gates

Current release: **v0.40.0 candidate**

- full automated suite must pass from the working tree;
- the exact source bundle must reproduce the same full-suite result after extraction to a clean directory;
- built wheel must report version 0.40.0 and retain the HWPX row fail-closed contract;
- v0.40.0 row probes must validate as ordinary HWPX and contain no fabricated row Track Changes metadata;
- the row analyzer must identify supported inline Insert/Delete markers as `hp:t` scoped and must not misclassify plain row structure changes as a row revision anchor;
- HWPX row-level structural revisions remain fail-closed until a Hancom-authored unaccepted row-change file establishes Accept/Reject semantics;
- existing CharShape/ParaShape/resource remap/semantic-style validation gates remain unchanged.

## Diagnostics-only batch testing

- A single HWPX contains independent ten native-editor tasks; case ID in the first cell must survive editing.
- `quality/native_batch_suite.py` must log each case even if a different case fails, is skipped, or is unsupported.
- Text markers must match both range IDs and header `trackChange` IDs; changes in other tables must not satisfy a case.
- Cell text markers do **not** prove row/column structural revision support.
- `quality/run_batch_checks.py` must continue the native analysis if pytest invocation fails.
- New 10-case native file has not yet been operated on in Hancom; no native GUI outcome is implied.


## v0.43.0 RC verification (2026-10-14)

- PASS: baseline 634 + ported python-docx public-contract scenarios 23 = 657/657, executed as 217/216/224 grouped pytest runs.
- PASS: clean wheel target install and DOCX/HWPX API integration smoke.
- HOLD: Hancom 2020 native H01/H03/H05/H07 and MS Word W01/W02 are pending execution on a Windows host.
- PASS (offline): H02/H04/H06/H08.
- Do not equate skipped COM checks with release approval. Native GUI/visual display remains unverified.
- HWPX table row-level tracked revisions remain explicitly unsupported.
