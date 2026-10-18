## 0.44.0rc1 — release structure candidate (not published)

- Consolidate product implementation under `src/pywpdoc/`, with internal `_engine`; pre-release legacy import shims are deliberately omitted.
- Consolidate deterministic business QA, Windows COM validation tools, and historical synthetic fixtures under `tests/`.
- Introduce authentic native-rendered README image assets and unified README metadata for GitHub/PyPI.
- Prepare CI and manual-approval PyPI Trusted Publishing workflows.
- No intentional changes to business document algorithms. Windows native retest required after restructure.
- Add explicit portable `pywpdoc.Document` methods, optional image-format sniffing, and a documented no-argument `add_section` contract without changing the backend engines.
- Introduce bilingual MkDocs API manual, tested DOCX/HWPX examples, API contract tests, and CI docs-build gate (site not yet published).

# 0.43.1rc2 — Untracked-format safety and CI candidate (2026-10-15)

- `compare(everywhere=False)` now rejects untracked DOCX table-border, cell-border, shading, merge and geometry changes rather than silently accepting them.
- Body-only compare also checks DOCX drawing appearance/payload, and native HWPX table geometry and image data for out-of-scope changes.
- Public source's default `pytest` skips the explicitly declared private fixture cases when the licensed source fixture is absent; public Actions still use the narrower published CI selector.
- Windows native Actions and QA launchers select and validate the current wheel version instead of assuming 0.43.0.
- Native Microsoft Word / Hancom 2020 verification of this release candidate is pending.

# 0.43.1rc1 — Safety stabilization candidate (2026-10-15)

- Restore native DOCX package when rebuilding DOCX to DOCX; reject missing payloads.
- Reject unsupported DOCX to HWPX rebuild explicitly.
- Reject body-only comparisons when excluded table/story content has changed.
- Preflight strict template rendering before any changes.
- Cache native run-to-paragraph linkage to remove quadratic HWPX text replacement traversal.
- Avoid exact sub-line-height Word table rows when rebuilding simple HWPX tables.
- 709 existing tests + 16 new defect regressions passed locally (725 total). Windows GUI revalidation pending.

## v0.43.0 — 보수적 정규식 검색·치환 (2026-10-13)

- Added `Document.find_regex(pattern, *, everywhere=True, flags=0, count=-1)` and `Document.replace_regex(pattern, replacement, *, everywhere=True, flags=0, count=-1)` for DOCX/HWPX.
- Reused core `TextMap`, safe-boundary checks, paragraph traversal and structure-preserving `replace_text_range` without changing existing literal APIs or native Track Changes writers.
- Python `re` capture groups/backreference expansion; unsupported zero-width matches and invalid replacements are rejected before mutation, opaque-boundary matches are skipped.
- Regression tests: 623/623 (588 preexisting + 35 new). See `REGEX_FIND_REPLACE_V0430_KO.md` and `QA_REGEX_V0430.md`.

## v0.42.0 — 검색·치환 미리보기 및 JSON 변경 보고 (2026-10-13)

- Added `Document.preview_replace(search, replacement, *, everywhere=True, case_sensitive=True, count=-1)` to inspect literal replacement candidates without modifying DOCX/HWPX.
- Uses exactly the existing replace matcher and text traversal; supports split runs, safe hyperlink joins, global replacement limits, case folding and body-only filtering.
- Added immutable `ReplacementPreviewReport` / `ReplacementPreviewMatch`, `to_dict()`, and `to_json()` (Korean Unicode preserved).
- Reports original zero-based logical paragraph offsets and before/after logical text; opaque/native non-text elements are not reconstituted in this preview.
- Matching across unsafe field/revision/content-control boundaries remains excluded. Successful preview does not promise future writer success if document or backend changes.
- Existing `replace_text()`, `find()`, `render_template()`, and Track Changes writers unchanged.
- QA: `REPLACE_PREVIEW_V0420_KO.md` and `tests/test_replace_preview_v0420.py`.

## v0.41.0 — 템플릿 사전 검사 (2026-10-13)

- `Document.check_template()` 추가 (DOCX/HWPX 공통, 읽기 전용).
- 누락된 활성 변수·섹션/반복 문맥·템플릿 문법·불안전 텍스트 경계 검사.
- 구조적 반복 행 문맥은 기존 렌더러의 행 탐지 로직 재사용.
- `TemplateCheckReport`/`TemplateCheckIssue` 및 `to_dict()` 제공.
- 기존 `render_template()` 구현 및 인수는 변경 없음.
- 테스트/제한 범위: `TEMPLATE_PREFLIGHT_V0410_KO.md`.

# Changelog

## 0.40.0 (QA batch diagnostics add-on; no product version bump)

- Added a single-file Hancom 2020 native batch probe with ten isolated text/format/structure cases, one-edit-session instructions, per-case validation and issue reports.
- Added `quality/run_batch_checks.py` to run all pytest cases and the native diagnostic gate independently; pytest failure never stops native analysis.
- Linked text marker TcIds and format anchor IDs to matching header change IDs to prevent other scenarios' revisions from producing false passes.
- Kept HWPX structural Track Changes fail-closed; case-level structural observations are never a native writer enablement signal.


- Record Hancom 2020 confirmation for the v0.39.0 semantic named-style identity QA.
- Keep HWPX table-row structural Track Changes fail-closed because no verified `hp:tr` revision anchor exists in current native evidence.
- Add a read-only HWPX row-tracking analyzer that compares package entries, header TrackChange records, inline marker scope, paragraph/run anchors, table row matrices, and possible history/version-log parts.
- Add isolated native Hancom 2020 row-insert and row-delete probe fixtures plus expected-final references and machine-readable manifests.
- Enrich `compare-hwpx-table-row-track-unsupported` context with the verified TrackChange type set and public marker scope so callers can distinguish an intentional evidence boundary from a generic unsupported feature.

## 0.39.0

- Record Hancom 2020 GUI confirmation for v0.38.0 embedded image-bullet Accept/Reject behavior.
- Compare HWPX paragraph named-style identity semantically instead of comparing raw header-local `styleIDRef` numbers.
- Allow equivalent named styles with different local ids across unrelated documents to participate in ordinary ParaShape tracking.
- Detect the inverse collision where equal numeric style ids resolve to different style identities and fail closed rather than silently missing the change.
- Resolve `nextStyleIDRef` by target style identity so self/next-style local id differences do not create false revisions.
- Keep actual named-style identity changes fail-closed; no unsupported style-identity TrackChange record is synthesized.
- Add `qa_hwpx_style_identity_v0390` and release-QA hash/structure checks.

## 0.38.0

- Added cross-document HWPX image-bullet import/remap for ParaShape Track Changes.
- Image bullets now carry their OPF manifest entry and embedded `BinData` payload into the NEW-based review clone.
- Resolved bullet comparison includes binary payload identity, preventing equal local `binaryItemIDRef` values from masking different images.
- Added payload deduplication when the OLD image already exists in the target package.
- Extended validation to reject dangling image-bullet manifest and BinData references.
- Kept external/non-embedded image dependencies and named-style identity changes fail-closed.

## 0.37.0

- Hancom 2020 GUI confirmation recorded for v0.36.0 HWPX ParaShape tracking.
- Added cross-document ParaShape resource import/remap for tabPr, paragraph borderFill, numbering, text bullets, and nested paraHead charPr dependencies.
- Paragraph-format comparison now resolves header-local resource meaning instead of comparing numeric ids across documents.
- Added validator checks for ParaShape dependency references.
- Image bullets and named-style identity changes remain fail-closed.

## 0.36.0

- HWPX ParaShape Track Changes candidate: `trackChange@type="ParaShape"` + OLD `parashapeID` + changed `hp:p@paraTcId`.
- Grounded the paragraph anchor/header contract in Hancom's public OWPML model.
- Fixed ParaShape-only revision plans being skipped by an early-return condition.
- Added alignment, line-spacing, mixed-format, overlap, named-style, and missing-OLD-paraPr safety coverage.
- Added `qa_hwpx_parashape_v0360` and `QA_INDEX_V0360.json`; Hancom 2020 GUI Accept/Reject remains pending.

## 0.35.0 - HWPX cross-document CharShape resource import/remap

- Extend native-backed HWPX CharShape Track Changes across independently-authored documents whose OLD character resources are absent from NEW.
- Resolve `charPr` semantics through referenced font definitions and border fills instead of comparing raw numeric IDs only.
- Import/deduplicate OLD fonts per language block and self-contained border fills, remap `fontRef`/`borderFillIDRef`, then author `trackChange@charshapeID` against the remapped OLD shape.
- Keep the NEW input immutable; imports are applied only to the NEW-derived review clone.
- Add validator checks for dangling `charPr` font and border-fill references.
- Fail closed for embedded-font payloads or unverified external border-fill dependencies.
- Preserve the Hancom 2020-native CharShape anchor contract (`run@paraTcId`) and keep ParaShape tracking fail-closed.
- v0.34.4 Hancom 2020 GUI display + Accept/Reject QA was user-confirmed before this increment.

## 0.34.4 - Hancom 2020-native CharShape tracking candidate

- Re-enabled HWPX **character-format** Track Changes from a real Hancom 2020-authored oracle supplied during GUI QA.
- Match Hancom 2020 native authoring: `trackChange(type="CharShape", charshapeID=<old charPr>)` plus `hp:run@paraTcId=<change id>`.
- Preserve `trackchageConfig` tracking bit behavior (`flags |= 1`) and native author metadata.
- Character-format-only and mixed text + character-format comparisons are enabled again.
- Keep HWPX paragraph-format (`ParaShape`) Track Changes fail-closed pending an independent native ParaShape oracle.
- Add a machine-readable native-oracle contract receipt and release QA with identical OLD/NEW/TRACKED text covering font, bold, and size changes.
- Full regression: 452/452 passed before packaging.

## 0.34.3

- Correct release QA packaging so unrelated HWPX formatting OLD/NEW and text TRACKED artifacts cannot be presented as one scenario.
- Add `scenario_id` manifests, SHA-256 checks, and `QA_INDEX_V0343.json`.
- Keep HWPX formatting Track Changes fail-closed pending a native Hancom-authored fixture.
- Preserve supported HWPX text Track Changes, paragraph structural tracking, DOCX formatting revisions, and v0.34.1 Hancom 2020 compatibility fixes.

## 0.34.2 - HWPX formatting Track Changes safety rollback

- Retracted HWPX CharShape/ParaShape Track Changes from the supported surface after Hancom 2020 GUI QA showed that the synthesized revisions were not displayed as formatting changes.
- HWPX character/paragraph formatting differences now fail closed with `compare-hwpx-format-track-unsupported` before any review metadata is authored.
- Mixed HWPX text + formatting comparisons also fail before partial review output is produced.
- HWPX text revisions and whole-paragraph structural revisions remain supported; DOCX formatting revisions remain supported.
- Kept the v0.34.1 Hancom 2020 creation profile and font-size unit fixes.
- Full regression: 439/439 passed.

## 0.34.1 - Hancom 2020 creation compatibility

- Fixed HWPX font-size normalization for foreign EMU-backed length objects such as `docx.shared.Pt`; 14pt now serializes as `charPr@height="1400"`.
- Added validation for invalid/non-positive HWPX font-size inputs.
- Added a Hancom 2020-targeted real-authored blank HWPX skeleton and made it the default for new HWPX documents.
- Added `compatibility="latest"` to explicitly retain the previous 13.x / xmlVersion 1.5 creation skeleton.
- Preserved `version.xml` byte-for-byte when opening/editing existing HWPX documents and when producing compare output from NEW.
- Preserved the existing header/footer style-ID contract while using the 2020-targeted skeleton.
- Full regression: 439/439 passed.

## 0.34.0 - Tracked HWPX formatting comparison

- Added HWPX `CharShape` Track Changes anchored by `hp:run@charTcId`.
- Added HWPX `ParaShape` Track Changes anchored by `hp:p@paraTcId`.
- Kept the current/new shape references in body XML and linked revision metadata to the prior shape definition for reject semantics.
- Added format-only Accept/Reject projection tests and mixed text + format coverage.
- Added fail-closed boundaries for missing prior header definitions, named-style identity changes, and pre-existing format revision anchors.
- Preserved the v0.33.0 baseline; full suite: 431/431 passed.

## 0.33.0 - Tracked DOCX formatting comparison

- Added DOCX run-format Track Changes using native `w:rPrChange` with previous run properties.
- Added DOCX paragraph-format Track Changes using native `w:pPrChange` with previous paragraph properties.
- Added format-aware planning that ignores harmless run fragmentation and splits revisions at both old/new run boundaries.
- Added mixed text + formatting revision coverage and explicit section-format fail-closed behavior.
- Kept HWPX format-only changes fail-closed until a verified native CharShape/ParaShape anchoring contract is available.
- Preserved the v0.32.0 baseline; full suite: 425/425 passed.

## 0.32.0 - Tracked body-paragraph comparison

- Added top-level body block alignment so paragraph insert/delete preserves position around table anchors.
- Added DOCX whole-paragraph Track Changes with revision-marked paragraph content and paragraph marks.
- Added HWPX whole-paragraph insert/delete ranges with `paraend="1"`.
- Added adjacent multi-paragraph, empty-paragraph, table-adjacent, and mixed structural/inline revision coverage.
- Added fail-closed boundaries for unsafe paragraph imports and multi-section structural edits.
- Preserved the v0.31.0 baseline; full suite: 418/418 passed.

## 0.31.0 - Tracked DOCX table-row comparison

- Added backend-neutral table-row revision planning.
- Added native DOCX row insert/delete revisions with `w:trPr/w:ins` and `w:trPr/w:del`.
- Kept HWPX row structural Track Changes fail-closed because no verified row-level OWPML grammar was established.
- Added Accept-All => new / Reject-All => old structural projection tests.
- Preserved the v0.30.0 baseline; full suite: 399/399 passed.

## 0.30.0 - Structural table-row capability and repetition

- Added backend-neutral structural table traversal and minimal row
  clone/insert/remove contracts.
- Added DOCX row cloning with fresh drawing identities while preserving native
  row/cell structure, horizontal merges, nested tables, formatting, and media
  relationships.
- Added HWPX row cloning with refreshed paragraph/object identities, stale
  layout-cache removal, preserved nested structure/media references, and native
  merge-aware removal.
- Added `render_template(..., sections=True, table_rows=True)` for an outer
  Mustache section that wraps an entire table row.
- Added sequence repetition, inverted row conditions, item context with parent
  fallback, fragmented markers, nested-table content rendering, and single-pass
  protection for template-like data values.
- Vertical merge ambiguity and emptying a table fail closed.
- `everywhere=False` retains the historical no-table template scope.
- Preserved all v0.29.0 baselines; full suite: 388/388 passed.

## 0.29.0 - Tracked text comparison

- Added `Document.compare(new, author=..., date=..., everywhere=True)` as an
  isolated high-level comparison feature.
- Added backend-neutral `RevisionPlan`, `ParagraphRevision`, and `TextEdit`
  models; alignment/diff policy remains outside DOCX/HWPX XML writers.
- Added DOCX native revision output using `w:ins`, `w:del`, `w:delText`,
  reviewer/date metadata, and `w:trackRevisions`.
- Added HWPX native revision output using insert/delete begin/end markers,
  `trackChanges`, `trackChangeAuthors`, and track-change configuration metadata.
- Comparison is non-destructive and writes revisions into a cloned copy of the
  newer document.
- Structural paragraph/table-row insert/delete and unsafe complex inline
  structures fail closed in this increment.
- Added Accept->new / Reject->old projection tests, table-cell comparison,
  metadata, no-op-copy, mismatch, and fail-closed regressions for both formats.
- Preserved all v0.28.2 baselines; full suite: 355/355 passed.
- Microsoft Word/Hancom GUI review of generated tracked-change files remains an
  explicit external release QA item.

## 0.25.0 - Logicless template v1

- Added `pywpdoc.Document.render_template()` as a third isolated high-level
  feature family.
- Added independent template `parser`, `context`, `renderer`, and `api` modules.
- Added `{{name}}`, dotted `{{customer.name}}`, current-context resolution,
  run-split tags, body/table/header/footer traversal, and explicit missing-value
  policies (`keep`, `empty`, `error`).
- Template does not import `find` or `replace`; it reuses only lower-level
  `pywpdoc.core.text` mapping/traversal/mutation primitives.
- Mustache control tags are explicitly rejected in v1 rather than silently
  mis-rendered; sections/loops/table-row repetition are reserved for later
  independent submodules.
- Preserved immutable v0.21.5 baseline; full suite is 284/284.

## 0.24.0 - Isolated high-level replace feature

- Added `pywpdoc.Document.replace_text()` as a thin facade over an independent
  `pywpdoc.features.replace` module.
- Extracted literal-span matching into `pywpdoc.core.text.match`, shared by
  `find` and `replace` without sibling-feature imports.
- Added `pywpdoc.core.text.mutation` for backend-neutral logical range mutation.
- Added architecture tests prohibiting sibling feature dependencies.
- Added real-document replacement isolation regression for HWPX and DOCX.
- Preserved immutable v0.21.5 baseline; full suite is 268/268.

# v0.21.4

- Fixed DOCX snapshot cell-border serialization. HWPX native cell borders now replace the provisional Word borders instead of appending duplicate `w:top`/`w:left`/`w:bottom`/`w:right` nodes.
- This fixes renderer-dependent missing table edges, including the lower outline of the application table in the school-notice Common rebuild sample.
- Added a regression asserting exactly one OOXML node per cell edge and preserving the HWPX 0.5 mm bottom border as `w:bottom w:sz="11"`.
- Full regression: 223/223 passed.

# 0.21.2
- Roll back the v0.21.0/v0.21.1 rich header/footer auto-reservation heuristic. HWPX save no longer estimates story height, rewrites header/footer areas, or injects a 0.5 mm clearance.
- Keep the verified section/page geometry fix that invalidates stale `hp:linesegarray` caches after page size, orientation, or margin changes.
- Keep the earlier rich-story `hp:subList/@textHeight="0"` policy and logical/control story synchronization.
- Add a regression proving that a rich header preserves the caller-authored native header area instead of silently auto-fitting it.
- Full regression: 219/219 passed.
- Add a reverse-rebuild diagnostic for a real Hancom school-notice HWPX: page geometry, top-level block order, 3 tables, 3 rectangles, and 1 picture reconstruct semantically; the rebuilt document intentionally carries 0 persisted `linesegarray` caches versus 52 in the Hancom source, forcing Hancom to re-layout on open.

# 0.21.1
- Fix v0.21.0 rich-header over-reservation: HWPX now keeps the caller-authored header/footer area as the baseline and adds only the rich-story overflow beyond the corresponding page margin, plus a minimal 0.5 mm clearance.
- Preserve v0.21 stale `hp:linesegarray` invalidation.
- Add regressions for DOCX-like compact header/body spacing and repeated-save idempotency.

# 0.21.0

- Fix native HWPX section-geometry mutation to invalidate stale `hp:linesegarray` paragraph layout caches instead of carrying coordinates from the bundled skeleton into a changed page box.
- Add native rich header/footer extent calculation from paragraph line metrics, table row/cell content, and cell margins.
- Rich HWPX stories now reserve enough native header/footer area before save; final table-cell edits are included in the calculation.
- Save-time normalization also upgrades older rich stories with a fixed `textHeight` to the content-sized form while preserving simple one-line stories.
- Keep the fix entirely below the Common facade; DOCX behavior is unchanged.
- Add 3 engine regressions; full regression is 220/220 passed.
- Real Hancom GUI verification remains required before declaring visual parity with DOCX.

# 0.20.0

- Split document core-properties ownership into backend-local `hwpx/metadata.py` and `docx/metadata.py` modules.
- Standalone HWPX and DOCX backends now return backend-owned `CoreProperties` objects while preserving `.native` escape hatches.
- Verify shared string metadata fields: title, author, subject, comments, keywords, language, and last-modified-by.
- Normalize shared created/modified datetime semantics to UTC-naive second precision inside each backend, not Common.
- Add 10 metadata isolation/roundtrip regressions; full regression is 217/217 passed.

# 0.19.0

- Split picture/media ownership into backend-local `hwpx/media.py` and `docx/media.py` modules.
- Standalone HWPX and DOCX backends now return backend-owned `Picture` objects from `add_picture()` and `pictures`.
- Add a verified shared picture subset: physical width/height/size, resize, embedded bytes, save/reopen persistence.
- Keep HWPX BinData/manifest/package behavior in the native HWPX engine; the standalone media module is an adapter rather than a duplicate implementation.
- Keep DOCX HWPUNIT/core-length to EMU translation inside `docx/media.py`; Common remains delegation-only.
- Fail closed for DOCX floating-picture requests (`treat_as_char=False`) until a verified anchor mapping exists.
- Add 11 media isolation/contract regressions; full regression is 207/207 passed.

# 0.18.0

- Lower HWPX Section/Header/Footer behavior beneath the standalone wrappers.
- Make `hwpx/section.py` and `hwpx/story.py` thin adapters only.
- Add native HWPX policy modules `_hwpx_section.py`, `_hwpx_story.py`, `_hwpx_table.py`.
- New HWPX stories use the skeleton's native `Header`/`머리말` style for the initial paragraph.
- `HeaderFooter.text` no longer leaks nested-table cell text; `all_text` preserves recursive expert access.
- Keep story-table width, cell margin, and TOP alignment behavior in the native HWPX layer.
- 194 regression tests pass; original notice remains 12/12 exact rebuild.

# v0.17.0

- Split Section/page setup routing into backend-owned `section.py` modules.
- Split Header/Footer block-story wrappers into backend-owned `story.py` modules.
- Common remains delegation-only and receives no page geometry, story mutation, or header-table sizing logic.
- DOCX even-page story access enables the required Word even/odd header setting inside the DOCX backend.
- Header tables default to section content width independently in both backends.
- Added section/story module isolation, persisted geometry, story block, add-section, support-gap, and HWPX mirror regressions.
- Final regression: 186/186 passed; original notice 12/12 exact rebuild.

# v0.16.0

- Split standalone style ownership into `docx/styles.py` and `hwpx/styles.py`.
- `Styles`, `Style`, `StyleFont`, and `StyleParagraphFormat` are backend-owned public types.
- Added backend-local DOCX `clone_from` direct-format copying; Common remains delegation-only.
- Paragraph/Run accept backend Style wrappers with one-way `paragraph -> styles` dependency.
- Added style isolation, clone independence, apply/next/delete, common-delegation, and minimal protocol regressions.
- Final regression: 167/167 passed; original notice 12/12 exact rebuild.

# Changelog


## 0.21.3

- Common에 `Document.rebuild()` / `export_snapshot()` / `rebuild_from()` 구조 보존 경로를 추가했다. Common은 `DocumentSnapshot`만 전달하고 포맷별 export/import는 각 backend가 소유한다.
- HWPX→HWPX `preserve_layout=True`는 native package payload를 보존해 변경 없는 rebuild에서 package part hash가 모두 동일하도록 했다. `hp:linesegarray`를 임의 삭제하지 않는다.
- HWPX→DOCX portable importer를 추가했다. 페이지 geometry, HWPX layout slot, run/paragraph 서식, 표/병합/셀 테두리·채움, 그림, text box를 Word 구조로 변환한다.
- DOCX 변환에서 `lineseg/@spacing`을 paragraph `space-after`로 중복 계산하던 문제를 제거했다. 한 줄 문단은 다음 cached line top을 이용해 measured advance를 유지한다.
- HWPX text box 내부의 borderless positioning grid를 Word에서 별도 nested table로 중복 배치하지 않고 host paragraph/tab 구조로 변환해 fixed slot clipping을 방지한다.
- Common HWPX same-format rebuild package fidelity, HWPX→DOCX reopen, inline positioning-grid flattening 회귀를 추가했다.

## 0.15.0

- Split table ownership inside each independent backend into `table.py` and `table_geometry.py`.
- `backend.py` now composes/delegates table creation instead of owning Table/Row/Column/Cell implementations.
- Keep Common API unchanged and thin; no table geometry or option normalization moved into Common.
- Normalize standalone backend `Row.height`, `Column.width`, and `Cell.width` around shared physical Length semantics.
- DOCX backend column-width setter now synchronizes rendered cell widths (`tcW`) as part of the backend contract, without changing python-docx native behavior.
- Add architecture, geometry, merge, nested-table, vertical-alignment, width, and height regression gates.
- Regression result: 153/153 passed; original notice exact rebuild remains 12/12.

## 0.14.0

- First feature-module isolation pass: split paragraph/run wrappers and text operations into backend-owned `paragraph.py` / `text.py` modules for both DOCX and HWPX.
- Common remains delegation-only; it owns no text replacement or paragraph mutation behavior.
- DOCX document-wide replace traversal moved out of the backend facade into `docx.text`.
- HWPX text operations are routed through a narrow backend boundary while the mature native HWPX engine remains the implementation owner.
- HWPX standalone backend `Paragraph.add_run()` now starts a new unstyled run from the paragraph style instead of leaking direct formatting from the previous sibling run; native expert API behavior remains unchanged.
- Added module dependency gates plus backend-direct replace count/scope/direct-format isolation tests.
- Regression result: 139/139 passed; original notice exact rebuild remains 12/12.

## 0.13.0

- Architecture-only refactor: independent HWPX backend, independent DOCX backend, thin common facade.
- Added backend-neutral `core/` units, enums, errors, defaults, and minimal Protocol contracts.
- Moved cross-run DOCX replace, page/table geometry, cell padding, vertical alignment, and nested-table sizing out of common and into the owning backend.
- Preserved the legacy top-level HWPX expert API and the `common_api.UnifiedDocument` compatibility import.
- Added AST dependency-boundary/geometry-delegation tests and direct standalone backend contract tests.
- Regression result: 128/128 passed; original notice exact rebuild remains 12/12.

## 0.12.3

- Common-created DOCX/HWPX table cells now persist the same default vertical alignment: TOP.
- Fixed the visual mismatch where HWPX native cells defaulted to CENTER while Word rendered missing `w:vAlign` as TOP.
- `UnifiedCell.vertical_alignment` now maps TOP/CENTER/BOTTOM through one python-docx-shaped enum for both backends.
- Common proxy setters now honor wrapper properties before falling through to native objects.
- Persisted-XML cross-format tests now verify outer and nested cell vertical alignment in addition to physical geometry.
- Regression suite expanded to 104 tests.

## 0.12.2

- Fixed common-API nested table geometry by sizing nested tables to the parent cell content box rather than the raw cell width.
- Normalized common-created table cell padding to 1.8 mm horizontal and 0.5 mm vertical for both HWPX and DOCX.
- Strengthened cross-format geometry tests to inspect persisted parent cell width, padding, content-box width, and nested table width.

## 0.12.1

- Common API preview geometry parity hotfix.
- `UnifiedDocument.new()` now normalizes new DOCX/HWPX documents to the same A4 page and margin geometry; opened documents are never rewritten.
- Common top-level `add_table()` now uses the full current body width when width is omitted, matching python-docx semantics instead of leaking the HWPX native 1-inch-per-column default.
- Added persisted-XML cross-format geometry contract tests for page, margins, body width, table width, column widths, and nested-table width with 0.05 mm tolerance.
- Regression suite expanded to 102 tests.


## 0.12.0

- HWPX v1.0 release-candidate stabilization.
- Targeted edits preserve unrelated package-part bytes rather than reserializing unchanged XML.
- Paragraph-style assignment uses generic charPr 3-way rebase so direct run formatting survives style changes.
- `Paragraph.style = None` returns to verified default paragraph style.
- `Run.clear()` invalidates stale line-layout cache.
- Structured public error families: `HwpxValueError`, `HwpxStateError`, `HwpxUnsupportedError`; validation reports are serializable.
- Experimental `python_hwpx_next.common_api.UnifiedDocument` backend-boundary preview for DOCX/HWPX.
- Automatic regression expanded to 99 tests: 71 HWPX, 20 native cross-format, 8 common-preview.


## 0.11.0

- v1.0 전 core-semantics 안정화 릴리스.
- `Paragraph.replace()` 추가: 여러 run/hyperlink 경계를 넘는 structure-preserving replace.
- `Document.replace(..., everywhere=True)` 추가: body/table/shape/header/footer/note semantic stories를 대상으로 하고 mirrored header/footer 중복 편집을 방지하며 memo body는 보존.
- visible Run/Hyperlink/tab/line-break 변경 시 stale `hp:linesegarray` 제거.
- `Document.paragraphs`를 python-docx 의미로 정정: HWPX 내부 secPr carrier 및 table-only wrapper를 숨김.
- `Row.cells`를 python-docx처럼 logical grid cells로 정정. HWPX physical XML cells는 `Row.physical_cells` escape hatch로 분리.
- `HwpxError` / `HwpxValidationError` 추가. validation failure는 기존 `ValueError` 호환을 유지하면서 code/report를 노출.
- `python-docx>=1.2,<2`를 test extra에 추가하고 `tests/test_cross_format_contract.py` 도입.
- HWPX/DOCX 양쪽에서 mixed text, paragraph insertion, nested table visibility, merged-row logical cells, core properties, section margin/orientation, next paragraph style, cross-run replace 의미론을 병렬 검증.
- 자동 회귀 80개로 확대.

## 0.10.0

- `WD_STYLE_TYPE` 추가. PARAGRAPH/CHARACTER는 지원하고 TABLE/LIST는 검증될 때까지 fail-closed.
- `Styles` iteration을 python-docx 의미로 수정: ID가 아니라 `Style` 객체를 반환.
- `Styles.default()`의 verified paragraph subset 추가.
- `Style.next_paragraph_style`을 HWPX `nextStyleIDRef`에 매핑.
- `Run.style` character-style facade 추가.
- `Paragraph.contains_page_break` 추가.
- section carrier 앞 `insert_paragraph_before()`가 `secPr`와 section-start controls를 새 첫 문단으로 이동하도록 안전화.
- `Row.height` setter 및 vertical-merge-aware logical row height 계산 추가.
- `Cell.merge(other_cell)`, `Cell.add_table()`, `Cell.tables`, `Cell.iter_inner_content()` 추가.
- `Cell.text` setter가 nested table을 포함한 기존 cell story를 제거하고 single paragraph/run으로 교체하도록 python-docx 의미로 수정.
- Header/Footer block container에 `tables`, `add_table()`, `iter_inner_content()` 추가. logical/control mirror equality를 테스트로 고정.
- Header/Footer `add_paragraph(..., style=...)`가 style 인자를 실제 적용하도록 수정.
- header/footer field의 charPr 선택식 우선순위 버그 정리.
- `Document.tables`를 python-docx처럼 body top-level tables로 의미 정정하고 `Document.all_tables` recursive escape hatch 추가.
- 자동 회귀 57개로 확대.

## 0.9.0

- `Table.columns` / `Column.width` 추가.
- 병합 셀을 고려해 열 폭 변경 시 physical cell width와 table width를 함께 동기화.
- 기존 logical column width 추정이 병합 셀을 우선해 잘못된 폭을 읽던 문제 수정; 단일-span 셀을 우선.
- `Cell.vertical_alignment` 및 `WD_CELL_VERTICAL_ALIGNMENT` / `WD_ALIGN_VERTICAL` 추가.
- `Section`에 python-docx-shaped page facade 추가: page width/height, margins, header/footer distance, gutter.
- `Section.orientation` 및 `WD_ORIENT` 추가. HWPX `WIDELY`(portrait) / `NARROWLY`(landscape) mapping 사용.
- `Document.core_properties` 추가: HWPX `Contents/content.hpf`의 검증된 metadata subset 편집.
- `Document.settings` typed foundation 및 `CaretPosition` 추가.
- `Style.delete()`가 dangling style ref를 만들지 않도록 참조 repoint + dense style-id compaction.
- 자동 회귀 49개로 확대.

## 0.8.0

- `Paragraph.text` / `Run.text`가 `\t`, `\n`을 한컴 native mixed-content `hp:tab` / `hp:lineBreak`로 왕복.
- `Paragraph.insert_paragraph_before()` 추가.
- `Paragraph.clear()` / `Run.clear()` section setup 보존 강화.
- `ParagraphFormat.tab_stops`, `TabStops`, `TabStop`, `WD_TAB_ALIGNMENT`, `WD_TAB_LEADER` 추가.
- `Document.iter_inner_content()`와 `Paragraph.iter_inner_content()` 추가.
- `Section.even_page_header/footer`, `odd_page_header/footer` 추가.
- 기본 `Document.save()`를 atomic validated save로 강화.

## 0.22.0 - PyWPDoc namespace architecture milestone

- Added new `pywpdoc` public namespace and distribution name.
- `pywpdoc.Document` is now the high-level format-neutral entry point.
- Added direct backend namespaces `pywpdoc.hwpx` and `pywpdoc.docx`.
- Preserved the verified `python_hwpx_next` v0.21.5 implementation/import path
  during staged migration instead of performing a big-bang internal rename.
- Added explicit common `Document.unwrap()` backend escape hatch.
- Added inert `pywpdoc.features` boundary and dependency architecture tests.
- Added immutable v0.21.5 baseline manifest and real-document regression gates.
- Preserved v0.21.5 DOCX layout-slot `AT_LEAST` fix.
- Legacy baseline: 224/224 passed; full suite: 236/236 passed.
- HWPX->DOCX font visual parity remains a deferred known issue.


## 0.23.0 - First isolated high-level feature

- Added `pywpdoc.Document.find()` as the first high-level feature module.
- Added backend-neutral `TextMap` and text traversal primitives under `pywpdoc.core.text`.
- Added minimal `iter_text_paragraphs()` backend capability for HWPX/DOCX.
- Added a separate read-only DOCX traversal module so search does not create missing header/footer parts.
- Added cross-backend run-boundary, table/header, case/limit, direct-backend, read-only isolation, and architecture tests.
- Preserved the immutable v0.21.5 baseline and all v0.22.0 migration tests.
- Full suite: 249/249 passed.
- HWPX->DOCX font visual parity remains deferred.

## 0.26.0

- added an experimental backend-neutral Drawing placement/transform model;
- added pure Mustache section parsing and structural repeat plan primitives,
  without enabling them in the public v1 renderer;
- added repository-only DOCX OPC/package validation and an external Open XML
  SDK validator adapter for release CI;
- added architecture gates preventing Drawing/template structure from depending
  on concrete backends;
- preserved all existing public behavior and v0.21.5 baseline outputs.

## 0.27.0

- added backend-neutral `TextFragment` layer below `TextMap`;
- DOCX high-level text features now mutate native `w:t` fragments rather than
  replacing whole run text;
- added safe transparent fragmentation across multiple `w:t`, hyperlinks,
  bookmarks, proofing markers, and significant whitespace;
- added hard/opaque boundary tracking for fields, revisions, SDT/content
  controls, tabs/breaks, drawings/objects, math, and unknown semantic nodes;
- `find`/`replace_text` skip matches crossing opaque boundaries;
- `render_template` fails closed with `template-unsafe-text-boundary` for a tag
  crossing such a boundary;
- added DOCX fragmentation torture and save/reopen regression coverage;
- preserved all v0.26 baselines and existing public template syntax.

## 0.28.0

- connected the isolated Mustache section parser to `render_template()` behind
  the backward-compatible `sections=True` opt-in;
- added normal (`#`) and inverted (`^`) inline sections, list repetition,
  nested sections, current-context `{{.}}`, and parent-context fallback;
- reused v0.27 TextFragment/TextMap handling so section markers may span safe
  run/native-text fragmentation;
- kept field/revision/SDT/tab/object boundaries fail-safe;
- kept table-row/block repetition separate from inline text expansion;
- preserved default control-tag fail-closed behavior and all earlier baseline
  tests;
- expanded the full suite to 329 tests.

## 0.28.1

- corrected the v0.28 cross-format section sample to request `Table Grid`
  explicitly on both HWPX and DOCX instead of relying on backend defaults;
- preserved `add_table(style=None)` behavior (DOCX remains `Normal Table`; HWPX
  remains backend-owned);
- added structural regressions proving DOCX `TableGrid` survives template
  rendering/reopen and HWPX uses a solid black borderFill for the explicit grid;
- added repository-only LibreOffice raster QA that verifies the rendered DOCX
  contains visible horizontal and vertical table borders;
- no runtime/document-generation behavior was changed outside the corrected
  comparison fixture; full suite: 333/333 passed.

## 0.28.2

- fixed HWPX all-story paragraph traversal for real Hancom-authored files that
  legally reuse paragraph `id` values (commonly `id="0"`) across unrelated
  table-cell paragraphs;
- replaced broad HWPX paragraph-id deduplication with semantic header/footer
  mirror suppression and explicit memo-field exclusion;
- fixed DOCX physical-cell traversal to use the underlying XML cell node as the
  dedupe identity instead of Python `id(cell._tc)`, which can be reused for
  short-lived lxml/python-docx proxy objects;
- added user-authored Word/Hancom template documents as permanent real-authoring
  regression fixtures;
- added cross-format `find`, `replace_text`, `render_template(sections=True)`,
  and save/reopen coverage for the manually authored fixtures;
- preserved all v0.28.1 baselines; full suite: 340/340 passed.

## 0.31.0

- extended the backend-neutral comparison plan with structural `TableRowRevision`
  entries while keeping v0.29 text revision objects backward-compatible;
- added conservative minimum-cost alignment for top-level body table rows;
- DOCX comparison now emits native row insertion/deletion revisions under
  `w:trPr` using `w:ins` / `w:del`, alongside existing inline text revisions;
- added old/new paragraph index mapping so row insertion/deletion may coexist
  with later cell-text edits in the same table;
- tracked deletion materializes the old DOCX row into the review copy and fails
  closed for relationship-bearing/control-heavy rows or vertical merges until a
  safe cross-package import layer exists;
- HWPX structural row changes fail closed with
  `compare-hwpx-table-row-track-unsupported`; the public OWPML model verified
  for this increment exposes tracked insert/delete ranges inside paragraph text
  but no row-level revision grammar equivalent to DOCX `w:trPr` revisions;
- unchanged-row tables retain the v0.29 paragraph alignment path, preserving
  text comparison behavior for same-structure complex/vertically merged tables;
- added Accept-All/Reject-All row projection regressions for insertions,
  deletions, mixed row/text changes, adjacent multi-row changes, metadata, and
  non-destructive input handling;
- preserved all v0.30.0 regression tests; full suite: **399/399 passed**.
