# Contributing

Thank you for improving PyWPDoc. Please open an issue before extensive feature work so common-API compatibility and DOCX/HWPX backend boundaries can be considered. Submit focused PRs with tests on both formats where applicable. Keep legacy behavior and native change-tracking limitations intact unless supported by reproducible real editor evidence.

**Data hygiene:** Do not include names, phone numbers, customer documents or institution-authored original content in public issues or commits. Use synthetic `.docx`/`.hwpx` files or regenerate minimal samples.

Run `python scripts/run_public_tests.py` before proposing a change. On Windows, run native QA using the repository's manual self-hosted workflow when an appropriately licensed runner is available.
