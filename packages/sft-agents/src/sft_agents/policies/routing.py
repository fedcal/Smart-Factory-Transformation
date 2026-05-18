"""HybridRouter — Stage 1 rules + Stage 2 LLM classifier (D-54).

Stage 1 (≤10ms): substring + regex match against routing.yaml rules.
    - Exactly 1 cluster matches → RoutingDecision(strategy='rules', confidence=1.0)
    - 0 OR ≥2 clusters match → defer to Stage 2

Stage 2 (~500ms–2s): LLM with structured_output=RoutingDecision + 4-shot examples.
    - If decision.confidence < 0.7 → fallback to ops, strategy='fallback_default_ops'
    - Else → return the LLM decision as-is

Trust boundary (T-04-LLM-Inject): the LLM-supplied cluster value is Pydantic-validated
against VALID_CLUSTERS by the RoutingDecision model_post_init, so prompt injection
cannot route to an arbitrary cluster name.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
import yaml

from sft_agents.runtime.state import VALID_CLUSTERS, AgentState, RoutingDecision

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

_log = structlog.get_logger(__name__)

_DEFAULT_YAML_PATH = Path(__file__).parent / "routing.yaml"

# Stage-2 4-shot examples (D-54). Italian-first, English fallback.
_FEWSHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "user": "Allarme sulla linea T-12, turno notte",
        "cluster": "ops",
        "rationale": "real-time alert on production line during shift → ops cluster",
    },
    {
        "user": "Necessaria root cause analysis del guasto al motore del cuscinetto",
        "cluster": "maintenance",
        "rationale": "RCA + failure language → maintenance cluster",
    },
    {
        "user": "Aggiorna il SOP di taratura con la nuova revisione",
        "cluster": "knowledge-curation",
        "rationale": "editorial document update → knowledge-curation cluster",
    },
    {
        "user": "Verifica costo energetico e demand forecast per il mese prossimo",
        "cluster": "supply",
        "rationale": "cost + demand forecasting → supply cluster",
    },
]


class HybridRouter:
    """Two-stage cluster router (D-54).

    Parameters
    ----------
    llm:
        Optional ``BaseChatModel`` for Stage 2 LLM classification. When ``None``
        every Stage-1 miss / multi-match collapses to ``fallback_default_ops``.
    routing_yaml_path:
        Override routing.yaml location (tests). Defaults to package-relative.
    """

    def __init__(
        self,
        *,
        llm: "BaseChatModel | Any | None" = None,
        routing_yaml_path: Path | None = None,
    ) -> None:
        self._llm = llm
        path = routing_yaml_path or _DEFAULT_YAML_PATH
        if not path.is_file():
            raise FileNotFoundError(f"routing.yaml not found at {path!r}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"routing.yaml must be a top-level mapping, got {type(raw).__name__}")
        self._rules: dict[str, dict[str, list[str]]] = raw

        # Validate clusters match VALID_CLUSTERS exactly (defense against drift).
        loaded = set(self._rules.keys())
        if loaded != VALID_CLUSTERS:
            raise ValueError(
                f"routing.yaml clusters {sorted(loaded)} do not match "
                f"VALID_CLUSTERS {sorted(VALID_CLUSTERS)}"
            )

        # Pre-compile regex patterns per cluster.
        self._compiled_patterns: dict[str, list[re.Pattern[str]]] = {}
        for cluster, cfg in self._rules.items():
            patterns = cfg.get("patterns") or []
            self._compiled_patterns[cluster] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    # ------------------------------------------------------------------ API

    async def route(self, state: AgentState | dict[str, Any]) -> RoutingDecision:
        """Return a RoutingDecision for the latest user message in `state`."""
        text = self._extract_last_user_text(state).lower()

        # ---- Stage 1: keyword + regex match
        matched: dict[str, str] = {}  # cluster -> first matched keyword/pattern
        for cluster, cfg in self._rules.items():
            for kw in cfg.get("keywords") or []:
                if kw.lower() in text:
                    matched[cluster] = kw
                    break
            else:
                # No keyword hit; try regex patterns.
                for pat in self._compiled_patterns[cluster]:
                    if pat.search(text):
                        matched[cluster] = pat.pattern
                        break

        if len(matched) == 1:
            cluster, kw = next(iter(matched.items()))
            decision = RoutingDecision(
                cluster=cluster,
                strategy="rules",
                confidence=1.0,
                matched_keyword=kw,
            )
            self._log_routing(decision)
            return decision

        # ---- Stage 2: LLM classifier (if available)
        if self._llm is not None:
            try:
                decision = await self._stage2_llm(text)
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "hybrid_router.stage2_failed",
                    error=str(exc),
                    text_prefix=text[:40],
                )
                return self._fallback()
            if decision.confidence < 0.7:
                _log.info(
                    "hybrid_router.stage2_low_confidence",
                    confidence=decision.confidence,
                    cluster_suggested=decision.cluster,
                )
                return self._fallback()
            self._log_routing(decision)
            return decision

        # ---- No LLM available → fallback
        return self._fallback(stage1_matches=list(matched.keys()))

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _extract_last_user_text(state: AgentState | dict[str, Any]) -> str:
        messages = state.get("messages") or []
        if not messages:
            return ""
        last = messages[-1]
        content = getattr(last, "content", None)
        if content is None and isinstance(last, dict):
            content = last.get("content")
        return str(content) if content is not None else ""

    async def _stage2_llm(self, text: str) -> RoutingDecision:
        prompt = self._build_fewshot_prompt(text)
        # `with_structured_output` returns a Runnable whose `.ainvoke` yields a
        # RoutingDecision instance.
        bound = self._llm.with_structured_output(RoutingDecision)  # type: ignore[union-attr]
        return await bound.ainvoke(prompt)

    @staticmethod
    def _build_fewshot_prompt(text: str) -> str:
        examples = "\n".join(
            f"USER: {ex['user']}\nCLUSTER: {ex['cluster']}\nRATIONALE: {ex['rationale']}\n"
            for ex in _FEWSHOT_EXAMPLES
        )
        return (
            "You are a smart-factory cluster router. Classify the USER intent "
            "into exactly one of: ops, maintenance, knowledge-curation, "
            "knowledge-training, supply.\n\n"
            "Return a JSON RoutingDecision with fields cluster (str), strategy "
            "(must be 'llm'), confidence (float 0..1).\n\n"
            f"{examples}\n"
            f"USER: {text}\nCLUSTER: ?\n"
        )

    @staticmethod
    def _fallback(stage1_matches: list[str] | None = None) -> RoutingDecision:
        decision = RoutingDecision(
            cluster="ops",
            strategy="fallback_default_ops",
            confidence=0.0,
        )
        _log.info(
            "hybrid_router.fallback_default_ops",
            stage1_matches=stage1_matches or [],
        )
        return decision

    @staticmethod
    def _log_routing(decision: RoutingDecision) -> None:
        _log.info(
            "supervisor.route",
            cluster=decision.cluster,
            strategy=decision.strategy,
            confidence=decision.confidence,
            matched_keyword=decision.matched_keyword,
        )


__all__ = ["HybridRouter"]
