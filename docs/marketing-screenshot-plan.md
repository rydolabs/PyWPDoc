# PyWPDoc PyPI / GitHub README — Screenshot Direction

The package's long description is **the English `README.md`** (`pyproject.toml` → `[project].readme`). GitHub and PyPI will display the same main product narrative only when a **new PyPI version** is published. Do not attempt to edit already published `0.44.0rc1` assets.

## Product promise and first-screen reading path

**Reviewable Word document automation in Python.**

The user should understand in approximately five seconds:

1. `pip install pywpdoc` (0.44.0+ only, and only once it is published).
2. `before.compare(after)` yields a **separate native-tracked Word document** (supported changes).
3. `check_template()` validates missing tags **before rendering**.
4. `preview_replace()` inspects edits **before applying them**.

Mention HWPX **after** the Word use case, as an optional format capability valuable in Korea.

**Order on the landing page:** title → installation → 3-line before/after proof + native tracked Word screenshot → 6-line compare Python example → template preflight example/real before-after screenshot → replacement preview → quickstart → API links → scope/provenance/older native QA screenshots.

## The primary visual: one story, not three full documents

Name after final approval: `docs/assets/readme/tracked-changes-hero.png`.

Use **one static, legible composite of actual source material** in two rows:

- **Top row (approximately 35%):** `BEFORE` and `AFTER` in equal-width cards. Crop real Word PDF-page exports of the synthetic 16-paragraph procurement agreement down to **only 3–4 aligned lines**: price `10,000 → 12,500`, delivery `November 15 → December 1`, support `3 → 6 months`, optionally approval status. Preserve punctuation and dates exactly as printed. Do not replace genuine source text with new typography, or imply we support irrelevant structural changes.
- **Bottom row (approximately 65%):** **one wide Word native Review → All Markup screenshot**, cropped to the same changed paragraphs. Keep the **visible inserted/deleted formatting** and optionally the Word 'All Markup' control in frame so a viewer can distinguish this from plain edited text. The screenshot must be produced from the actual generated `05_tracked_review.docx`.
- Outside the screenshots, add **short neutral labels** `BEFORE`, `AFTER`, `WORD TRACKED REVIEW`, and an honest caption `13 text-edited paragraphs · same document structure · native Word Track Changes`.
- Show just **three representative edits** in the hero; link to the full document/runner for all 13. Do **not** scale down an entire Word page or show 13 unreadable lines.

**Target export:** 1200–1400 px wide, roughly 700–950 px high, PNG or lossless equivalent. Verify readability when downscaled to **~680 px width (PyPI)** and when viewed on a phone; keep final text comfortably legible, not miniature. Do not assume arbitrary CSS positioning in Markdown/PyPI.

**Status:** CURRENTLY BLOCKED for the hero. A real Word-generated PDF from the earlier single-line case overprinted redline glyphs (`10,000 → 12,000` looked like `102,000`). We have a new 16-paragraph/13-edited native-tracking DOCX, and the source generator passed API CI, but do **not** represent an artificially reconstructed redline as a real Word screenshot. Request a screenshot from an open Word window using **Review → Display for Review → All Markup**, crop only after visual sign-off.

## Secondary visual: template preflight and render

Final filename: `docs/assets/readme/template-preflight-before-after.png`.

There is already an **authentic Word COM PDF-page composite**, returned by user on 2026-10-19: `template_before_after.png`. It displays:

- `Customer: {{customer.name}}` → `Customer: Acme Corp`
- `Agreement ID: {{agreement.id}}` → `Agreement ID: SAMPLE-2026-001`
- `Amount: USD {{agreement.amount}}` → `Amount: USD 12,000`

Crop to the text-only region; keep labels outside the actual Word source crops. Pair with `check_template()` and `render_template()` example. Clearly distinguish read-only validation from actual rendering; a screenshot of filled text **does not** independently prove preflight behavior. Provenance: user-provided `SHOWCASE_RESULTS_20261019T134822Z_138f18.zip`, Word COM export, 7/7 Word PDF runs PASS; original source and checksum report were reviewed in conversation.

## Third visual: replacement preview (optional, not first screen)

Final filename: `docs/assets/readme/replacement-preview-before-after.png`.

User's original genuine Word COM PDF composite shows `Status: Draft` → `Status: Approved`; it represents **post-preview** `replace_text()` results. Do not claim the PNG directly visualizes the read-only `preview_replace()` report. Prefer to show the small Python API snippet and count/JSON report before the PNG.

## What stays out of the above-the-fold view

Full-page Word contracts, complex table layouts, DOCX/HWPX comparison and extensive QA evidence should be linked under 'More screenshots' or 'Compatibility', **below** the three global Word automation use cases. Keep the format comparison for Korean-market visitors, not as the main global conversion claim.

## Provenance and release gate

- Never fabricate a Word screenshot, silently recolor revisions, erase unsupported results or create fake GUI chrome.
- Do not call synthetic offline DOCX rendering a Word COM native visual test.
- Keep each original/source export and SHA256 manifest with the QA record. Cite Word version, OS, date, and package version when captured.
- Make sure generated screenshots show just synthetic business data and no actual user/customer information.
- Add approved PNG assets and an attribution entry in `docs/assets/readme/PROVENANCE.md`, then update both READMEs to point at those exact approved files.
- Run the **latest PR branch CI** with 10/10 jobs; keep PR Draft until screenshot and release-review decisions.
- Merge and publish **only with separate user approval** and CI/appropriate native QA. GitHub source updates do not retroactively update PyPI `0.44.0rc1`.

## Links for the PyPI card and README

- [Document API](https://rydolabs.github.io/PyWPDoc/reference/document/)
- [Tracked Changes](https://rydolabs.github.io/PyWPDoc/guide/compare/)
- [Templates](https://rydolabs.github.io/PyWPDoc/guide/templates/)
- [Text Preview & Replace](https://rydolabs.github.io/PyWPDoc/guide/search-replace/)
- [Quickstart](https://rydolabs.github.io/PyWPDoc/getting-started/quickstart/)
