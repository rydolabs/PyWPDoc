# Known issues — 0.44.0rc1

- `compare(everywhere=False)` is fail-closed for detected changes outside selected body text, including table borders, cell properties/merges and image payload/geometry. It **does not** generate tracked revisions for excluded formatting changes. Complex indirect style changes and unsupported native content may still require separate coverage; do not use as a comprehensive legal/audit change oracle.
- `compare(everywhere=True)` has separate native revision capability boundaries; not every table style, image, or complex structural change can be represented with native tracked changes.
- HWPX -> DOCX `rebuild()` remains experimental; converted paragraphs/tables can be nested in an outer layout table.
- DOCX -> HWPX `rebuild()` remains unsupported and fails closed.
- HWPX native structural row Track Changes remain unsupported/fail-closed.
- Windows Hancom/Word native verification has **not** yet been performed against the refactored 0.44.0rc1 build. Previous 0.43.1rc2 evidence does not establish this release candidate's native PASS.
- Private fixture `tests/fixtures/original_notice.hwpx` is not redistributable in this source package. Plain pytest explicitly skips only tests requiring it if absent; the `run_public_tests.py` policy continues to deselect those tests.

