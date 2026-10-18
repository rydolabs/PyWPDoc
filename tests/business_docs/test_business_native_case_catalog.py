"""Shape and governance of synthetic corpus (no GUI prerequisites)."""
from __future__ import annotations
from tests.generators.business_docs.scenarios import SCENARIOS


def test_24_distinct_business_intents_with_columns_and_rows():
    assert len(SCENARIOS) == 24
    assert len({x.key for x in SCENARIOS}) == len(SCENARIOS)
    for scenario in SCENARIOS:
        assert len(scenario.sections) >= 4
        assert len(scenario.columns) >= 2
        assert len(scenario.records) >= 2
        assert all(len(row) == len(scenario.columns) for row in scenario.records)


def test_complex_media_nested_merge_and_bulk_scenarios_are_covered():
    assert sum(s.image for s in SCENARIOS) >= 4
    assert sum(s.nested for s in SCENARIOS) >= 2
    assert sum(s.merged for s in SCENARIOS) >= 2
    assert sum(s.template for s in SCENARIOS) >= 2
    assert sum(s.long for s in SCENARIOS) >= 1
    assert sum(s.extra_tables > 0 for s in SCENARIOS) >= 2
