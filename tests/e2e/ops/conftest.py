"""Wave 0 stub for plan 06-12 — shared fixtures for ops e2e scenarios.

Provides minimal-shape fixtures so Wave 1+ test stubs already have a
fixture symbol to bind to:

- `ops_scenario(request)` — yaml.safe_load loader for a scenario YAML file
  identified by indirect parametrize value (e.g. "operator-assistant/happy").
  Returns an empty dict if the YAML payload is the Wave 0 placeholder.

- `mock_llm_backend(monkeypatch, request)` — sets env `LLM_BACKEND=mock`
  and `MOCK_LLM_FIXTURE=<absolute path>` to the corresponding JSONL trace
  file so the MockReplayChatModel (plan 06-01) can pick it up. Wave 0
  does not instantiate the backend — full wiring lands in plan 06-12.

Testcontainers wiring (Qdrant + Neo4j + TimescaleDB + NATS + Postgres)
is deferred to plan 06-12 to avoid Wave 0 dependencies on infra fixtures
that do not yet exist.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest
import yaml

# Repo root computed relative to this file (robust against cwd).
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SCENARIOS_ROOT = _REPO_ROOT / "tests" / "fixtures" / "ops_scenarios"
_LLM_TRACES_ROOT = _REPO_ROOT / "tests" / "fixtures" / "llm_responses"


def _resolve_scenario_key(request: pytest.FixtureRequest) -> str:
    """Extract '<agent>/<scenario>' from indirect parametrize or fallback.

    Tests should pass an indirect parametrize like
    `@pytest.mark.parametrize("ops_scenario", ["operator-assistant/happy"], indirect=True)`.
    If no parametrize value is provided, returns a sentinel that maps to no
    fixture file and yields an empty dict (Wave 0 stub posture).
    """
    param = getattr(request, "param", None)
    if isinstance(param, str) and "/" in param:
        return param
    return ""


@pytest.fixture
def ops_scenario(request: pytest.FixtureRequest) -> dict[str, Any]:
    """Load a scenario YAML via `yaml.safe_load` (T-V6-W0-yaml-injection mitigation).

    Returns:
        Parsed YAML dict, or {} if no scenario was selected / file is empty.
    """
    key = _resolve_scenario_key(request)
    if not key:
        return {}
    yaml_path = _SCENARIOS_ROOT / f"{key}.yaml"
    if not yaml_path.exists():
        return {}
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


@pytest.fixture
def mock_llm_backend(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> dict[str, str]:
    """Configure env to point MockReplayChatModel at the matching JSONL trace.

    Sets:
        LLM_BACKEND=mock
        MOCK_LLM_FIXTURE=<abs path to tests/fixtures/llm_responses/<key>.jsonl>

    Returns the resolved env mapping for assertion convenience. Does NOT
    instantiate the backend — that wiring lands in plan 06-12 once the
    MockReplayChatModel (plan 06-01) is on disk.
    """
    key = _resolve_scenario_key(request)
    env: dict[str, str] = {"LLM_BACKEND": "mock"}
    if key:
        jsonl_path = _LLM_TRACES_ROOT / f"{key}.jsonl"
        env["MOCK_LLM_FIXTURE"] = str(jsonl_path)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return env
