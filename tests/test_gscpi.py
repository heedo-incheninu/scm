from __future__ import annotations

import pandas as pd

from scm.gscpi import latest_gscpi_recommendation, load_gscpi_recommendation, recommend_scenario


def test_gscpi_thresholds_map_to_scenarios():
    assert recommend_scenario(0.1) == ("Normal", "normal", 1.0)
    assert recommend_scenario(0.8) == ("Warning", "moderate", 1.18)
    assert recommend_scenario(2.5) == ("Crisis", "high", 1.8)
    assert recommend_scenario(4.2) == ("Extreme", "extreme", 2.2)


def test_latest_gscpi_recommendation_uses_last_numeric_value():
    frame = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-02-01"],
            "GSCPI": [0.3, 2.3],
        }
    )

    recommendation = latest_gscpi_recommendation(frame)

    assert recommendation.value == 2.3
    assert recommendation.scenario == "high"
    assert recommendation.status == "Crisis"


def test_gscpi_loader_can_be_skipped_for_offline_tests(monkeypatch):
    monkeypatch.setenv("SCM_SKIP_GSCPI", "1")

    recommendation = load_gscpi_recommendation()

    assert recommendation.value is None
    assert recommendation.scenario == "moderate"
    assert recommendation.warning is not None

