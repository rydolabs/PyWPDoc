# One-click Windows screenshots for PyWPDoc

**Double-click:** \`tests\showcase\RUN_SCREENSHOTS_WINDOWS.bat\`

## Before you run

- Windows with **Python 3.10+**; Microsoft Word desktop installed and activated for **Word DOCX screenshots**.
- Internet access for a one-time Python dependency install (\`pywpdoc\` is installed from **this extracted repository**, not the older PyPI release).
- For optional Hancom HWPX screenshots: licensed Hancom Office installed and the user-approved **official** \`FilePathCheckerModuleExample\` module registered in \`HKCU\Software\HNC\HwpAutomation\Modules\`. The runner never weakens file security or auto-accepts dialogs.
- **No private documents needed.** Every source document is synthetic English test data.

## Instructions

1. Download [the PR #4 source ZIP](https://github.com/rydolabs/PyWPDoc/archive/refs/heads/docs/global-showcase-stable-0440.zip) and **extract it** to a short path like \`C:\PyWPDoc-showcase\`.
2. Double-click \`tests\showcase\RUN_SCREENSHOTS_WINDOWS.bat\` in the extracted folder.
3. Wait for the console to finish. It creates \`tests\showcase\OUTPUT\SHOWCASE_RESULTS_<timestamp>.zip\`.
4. Upload the **newest ZIP** back to ChatGPT. If Word or Hancom fails, upload the ZIP anyway: it contains a structured status report and any successfully generated samples.

The script creates/uses the local \`tests/showcase/.venv-showcase\` only and keeps each run in its **own** output directory. It never deletes older results, changes personal documents, pushes to GitHub or uploads to PyPI.

### What is inside the ZIP?

- Before/after \`Customer: {{customer.name}}\` template samples in **DOCX and HWPX**.
- Separate before/after documents and a **native Track Changes** document in each format.
- Read-only replacement preview JSON and before/after documents in both formats.
- With Word: \`WORD_*.pdf\` plus \`WORD_*.png\` generated from an actual **Word COM PDF export**, with \`Item=7\` markup export for the tracked file.
- With approved Hancom access: \`HANCOM_*.pdf\` plus \`HANCOM_*.png\`; otherwise an explicit \`SKIP\`.
- \`results.json\`, checksum inventory, errors when present, and \`READ_ME_FIRST.txt\`.

### QA boundaries

PNG files are **real PDF-page renders**, *not* screenshots of application windows. The Word tracked file uses Word's markup export mode, but reviewers must inspect whether revisions are visible in the produced PDF/PNG. Successful file generation alone cannot establish native visual equivalence or a passing stable-release QA.

To generate only the source documents without Windows Office (for CI):

\`\`\`bash
python tests/showcase/run_showcase.py --generate-only --output-root ./tmp-showcase
\`\`\`
