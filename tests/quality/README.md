# DOCX validation gates

## Mandatory local gate

```bash
python -c "from quality.docx_package import validate_docx_package; print(validate_docx_package('out.docx').issues)"
```

Checks OPC/ZIP/XML/relationship/content-type integrity and is read-only.

## External Open XML SDK gate

Release CI should install/provide a small command-line validator based on the
Microsoft Open XML SDK and set:

```bash
export PYWPDOC_OPENXML_VALIDATOR=/path/to/openxml-validator
```

The command is invoked with the DOCX path as its final argument and must exit 0
for a valid document.  This adapter is intentionally external so PyWPDoc's
runtime wheel does not depend on .NET.

Local development environments without the SDK can run the mandatory package
gate and the existing render/golden regressions, but must not claim that the
Open XML SDK schema gate was executed.

## v0.34.3 release-QA generator

Run `python quality/generate_qa_v0343.py` from the repository root to regenerate
the current HWPX formatting fail-closed scenario, the text-tracking positive
control, per-scenario manifests, and `QA_INDEX_V0343.json`.  The accompanying
release tests verify that unrelated scenario IDs cannot be packaged as one
OLD/NEW/TRACKED trio.


## v0.34.4 current release QA

Run `python quality/generate_qa_v0344.py` from the repository root.

## v0.40.0 HWPX table-row Track Changes probe

Run `python quality/generate_qa_v0400.py` to regenerate the native row-insert/delete probe set.

Use the read-only analyzer on a Hancom-authored unaccepted row-change file:

```bash
python quality/analyze_hwpx_row_tracking.py BASE.hwpx NATIVE_TRACKED.hwpx --expected-final EXPECTED.hwpx --output report.json
```

The tool reports evidence; it does not assert that a row revision encoding is valid. HWPX row-level comparison remains fail-closed until native Accept/Reject semantics are established.
