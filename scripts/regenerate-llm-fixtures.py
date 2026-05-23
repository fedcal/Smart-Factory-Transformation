#!/usr/bin/env python3
"""regenerate-llm-fixtures.py — re-record JSONL replay traces for OPS agents.

Plan 06-13 Task 2 / Pitfall §10 mitigation.

The hand-authored JSONL fixtures under ``tests/fixtures/llm_responses/`` use
empty ``prompt_hash`` strings and rely on the MockReplayChatModel's ordered
fallback (with a structlog warning). That keeps fixture authoring tractable
without computing real sha256 of every prompt — but it means CI sees a
``mock_llm_hash_miss_fallback`` warning on every run.

Pre-release, run this script to regenerate the JSONL fixtures with real
``prompt_hash`` values computed against real LLM rounds — eliminating the
warning and locking in a 1:1 prompt→response trace.

Usage::

    # Re-record one (agent, scenario):
    uv run python scripts/regenerate-llm-fixtures.py \\
        --agent operator-assistant --scenario happy --backend ollama

    # Re-record all 12 scenarios:
    uv run python scripts/regenerate-llm-fixtures.py --all --backend ollama

Backends:
    ollama   — local Ollama daemon (default Qwen2.5-7B-Instruct).
    vllm     — local vLLM server (Qwen2.5 served via OpenAI-compatible API).

The script is OPT-IN — never executed in CI. CI runs the existing fixtures
with ordered-fallback; this tool is for the human author of OPS agent
prompts to refresh the trace whenever prompts change.

Status:
    SKELETON — the recorder loop is intentionally a documented TODO. Wiring
    it requires a live LLM backend + the full agent collaborators
    (testcontainers) and is out-of-scope for the deterministic CI E2E.
    The full implementation is queued for Phase 11 (observability), where
    we also wire the drift CI gate that flags stale fixtures.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Iterable


_AGENTS: tuple[str, ...] = (
    "operator-assistant",
    "production-planner",
    "quality-inspector",
    "anomaly-detector",
)
_SCENARIOS: tuple[str, ...] = ("happy", "degraded", "failure")
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_FIXTURES_ROOT = _REPO_ROOT / "tests" / "fixtures" / "llm_responses"
_SCENARIOS_ROOT = _REPO_ROOT / "tests" / "fixtures" / "ops_scenarios"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Regenerate JSONL mock LLM traces for OPS agents (Pitfall §10)."
    )
    p.add_argument(
        "--agent",
        choices=_AGENTS,
        help="Agent slug to regenerate (omit with --all).",
    )
    p.add_argument(
        "--scenario",
        choices=_SCENARIOS,
        help="Scenario slug to regenerate (omit with --all).",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Regenerate every (agent, scenario) pair (12 fixtures).",
    )
    p.add_argument(
        "--backend",
        choices=("ollama", "vllm"),
        default="ollama",
        help="Real LLM backend to record against (default: ollama).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be regenerated without invoking the backend.",
    )
    return p.parse_args()


def _enumerate_targets(args: argparse.Namespace) -> Iterable[tuple[str, str]]:
    if args.all:
        for a in _AGENTS:
            for s in _SCENARIOS:
                yield a, s
        return
    if not args.agent or not args.scenario:
        print(
            "ERROR: supply --agent + --scenario or use --all to regenerate every fixture.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    yield args.agent, args.scenario


def regenerate_one(agent: str, scenario: str, backend: str, *, dry_run: bool) -> None:
    """Re-record one (agent, scenario) JSONL trace.

    SKELETON — see module docstring. Outline of the production implementation:

        1. Load tests/fixtures/ops_scenarios/{agent}/{scenario}.yaml.
        2. Spin the same testcontainer set as tests/e2e/ops/conftest.py
           (Qdrant + Neo4j + TSDB + NATS + PG) seeded from spec.seed.
        3. Build the appropriate agent (operator-assistant uses
           ``OperatorAssistantAgent``; production-planner uses
           ``ProductionPlanner``; quality-inspector uses ``QualityInspector``;
           anomaly-detector uses ``AnomalyDetector``).
        4. Build a real ChatModel via sft_agents.llm.factory.build_chat_model
           with LLM_BACKEND={backend} + temperature=0 + seed=42.
        5. Wrap the model in a Recorder shim that intercepts every ``ainvoke``
           call and writes ``{"prompt_hash", "response": {...}}`` to the JSONL.
        6. Invoke the agent with spec.input.body.
        7. Close the recorder, dump JSONL to
           ``tests/fixtures/llm_responses/{agent}/{scenario}.jsonl``.
        8. Tear down testcontainers.

    For the AnomalyDetector the script is a no-op (deterministic; never calls
    LLM) and we just write a documentation placeholder.
    """
    target_path = _FIXTURES_ROOT / agent / f"{scenario}.jsonl"
    scenario_path = _SCENARIOS_ROOT / agent / f"{scenario}.yaml"
    if not scenario_path.exists():
        print(f"SKIP: missing scenario file {scenario_path}", file=sys.stderr)
        return

    if dry_run:
        print(
            f"DRY-RUN would regenerate {target_path.relative_to(_REPO_ROOT)} "
            f"(scenario={scenario_path.relative_to(_REPO_ROOT)}, backend={backend})"
        )
        return

    if agent == "anomaly-detector":
        print(
            f"SKIP: {agent}/{scenario}.jsonl — AnomalyDetector is deterministic "
            "and never invokes the LLM (no fixture to regenerate)."
        )
        return

    raise NotImplementedError(
        f"SKELETON: regeneration loop for {agent}/{scenario} not yet implemented. "
        "See module docstring outline + Phase 11 backlog ticket (CI drift gate). "
        "Workflow: load testcontainers from conftest, build agent, record real "
        "LLM rounds via a Recorder shim, dump JSONL with real prompt_hash."
    )


def main() -> int:
    args = parse_args()
    for agent, scenario in _enumerate_targets(args):
        try:
            regenerate_one(agent, scenario, args.backend, dry_run=args.dry_run)
        except NotImplementedError as exc:
            print(f"TODO: {exc}", file=sys.stderr)
            # Continue with other targets so --all surfaces every pending entry
            # at once instead of stopping on the first NotImplementedError.
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
