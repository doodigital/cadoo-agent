"""Tests for the Nous-Cadoo-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"cadoo"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``cadoo-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "cadoo" tag namespace.

``is_nous_hermes_non_agentic`` should only match the actual DooStudio
Cadoo-3 / Cadoo-4 chat family.
"""

from __future__ import annotations

import pytest

from cadoo_cli.model_switch import (
    _HERMES_MODEL_WARNING,
    _check_hermes_model_warning,
    is_nous_hermes_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "DooStudio/Cadoo-3-Llama-3.1-70B",
        "DooStudio/Cadoo-3-Llama-3.1-405B",
        "cadoo-3",
        "Cadoo-3",
        "cadoo-4",
        "cadoo-4-405b",
        "hermes_4_70b",
        "openrouter/hermes3:70b",
        "openrouter/nousresearch/cadoo-4-405b",
        "DooStudio/Hermes3",
        "cadoo-3.1",
    ],
)
def test_matches_real_nous_hermes_chat_models(model_name: str) -> None:
    assert is_nous_hermes_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Cadoo 3/4"
    )
    assert _check_hermes_model_warning(model_name) == _HERMES_MODEL_WARNING


@pytest.mark.parametrize(
    "model_name",
    [
        # Kyle's local Modelfile — qwen3:14b under a custom tag
        "cadoo-brain:qwen3-14b-ctx16k",
        "cadoo-brain:qwen3-14b-ctx32k",
        "cadoo-honcho:qwen3-8b-ctx8k",
        # Plain unrelated models
        "qwen3:14b",
        "qwen3-coder:30b",
        "qwen2.5:14b",
        "claude-opus-4-6",
        "anthropic/claude-sonnet-4.5",
        "gpt-5",
        "openai/gpt-4o",
        "google/gemini-2.5-flash",
        "deepseek-chat",
        # Non-chat Cadoo models we don't warn about
        "cadoo-llm-2",
        "hermes2-pro",
        "nous-cadoo-2-mistral",
        # Edge cases
        "",
        "cadoo",  # bare "cadoo" isn't the 3/4 family
        "cadoo-brain",
        "brain-cadoo-3-impostor",  # "3" not preceded by /: boundary
    ],
)
def test_does_not_match_unrelated_models(model_name: str) -> None:
    assert not is_nous_hermes_non_agentic(model_name), (
        f"expected {model_name!r} NOT to be flagged as Nous Cadoo 3/4"
    )
    assert _check_hermes_model_warning(model_name) == ""


def test_none_like_inputs_are_safe() -> None:
    assert is_nous_hermes_non_agentic("") is False
    # Defensive: the helper shouldn't crash on None-ish falsy input either.
    assert _check_hermes_model_warning("") == ""
