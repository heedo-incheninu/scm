from __future__ import annotations

from scm.analysis import analyze_inventory
from scm.comparison import compare_strategies
from scm.copilot import build_copilot_brief, calculate_strategy_effects


def test_strategy_effects_compare_priority_with_baselines(sample_data):
    products, sales = sample_data
    result = analyze_inventory(products, sales, "moderate", 0.2)
    comparison = compare_strategies(result.safety_stock, [0.2])

    effects = calculate_strategy_effects(comparison)

    assert effects.priority_protection > 0
    assert effects.proportional_delta_pp > 0


def test_copilot_brief_returns_actions_and_evidence(sample_data):
    products, sales = sample_data
    result = analyze_inventory(products, sales, "moderate", 0.2)
    comparison = compare_strategies(result.safety_stock, [0.2])
    effects = calculate_strategy_effects(comparison)

    brief = build_copilot_brief(
        result.allocation,
        effects,
        scenario_label="중간 충격",
        budget_ratio=0.2,
    )

    assert "중간 충격" in brief.headline
    assert len(brief.actions) == 3
    assert brief.evidence
