from pathlib import Path

import pytest
from assess import CAPABILITIES, Worksheet, gaps_for, load, radar_svg, report, sustainable_level

EXAMPLE = Path(__file__).with_name("worksheet.example.yaml")


def test_example_worksheet():
    ws = load(EXAMPLE)
    assert sustainable_level(ws) == 3
    assert gaps_for(ws, 4) == ["quality_internal_platforms", "ai_accessible_internal_data"]
    assert "Sustainable level (course synthesis): L3" in report(ws)


def test_working_above_capabilities_warns():
    ws = Worksheet(team="t", workflow_level=4, capabilities={c: 1 for c in CAPABILITIES})
    assert sustainable_level(ws) == 1
    assert "Warning" in report(ws)


def test_validation_rejects_missing_and_out_of_range():
    with pytest.raises(ValueError):
        Worksheet(team="t", workflow_level=1, capabilities={"clear_ai_stance": 2})
    with pytest.raises(ValueError):
        Worksheet(team="t", workflow_level=1, capabilities={c: 9 for c in CAPABILITIES})


def test_radar_svg_has_one_vertex_per_capability():
    svg = radar_svg({c: 2 for c in CAPABILITIES})
    assert svg.startswith("<svg") and svg.count("<text") == len(CAPABILITIES)
