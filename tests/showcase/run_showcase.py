"""One-click, source-pinned DOCX/HWPX marketing screenshot evidence generator.

Creates synthetic sample documents first. On Windows, exports fresh Word/Hancom
PDFs through applications launched in new COM sessions, then rasterizes PDFs.
A generated PNG is a *PDF page render*, never a fabricated editor screenshot.

Never opens user-supplied files, manipulates security dialogs, or publishes data.
Output is always a new timestamp+UUID directory and an uploadable ZIP.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import traceback
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUTPUT = BASE / "OUTPUT"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create_sources(dest: Path) -> tuple[list[Path], dict]:
    """Use the *installed source checkout* PyWPDoc public API."""
    import pywpdoc
    from pywpdoc import Document

    sources: list[Path] = []
    evidence: dict = {"package_version": pywpdoc.__version__, "scenarios": {}}

    for fmt in ("docx", "hwpx"):
        def save(doc, name: str) -> Path:
            path = dest / f"{name}.{fmt}"
            doc.save(path)
            if not path.is_file() or path.stat().st_size < 100:
                raise RuntimeError(f"Empty document: {path.name}")
            # Reopen generated files before attempting any native rendering.
            Document.open(path)
            sources.append(path)
            return path

        # Template: explicit visible tags, read-only preflight, then substitutions.
        template = Document.new(fmt)
        template.add_paragraph("SERVICE AGREEMENT | TEMPLATE")
        template.add_paragraph("Customer: {{customer.name}}")
        template.add_paragraph("Agreement ID: {{agreement.id}}")
        template.add_paragraph("Amount: USD {{agreement.amount}}")
        save(template, "01_template_before")
        data = {
            "customer": {"name": "Acme Corp"},
            "agreement": {"id": "SAMPLE-2026-001", "amount": "12,000"},
        }
        checked = template.check_template(data)
        if not checked.ok:
            raise AssertionError(f"Template check failed for {fmt}: {checked.missing_keys!r}")
        replaced_count = template.render_template(data)
        if replaced_count < 3:
            raise AssertionError(f"Expected 3 or more template replacements, got {replaced_count}")
        filled = save(template, "02_template_filled")
        filled_again = Document.open(filled)
        if not any("Acme Corp" in p.text for p in filled_again.paragraphs):
            raise AssertionError("Saved template output does not contain customer")
        evidence["scenarios"][f"template_{fmt}"] = {
            "status": "PASS", "tag_count": checked.tag_count,
            "substitutions": replaced_count, "readonly_check_ok": checked.ok,
        }

        # Multi-paragraph, native tracked revisions for a real business review.
        # Keep structure compatible; only the text changes.
        before = Document.new(fmt)
        after = Document.new(fmt)
        amendments = [
            ("PROCUREMENT AGREEMENT | REVIEW COPY", "PROCUREMENT AGREEMENT | REVIEW COPY"),
            ("Customer: Acme Corp", "Customer: Acme Corporation"),
            ("Project: Northwind regional rollout", "Project: Northwind national rollout with onsite training"),
            ("Agreement ID: NW-2026-042", "Agreement ID: NW-2026-042"),
            ("Scope: Deploy 12 workstations at the main office.", "Scope: Deploy 24 workstations across three regional offices."),
            ("Contract price: USD 10,000, payable within 30 days.", "Contract price: USD 12,500, paid in two installments within 45 days."),
            ("Delivery date: November 15, 2026.", "Delivery date: December 1, 2026."),
            ("Implementation: Remote onboarding for one business day.", "Implementation: Onsite onboarding for three business days."),
            ("Support: 3 months of email support during business hours.", "Support: 6 months of email and phone support, including weekends."),
            ("Service level: Critical cases answered within 48 hours.", "Service level: Critical cases answered within 12 hours."),
            ("Primary contact: alice@acme.test", "Primary contact: contracts@acme.test"),
            ("Data handling: Files stored for 90 days after delivery.", "Data handling: Files deleted 30 days after final acceptance."),
            ("Warranty: Defective equipment repaired within 20 days.", "Warranty: Defective equipment replaced within 7 days."),
            ("Late delivery: Supplier may delay delivery by 3 business days.", "Late delivery: Supplier must notify customer within 1 business day."),
            ("Approval status: Draft, pending internal review.", "Approval status: Approved by legal and finance teams."),
            ("Confidentiality: Both parties protect nonpublic information.", "Confidentiality: Both parties protect nonpublic information."),
        ]
        assert sum(a != b for a, b in amendments) == 13
        for previous, revised in amendments:
            before.add_paragraph(previous)
            after.add_paragraph(revised)
        save(before, "03_revision_before")
        save(after, "04_revision_after")
        tracked = before.compare(after, author="Sample Reviewer")
        tracked_path = save(tracked, "05_tracked_review")
        # True tracked changes, not merely red/green text styling.
        if fmt == "docx":
            with ZipFile(tracked_path) as z:
                xml = z.read("word/document.xml")
            if b"<w:ins" not in xml or b"<w:del" not in xml:
                raise AssertionError("Tracked DOCX missing native insertion/deletion markup")
        evidence["scenarios"][f"tracked_{fmt}"] = {
            "status": "PASS", "tracked_document": tracked_path.name,
            "meaning": "native revision writer, supported text-only structure",
        }

        # Read-only replacement preview, then explicit actual replacement.
        draft = Document.new(fmt)
        draft.add_paragraph("APPROVAL WORKFLOW | SAMPLE")
        draft.add_paragraph("Status: Draft")
        save(draft, "06_preview_before")
        preview = draft.preview_replace("Draft", "Approved")
        if preview.count != 1:
            raise AssertionError(f"Expected one read-only preview match; got {preview.count}")
        if "Draft" not in draft.paragraphs[-1].text:
            raise AssertionError("Preview unexpectedly edited the document")
        (dest / f"preview_report_{fmt}.json").write_text(
            json.dumps(preview.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if draft.replace_text("Draft", "Approved") != 1:
            raise AssertionError("Actual replacement count differs from preview")
        save(draft, "07_preview_after")
        evidence["scenarios"][f"preview_{fmt}"] = {
            "status": "PASS", "matches": preview.count, "read_only": True
        }
    return sources, evidence


def pdf_to_png(pdf: Path, png: Path) -> dict:
    """Rasterize a real application-exported PDF page; never synthesize UI."""
    import fitz
    with fitz.open(str(pdf)) as document:
        if len(document) == 0:
            raise RuntimeError(f"Empty PDF: {pdf.name}")
        page = document[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.75, 1.75), alpha=False)
        pix.save(str(png))
        return {"pages": len(document), "preview": png.name,
                "preview_pixels": [pix.width, pix.height]}


def render_with_word(sources: list[Path], dest: Path) -> dict:
    paths = [p for p in sources if p.suffix.lower() == ".docx"]
    try:
        import win32com.client
    except ImportError as exc:
        return {"status": "SKIP", "reason": f"pywin32 unavailable: {exc}"}
    try:
        app = win32com.client.DispatchEx("Word.Application")
    except Exception as exc:
        return {"status": "SKIP", "reason": f"Microsoft Word COM unavailable: {exc}"}

    successes, failures = [], []
    try:
        app.Visible = False
        app.DisplayAlerts = 0
        for path in paths:
            doc = None
            try:
                doc = app.Documents.Open(str(path.resolve()), ReadOnly=True,
                                         AddToRecentFiles=False, Visible=False)
                is_tracked = path.stem == "05_tracked_review"
                revision_count = int(doc.Revisions.Count)
                if is_tracked and revision_count < 1:
                    raise AssertionError("Word does not recognize tracked revisions")
                pdf = dest / f"WORD_{path.stem}.pdf"
                png = dest / f"WORD_{path.stem}.png"
                # wdExportDocumentWithMarkup=7. For the tracked sample this asks
                # Word to include revision markup; human visual QA is still needed.
                doc.ExportAsFixedFormat(str(pdf.resolve()), 17,
                                        OpenAfterExport=False,
                                        Item=7 if is_tracked else 0)
                if not pdf.is_file() or pdf.stat().st_size < 100:
                    raise RuntimeError(f"Word exported no PDF: {pdf.name}")
                visual = pdf_to_png(pdf, png)
                successes.append({"source": path.name, "pdf": pdf.name,
                                  "word_revision_count": revision_count,
                                  "render_method": "Word COM PDF then PyMuPDF",
                                  **visual})
            except Exception as exc:
                failures.append({"source": path.name, "error": repr(exc),
                                 "traceback": traceback.format_exc()})
            finally:
                if doc is not None:
                    try:
                        doc.Close(SaveChanges=0)
                    except Exception:
                        pass
    finally:
        try:
            app.Quit()
        except Exception:
            pass
    return {"status": "FAIL" if failures else "PASS",
            "passed": len(successes), "failed": len(failures),
            "renders": successes, "errors": failures}


def start_hancom():
    """Use the *same official user-approved module* as tests/native/run_rc_windows.py.

    Never auto-install the module, accept a security prompt, or bypass Hancom.
    """
    import winreg
    import win32com.client
    name = "FilePathCheckerModuleExample"
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, r"Software\HNC\HwpAutomation\Modules"
    ) as key:
        dll, kind = winreg.QueryValueEx(key, name)
    if kind != winreg.REG_SZ or not Path(dll).is_file():
        raise RuntimeError("Registered Hancom official module DLL is invalid")
    app = win32com.client.DispatchEx("HWPFrame.HwpObject")
    try:
        if app.RegisterModule("FilePathCheckDLL", name) is False:
            raise RuntimeError("Hancom official file-access module registration failed")
        return app
    except Exception:
        try:
            app.Quit()
        except Exception:
            pass
        raise


def render_with_hancom(sources: list[Path], dest: Path) -> dict:
    paths = [p for p in sources if p.suffix.lower() == ".hwpx"]
    try:
        app = start_hancom()
    except Exception as exc:
        return {"status": "SKIP", "reason": (
            "Hancom COM or official user-approved security module unavailable. "
            "Nothing was bypassed: " + repr(exc)
        )}
    successes, failures = [], []
    try:
        for path in paths:
            try:
                app.Clear(1)
                if app.Open(str(path.resolve()), "HWPX", "") is False:
                    raise RuntimeError(f"Hancom Open returned False for {path.name}")
                pdf = dest / f"HANCOM_{path.stem}.pdf"
                png = dest / f"HANCOM_{path.stem}.png"
                app.SaveAs(str(pdf.resolve()), "PDF", "")
                if not pdf.is_file() or pdf.stat().st_size < 100:
                    raise RuntimeError(f"Hancom saved no PDF: {pdf.name}")
                visual = pdf_to_png(pdf, png)
                successes.append({"source": path.name, "pdf": pdf.name,
                                  "render_method": "Hancom COM PDF then PyMuPDF",
                                  **visual})
            except Exception as exc:
                failures.append({"source": path.name, "error": repr(exc),
                                 "traceback": traceback.format_exc()})
    finally:
        try:
            app.Clear(1)
        except Exception:
            pass
        try:
            app.Quit()
        except Exception:
            pass
    return {"status": "FAIL" if failures else "PASS",
            "passed": len(successes), "failed": len(failures),
            "renders": successes, "errors": failures}


def write_bundle(directory: Path, result: dict) -> Path:
    result["files"] = {
        p.relative_to(directory).as_posix(): {
            "bytes": p.stat().st_size, "sha256": sha256(p)
        }
        for p in sorted(directory.rglob("*")) if p.is_file()
    }
    (directory / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    notes = [
        "# PyWPDoc marketing samples — local QA evidence",
        "",
        "These are synthetic English business documents, not customer files.",
        "PNG previews are PDF-page rasterizations produced from a *real* "
        "Word/Hancom COM PDF export (never app chrome or fabricated screenshots).",
        "The tracked DOCX export requests Word's 'document with markup' mode. "
        "Verify visually that redlines are visible before public use.",
        "PASS in semantic document creation does not prove Word/Hancom visual fidelity.",
        "A SKIP means no native image evidence for that app.",
        "",
        f"Installed package version: {result.get('package_version', 'unknown')}",
        f"Word PDF: {result.get('word', {}).get('status', 'unknown')}",
        f"Hancom PDF: {result.get('hancom', {}).get('status', 'unknown')}",
        "",
        "Upload the ZIP to ChatGPT for image inspection. You may review it first.",
    ]
    (directory / "READ_ME_FIRST.txt").write_text("\n".join(notes) + "\n",
                                                 encoding="utf-8")
    zip_path = directory.parent / (directory.name + ".zip")
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        for item in sorted(directory.rglob("*")):
            if item.is_file():
                archive.write(item, item.relative_to(directory).as_posix())
    return zip_path


def run(*, output_root: Path, generate_only: bool = False) -> int:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:6]
    directory = output_root.resolve() / f"SHOWCASE_RESULTS_{run_id}"
    directory.mkdir(parents=True, exist_ok=False)
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "machine": {"platform": platform.system(), "python": platform.python_version()},
        "purpose": "synthetic DOCX/HWPX marketing screenshot evidence",
        "generator": "tests/showcase/run_showcase.py",
    }
    exit_code = 0
    try:
        sources, document_result = create_sources(directory)
        result.update(document_result)
        print("Created", len(sources), "synthetic documents", flush=True)
        if generate_only:
            result["word"] = {"status": "SKIP", "reason": "--generate-only"}
            result["hancom"] = {"status": "SKIP", "reason": "--generate-only"}
        elif os.name != "nt":
            result["word"] = {"status": "SKIP", "reason": "Windows required"}
            result["hancom"] = {"status": "SKIP", "reason": "Windows required"}
            exit_code = 2
        else:
            result["word"] = render_with_word(sources, directory)
            result["hancom"] = render_with_hancom(sources, directory)
            if result["word"]["status"] != "PASS" or result["hancom"]["status"] == "FAIL":
                exit_code = 2
    except Exception as exc:
        result["fatal_error"] = repr(exc)
        result["traceback"] = traceback.format_exc()
        print("Error:", exc, file=sys.stderr, flush=True)
        exit_code = 3
    finally:
        bundle = write_bundle(directory, result)
        print("UPLOAD THIS ZIP:", bundle, flush=True)
        print("Word:", result.get("word", {}).get("status", "not run"),
              "| Hancom:", result.get("hancom", {}).get("status", "not run"),
              flush=True)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-only", action="store_true",
                        help="CI/offline: generate DOCX/HWPX sources without COM screenshots")
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    args = parser.parse_args()
    return run(output_root=args.output_root, generate_only=args.generate_only)


if __name__ == "__main__":
    raise SystemExit(main())
