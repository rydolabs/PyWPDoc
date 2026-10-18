# Test evidence and boundaries

**2026-10-18 Windows native validation**: previous reviewed product build, 24 synthetic business scenarios generated in DOCX and HWPX (48 source documents), 48/48 native open/save and 48/48 PDF exports. Native security module reported registered for Hancom. This evidence predates `0.44.0rc1` project reorganization, so does not automatically validate its Windows installer, COM integration, or visual rendering.

**Private source fixture** `tests/fixtures/original_notice.hwpx` is not publicly redistributed, and some historical regressions require it. `scripts/run_public_tests.py` lists exclusions precisely; skipped tests are not passes. Stable regression test node IDs and source-reproduction manifests are preserved under `tests/`.

**QA screenshots** in `docs/assets/readme/` derive from actual Windows PDFs. Their source bundle is retained outside the public GitHub tree. See `PROVENANCE.md` in that directory.

See `tests/README.md` for the portable test command, native test requirements, and layout checking notes. New release candidates require *new* Word/Hancom validation before claiming native acceptance.
