"""Skip only explicitly enumerated private-fixture cases when not available.

The fixture is intentionally not shipped publicly. This is not a product pass.
With the approved fixture restored, these tests run without any skipping.
"""
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
PRIVATE_FIXTURE = HERE / "fixtures" / "original_notice.hwpx"
PRIVATE_CASES = {
    line.strip() for line in (HERE / "_private_fixture_nodeids.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
}


def pytest_collection_modifyitems(items):
    if PRIVATE_FIXTURE.is_file():
        return
    for item in items:
        if item.nodeid.replace("\\", "/") in PRIVATE_CASES:
            item.add_marker(pytest.mark.skip(
                reason="private golden HWPX fixture intentionally not redistributed"
            ))
