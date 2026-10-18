# Current QA state — v0.43.0 (2026-10-14)

- Latest extended Python suite: **709/709 PASS**, including 52 new representative `python-docx` Common API ports.
- Windows native: RC **11/11 PASS** + extended **7/7 PASS**; native saved docs Word/Hancom independently audited for semantic preservation.
- Page-layout proxy: LibreOffice original vs Word-saved DOCX long 51 pages / stress 109 pages, page-wise extracted text equality, no unexpectedly empty pages, no out-of-page PDF text blocks.
- Native Word/Hancom display sign-off: **REVIEW (not verified here)**. HWPX `Preview/PrvImage.png` before native save may be blank, while Hancom regenerates it after save; preview thumbnail is not equivalent to full-document GUI check.
- Current wheel requires the optional `[unified]` extra for normal DOCX dependency installation. Packaging metadata will include project README in the RC rebuild.
- Public distribution license selected: **MIT**; LICENSE and wheel metadata updated. Native GUI layout sign-off remains REVIEW. Image appearances were user-checked.
- HWPX table-row/column structural Track Changes remains **UNSUPPORTED**, fail-closed.

See `RELEASE_FINAL_QA_V0430_KO.md` and `QUALITY_GATES.md`.

---

## Historical v0.40.0 QA state (archived)

# Current QA state — v0.40.0

- DOCX formatting Track Changes: Microsoft Word GUI confirmed.
- HWPX text/paragraph structural Track Changes: supported.
- HWPX CharShape Track Changes: Hancom 2020 GUI confirmed, including cross-document font/resource remap.
- HWPX ParaShape Track Changes: Hancom 2020 GUI confirmed for direct paragraph-format changes and cross-document list/image-bullet resources.
- v0.37.0 numbering/text-bullet blank change-description behavior matches Hancom 2020 native-authored behavior and is accepted as normal UI behavior.
- v0.38.0 embedded image-bullet cross-document Accept/Reject behavior: Hancom 2020 GUI confirmed.
- v0.39.0 semantic named-style identity gating: user GUI confirmation completed.
- HWPX table-row structural Track Changes: **native oracle required; fail-closed**. v0.40.0 adds the analyzer/probe set but does not claim support.

Current automated QA artifact: `qa_hwpx_row_tracking_probe_v0400/`.

## 2026-10-13: native accept/reject checkpoint

- Hancom 2020 native accept-all/reject-all HWPX: content and revision cleanup verified (12/12 + 12/12).
- Independent structural/content validation 26/26; Python tests 514/514 pass.
- Reviewer notes and source archive: `qa_native_accept_reject_v0400/native_verified_2026_10_13/`.
- Row/column/merge *structural* revision support is still NOT claimed.


## 2026-10-14 release candidate addendum

Latest verification: 657/657 pytest PASS. python-docx reference behavior port 23/23 PASS with documented proxy representation differences. Windows native test kit created but NOT yet executed under Hancom/Word; release status HOLD. See `RELEASE_CANDIDATE_QA_V0430_KO.md`.
