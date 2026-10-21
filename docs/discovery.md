# Search discovery: GitHub Topics and PyPI metadata

Use accurate product terms, not broad unrelated keywords or unsupported claims.

## GitHub About (repository owner: one-time UI setup)

At [rydolabs/PyWPDoc](https://github.com/rydolabs/PyWPDoc), click the **gear icon in About** (upper-right), then enter:

**Description:**

> Python toolkit for Word DOCX templates, safe text editing, and tracked document revisions; also supports Hancom HWPX.

**Website:** \`https://rydolabs.github.io/PyWPDoc/\`

**Topics** (12; all lowercase, hyphens allowed):

\`\`\`text
python
docx
microsoft-word
document-automation
document-templates
document-comparison
tracked-changes
document-review
find-and-replace
word-processing
hwpx
hancom
\`\`\`

Click **Save changes**. GitHub supports up to 20 topics. The repo's name, description and topics all participate in default repository searching; this does **not** guarantee search placement or any GPT/Claude ranking.

**Current metadata as inspected on 2026-10-19:** description was simply \`PyWPDoc\`, Topics were empty, Website was unset. The GitHub connected integration currently cannot edit repository About / Topics, so **the repository owner must apply these three settings directly**. Do not claim they are already set.

## PyPI project metadata

The source's \`pyproject.toml\` defines:

- \`[project].description\`: Word-first package summary, mentioning HWPX as a secondary capability.
- \`[project].keywords\`: DOCX, automation, templates, preflight, safe editing and tracked revision concepts, plus HWPX/Hancom.
- \`[project].classifiers\`: official package-development, operating system, audience, language and word processing classifications.
- \`[project.urls]\`: Documentation, **API Reference**, Template Guide, Tracked Changes, Quickstart and other useful entry points.
- \`readme = {file = "README.md", ...}\`: PyPI project long description renders the English Word-first README, including tested code and real historical Word-document images.

**PyPI has no GitHub-style editable Topics field.** To change keywords/classifiers/description/URLs/README displayed for a version, publish a **new version**; changing GitHub alone does not retroactively replace \`0.44.0rc1\` metadata.

## Release tags vs discovery topics

\`v0.44.0\` is a **Git tag** tied to release source. It is not a search topic. Repository Topics are independent topic labels, and PyPI Keywords are package metadata.

## Honest positioning checklist

Prefer: *Word DOCX templates, preflight validation, read-only text replacement preview, supported tracked changes, automated document review, optional Hancom HWPX*.

Avoid: *lossless DOCX↔HWPX conversion, support for legacy binary .hwp, pixel-identical layout, all structural Track Changes, built-in AI/MCP server*, or any claim of guaranteed search ranking.

[Official API contract](https://rydolabs.github.io/PyWPDoc/reference/document/) · [Template Guide](https://rydolabs.github.io/PyWPDoc/guide/templates/) · [Tracked Changes](https://rydolabs.github.io/PyWPDoc/guide/compare/) · [One-click Windows screenshots](https://github.com/rydolabs/PyWPDoc/tree/main/tests/showcase)
