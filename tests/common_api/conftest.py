"""Backend matrix: every shared API contract must run against DOCX and HWPX."""
from __future__ import annotations

import pytest
from pywpdoc import Document


@pytest.fixture(params=["docx", "hwpx"], ids=["DOCX", "HWPX"])
def common_format(request):
    return request.param


@pytest.fixture
def document(common_format):
    return Document.new(common_format)


@pytest.fixture
def save_reopen(tmp_path, common_format):
    def roundtrip(doc, name="contract"):
        path = tmp_path / f"{name}.{common_format}"
        doc.save(path)
        return Document.open(path), path
    return roundtrip
