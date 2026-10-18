"""Independent-review defect regressions (2026-10-15)."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

import pytest
from pywpdoc import Document
from pywpdoc._engine.core.errors import DocumentUnsupportedError, DocumentValueError
from pywpdoc._engine.core.snapshot import DocumentSnapshot
from pywpdoc._engine.docx.snapshot import import_snapshot as import_docx_snapshot


def _make_docx(path: Path) -> None:
    d = Document.new("docx")
    d.add_paragraph("본문 원문")
    table = d.add_table(2, 2)
    table.cell(0, 0).text = "중요 데이터"
    table.cell(1, 1).text = "보존해야 할 값"
    d.save(path)


@pytest.mark.parametrize("preserve_layout", [True, False])
def test_docx_rebuild_same_format_preserves_body_and_tables(tmp_path, preserve_layout):
    src = tmp_path / "source.docx"
    _make_docx(src)
    restored = Document.rebuild(src, format="docx", preserve_layout=preserve_layout)
    out = tmp_path / "rebuilt.docx"
    restored.save(out)
    opened = Document.open(out)
    assert [p.text for p in opened.paragraphs] == ["본문 원문"]
    assert len(opened.tables) == 1
    assert opened.tables[0].cell(0, 0).text == "중요 데이터"
    assert opened.tables[0].cell(1, 1).text == "보존해야 할 값"
    # Restoring the package must not erase unrelated parts.
    with zipfile.ZipFile(src) as a, zipfile.ZipFile(out) as b:
        assert set(a.namelist()) == set(b.namelist())
        assert a.read("word/document.xml") == b.read("word/document.xml")


def test_docx_missing_native_payload_fails_closed():
    snapshot = DocumentSnapshot(source_format="docx", portable={}, native_payload={})
    with pytest.raises(DocumentUnsupportedError) as exc:
        import_docx_snapshot(snapshot)
    assert exc.value.code == "docx-snapshot-native-payload-required"


def test_docx_to_hwpx_rebuild_unsupported_without_partial_output(tmp_path):
    src = tmp_path / "source.docx"
    _make_docx(src)
    with pytest.raises(DocumentUnsupportedError) as exc:
        Document.rebuild(src, format="hwpx")
    assert exc.value.code == "rebuild-docx-to-hwpx-unsupported"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_compare_body_only_rejects_untracked_table_text(fmt):
    old = Document.new(fmt)
    new = Document.new(fmt)
    old.add_paragraph("before"); new.add_paragraph("after")
    t1=old.add_table(1,1); t1.cell(0,0).text="OLD CELL"
    t2=new.add_table(1,1); t2.cell(0,0).text="NEW CELL"
    with pytest.raises(DocumentUnsupportedError) as exc:
        old.compare(new, everywhere=False)
    assert exc.value.code == "compare-outside-scope-changes-unsupported"
    assert t1.cell(0,0).text == "OLD CELL"
    assert t2.cell(0,0).text == "NEW CELL"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_compare_body_only_rejects_untracked_table_row_insert(fmt):
    old=Document.new(fmt);new=Document.new(fmt)
    old.add_paragraph("same");new.add_paragraph("same")
    a=old.add_table(1,1);a.cell(0,0).text="same"
    b=new.add_table(2,1);b.cell(0,0).text="same";b.cell(1,0).text="NEW"
    with pytest.raises(DocumentUnsupportedError) as exc:
        old.compare(new,everywhere=False)
    assert exc.value.code == "compare-outside-scope-changes-unsupported"


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_compare_body_only_allows_unchanged_table(fmt):
    old=Document.new(fmt);new=Document.new(fmt)
    old.add_paragraph("before");new.add_paragraph("after")
    a=old.add_table(1,1);a.cell(0,0).text="same"
    b=new.add_table(1,1);b.cell(0,0).text="same"
    old.compare(new,everywhere=False)


@pytest.mark.parametrize("fmt", ["docx", "hwpx"])
def test_template_missing_error_is_document_atomic(fmt):
    d=Document.new(fmt)
    d.add_paragraph("Hello {{name}}")
    d.add_paragraph("No {{missing}}")
    with pytest.raises(DocumentValueError) as exc:
        d.render_template({"name":"Alice"},missing="error",everywhere=False)
    assert exc.value.code == "template-value-missing"
    assert [x.text for x in d.paragraphs] == ["Hello {{name}}", "No {{missing}}"]


def test_hwpx_native_run_edit_clears_only_local_paragraph_cache():
    d=Document.new('hwpx')
    for i in range(15):d.add_paragraph(f'P{i}:old')
    p=d.paragraphs[8]
    p.runs[0].text='P8:new'
    assert p.text=='P8:new'
    assert d.paragraphs[7].text=='P7:old'
    assert d.paragraphs[9].text=='P9:old'


def test_hwpx_bulk_replacement_is_correct(tmp_path):
    d=Document.new('hwpx')
    for i in range(1000):d.add_paragraph(f'[{i:04}] old token')
    assert d.replace_text('old','NEW')==1000
    path=tmp_path/'bulk.hwpx';d.save(path)
    reopened=Document.open(path)
    text='\n'.join(p.text for p in reopened.paragraphs)
    assert text.count('NEW token')==1000 and 'old token' not in text


def test_hwpx_to_docx_unmeasured_table_rows_allow_text_to_grow(tmp_path):
    d = Document.new('hwpx')
    d.add_paragraph('본문')
    table = d.add_table(2, 1)
    table.cell(0, 0).text = '보존문자'
    table.cell(1, 0).text = '다음셀'
    output = tmp_path / 'renderable.docx'
    rebuilt = Document.rebuild(d, format='docx')
    rebuilt.save(output)
    from lxml import etree
    with zipfile.ZipFile(output) as zf:
        root = etree.fromstring(zf.read('word/document.xml'))
    ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    for marker in ('보존문자', '다음셀'):
        rows = root.xpath('//w:tr[.//w:t[text()=$value]]', namespaces=ns, value=marker)
        assert rows, marker
        # No exact row-height rule that is smaller than the rendered text.
        for row in rows:
            for elem in row.xpath('./w:trPr/w:trHeight',namespaces=ns):
                assert elem.get('{%s}hRule'%ns['w']) != 'exact'


def test_docx_rebuild_from_preserves_original_docx(tmp_path):
    input_file = tmp_path / 'input.docx'; _make_docx(input_file)
    source = Document.open(input_file)
    target = Document.new('docx')
    target.add_paragraph('to be replaced')
    target.rebuild_from(source)
    output = tmp_path / 'output.docx'; target.save(output)
    reopened = Document.open(output)
    assert reopened.paragraphs[0].text == '본문 원문'
    assert reopened.tables[0].cell(0, 0).text == '중요 데이터'
