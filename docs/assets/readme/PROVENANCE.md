# README asset provenance

These PNG files are actual **PDF page renders** from prior Windows native QA, not hand-created mock-ups and not screenshots of live application chrome.

- `contract-word.png`, `contract-hancom.png`, `docx-hwpx-contract-comparison.png`: rendered page 1 of `01_contract-docx.pdf` and `01_contract-hwpx.pdf` from `UPLOAD_SPACING_COMPARE_PDFS(1).zip`, Windows QA dated **2026-10-18**. These were produced from the spacing/margin corrected QA run and approved as acceptable with documented layout differences.
- `longform-word-page2.png`, `longform-hancom-page2.png`, `docx-hwpx-longform-comparison.png`: rendered page 2 of `24_long_form-docx.pdf` and `24_long_form-hwpx.pdf` from same results ZIP, **2026-10-18**.
- `complex-tables-docx.png`, `complex-tables-hwpx.png`, `complex-tables-comparison.png`: rendered page 1 of `23_complex_tables-*.pdf` in `PyWPDoc_시각검수_64문서_20261018.zip`, QA **2026-10-17** (prior to 2026-10-18 spacing/margin revalidation).

Rendering used PyMuPDF on existing PDFs at 1.75x; composite images add labels and margins and crop only the unused lower white space of the first-page previews. No printed source text was retouched or removed. Original PDF output and hashes belong to the offline Windows QA results and are **not included in the public GitHub repository**. UI chrome is not depicted. QA marker strings remain visible to preserve evidence integrity.

Actual Word/Hancom view may vary with software version, fonts, page properties, and platform. Do not represent these renders as exact cross-format visual parity.

---

# README v3 screenshot provenance / QA integrity

This proposed README uses **actual file-derived output, not recreated document text**. The labels, neutral panels, cropping, and resizing were added for clarity. No document text, tracked revision marks, or QA image content was repainted.

| File | Source | Renderer and verification | Transform |
| --- | --- | --- | --- |
| `track-changes-three-versions.png` | Handoff `PyWPDoc_TrackChanges_Before_After_Tracked.zip`: `03_revision_before.docx`, `04_revision_after.docx`, `05_tracked_review.docx`; Word-exported `05_tracked_review.pdf` uploaded by user | Source before/after: LibreOffice PDF-page render from actual DOCX (2026-10-20); tracked: Microsoft Word → Save as PDF (user provided, 2026-10-20). | Crop middle document lines; arrange 3 panels; **some Word-exported inline changes overlap visually**. Not a screenshot of live Word UI. |
| `table-repeat-before-after.png` | Actual output files in `examples/table_repeat/`, generated using bundled PyWPDoc library package | DOCX source/result saved and reopened and rendered to PDF with LibreOffice; HWPX source/result saved and reopened and their table rows checked programmatically. | Crop document top; arrange side-by-side; no Windows native Word/Hancom screenshot for this newly generated example. |
| `docx-hwpx-table-excerpts.png` | `docx-hwpx-contract-comparison.png` from previous Windows QA (`2026-10-18`, see full source `docx-hwpx-original-qa.png`) | Real Microsoft Word and Hancom PDF-page renders, existing historical QA | **Table-only content crops**, independently selected around same table; no retouch, no vertical stretching; source layout differences still exist. |
| `docx-hwpx-original-qa.png` | Handoff `06_Historical_Images/docx-hwpx-contract-comparison.png`, original from `UPLOAD_SPACING_COMPARE_PDFS(1).zip` QA 2026-10-18 | Existing Word/Hancom native PDF render composite | Unmodified copy for audit. |

## Files and limitations

- `examples/track_changes/{03_revision_before,04_revision_after,05_tracked_review}.docx` are byte-for-byte copies of the original 16-paragraph sample files from the handoff. Matching HWPX files are included for independent inspection.
- `examples/track_changes/05_tracked_review_word_export.pdf` is the provided Word PDF export. Red inline marks can overlap, which is a limitation of that display, not an edit made to the screenshot.
- `examples/table_repeat/generate.py` reproduces source and filled documents for **both** DOCX and HWPX; executed in this handoff environment, and both resulting files were reopened with PyWPDoc to assert three physical data rows.
- The table-only DOCX/HWPX crop is a **content comparison**, not a claim of identical layout, margins, page breaks, or seamless DOCX↔HWPX conversion.
- `pip install pywpdoc` in the README is intended for the planned 0.44.0 release; this handoff has not published or merged anything.
