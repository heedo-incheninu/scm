from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

from scm.analysis import analyze_inventory
from scm.diagnosis import build_prompt, generate_diagnosis


def test_demo_diagnosis_works_without_api_key(sample_data):
    products, sales = sample_data
    result = analyze_inventory(products, sales)
    diagnosis = generate_diagnosis(
        result.allocation,
        "중간 충격",
        0.2,
        api_key=None,
    )

    assert diagnosis.mode == "demo"
    assert "위험 요약" in diagnosis.text
    assert "판단의 한계" in diagnosis.text
    assert "**" not in diagnosis.text
    assert "###" not in diagnosis.text


def test_prompt_contains_only_aggregated_decision_context(sample_data):
    products, sales = sample_data
    result = analyze_inventory(products, sales)
    prompt = build_prompt(result.allocation, "중간 충격", 0.2)

    assert "SKU-" in prompt
    assert "2024-" not in prompt
    assert "수치를 과장" in prompt


def test_api_failure_falls_back_to_demo(sample_data, monkeypatch):
    products, sales = sample_data
    result = analyze_inventory(products, sales)
    fake_openai = ModuleType("openai")

    class FailingOpenAI:
        def __init__(self, **_kwargs):
            raise RuntimeError("API unavailable")

    fake_openai.OpenAI = FailingOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    diagnosis = generate_diagnosis(
        result.allocation,
        "중간 충격",
        0.2,
        api_key="test-key",
    )

    assert diagnosis.mode == "demo"
    assert diagnosis.warning and "OpenAI 호출 실패" in diagnosis.warning


def test_openai_responses_output_is_returned(sample_data, monkeypatch):
    products, sales = sample_data
    result = analyze_inventory(products, sales)
    fake_openai = ModuleType("openai")

    class SuccessfulOpenAI:
        def __init__(self, **_kwargs):
            self.responses = SimpleNamespace(
                create=lambda **_request: SimpleNamespace(output_text="검증된 OpenAI 조언")
            )

    fake_openai.OpenAI = SuccessfulOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    diagnosis = generate_diagnosis(
        result.allocation,
        "중간 충격",
        0.2,
        api_key="test-key",
    )

    assert diagnosis.mode == "openai"
    assert diagnosis.text == "검증된 OpenAI 조언"
