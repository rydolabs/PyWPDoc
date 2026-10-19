"""Validate authored API manual links, tested snippets, and public signatures.

Runs offline; does not create a site, touch Git, or publish anything.
"""
from __future__ import annotations
import inspect
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TESTED_EXAMPLES = {
    "quickstart", "search_replace", "template", "pictures", "compare", "sections",
    "agent_tasks",
}


def main() -> int:
    issues: list[str] = []
    mkdocs = ROOT / "mkdocs.yml"
    if not mkdocs.is_file():
        issues.append("missing mkdocs.yml")
    for name in sorted(TESTED_EXAMPLES):
        if not (ROOT / "examples" / "manual" / f"{name}.py").is_file():
            issues.append(f"missing tested example: {name}")
    for document in sorted(DOCS.rglob("*.md")):
        text = document.read_text(encoding="utf-8")
        for filename in re.findall(r'--8<--\s+"([^"]+)"', text):
            if not (ROOT / filename).is_file():
                issues.append(f"{document.relative_to(ROOT)}: broken snippet {filename}")
        for link in re.findall(r'(?<!\!)\[[^\]]+\]\(([^)]+)\)', text):
            target = link.split("#", 1)[0].strip()
            if not target or target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            if not (document.parent / target).is_file():
                issues.append(f"{document.relative_to(ROOT)}: broken link {link}")
    sys.path.insert(0, str(ROOT / "src"))
    from pywpdoc import Document
    facade = Document
    for method in ("add_paragraph", "add_table", "save", "add_picture", "add_section"):
        if method not in vars(facade):
            issues.append(f"facade method not explicit: {method}")
    if list(inspect.signature(facade.add_section).parameters) != ["self"]:
        issues.append("portable add_section signature changed; docs require refresh")
    if issues:
        print("Manual/API contract FAILED:")
        print("\n".join(f" - {issue}" for issue in issues))
        return 1
    print(f"Manual/API contract OK: {len(list(DOCS.rglob('*.md')))} Markdown files, {len(TESTED_EXAMPLES)} executable examples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
