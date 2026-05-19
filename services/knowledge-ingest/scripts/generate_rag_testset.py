#!/usr/bin/env python3
"""generate_rag_testset.py — Q-gen for the RAG A/B testset (Plan 05-10 Task 4).

Per D-71 LOCKED: for each reviewed SOP in `simulators/synthetic-corpus/`, generate
3 query types via Qwen2.5-7B (via Phase 4 LLM adapter) with seed=42, temperature=0.3:

    keyword_it       — short IT keyword query (operator-style)
    natural_it       — natural-language IT question (a technician would ask)
    cross_lingual_en — English query against an IT SOP (or vice-versa)

Output `tests/data/rag_eval/testset.jsonl` — one JSON per line:
    {"id": "q-NNN", "query": str, "lang": "it|en", "type": ..., "gold_sop_id": str, "gold_chunk_idx": int}

Idempotent: default skips when the output file exists; pass --regenerate to force.

Fallback (no LLM available):
    --skip-llm flag generates a deterministic placeholder testset built from SOP titles
    so the eval deliverable can still be produced in CI without an LLM backend.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path
from typing import Iterable

import frontmatter

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = WORKSPACE_ROOT / "simulators" / "synthetic-corpus"
DEFAULT_OUTPUT = WORKSPACE_ROOT / "tests" / "data" / "rag_eval" / "testset.jsonl"

QUERY_TYPES = ("keyword_it", "natural_it", "cross_lingual_en")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("generate_rag_testset")


def _walk_reviewed_sops(root: Path) -> Iterable[Path]:
    """Yield every reviewed SOP markdown file under the corpus root."""
    for md in sorted(root.rglob("*.md")):
        if md.name.upper() == "README.MD":
            continue
        try:
            post = frontmatter.load(str(md))
        except Exception as exc:  # noqa: BLE001
            logger.warning("frontmatter_load_failed file=%s error=%s", md, exc)
            continue
        if post.metadata.get("status") == "reviewed":
            yield md


def _placeholder_queries(sop: Path, post) -> list[dict]:
    """Deterministic placeholder Q-gen used when --skip-llm is set."""
    title = str(post.metadata.get("title") or sop.stem)
    sop_id = str(post.metadata.get("id") or sop.stem)
    lang = post.metadata.get("lang") or ("it" if "/it/" in str(sop) else "en")
    return [
        {
            "type": "keyword_it",
            "lang": "it",
            "text": title.split(":")[0][:50].lower(),
            "target_section": "0",
        },
        {
            "type": "natural_it",
            "lang": "it",
            "text": f"come gestire {title.lower()}?",
            "target_section": "0",
        },
        {
            "type": "cross_lingual_en",
            "lang": "en",
            "text": f"procedure for {title.lower()}",
            "target_section": "0",
        },
    ]


def _llm_queries(sop: Path, post, seed: int) -> list[dict]:  # pragma: no cover
    """Q-gen via the Phase 4 LLM adapter (Qwen2.5-7B by default).

    Prompt structure follows D-71 lines 605-616: ask the model to produce exactly
    3 queries in JSON format with explicit type labels. Seed + temperature pin
    reproducibility within a single LLM backend version.
    """
    from sft_agents.llm.factory import build_chat_model

    llm = build_chat_model(temperature=0.3, seed=seed)
    title = str(post.metadata.get("title") or sop.stem)
    lang = post.metadata.get("lang") or "it"
    body = sop.read_text(encoding="utf-8")[:3000]

    prompt = (
        "You are generating retrieval evaluation queries for a textile-factory SOP.\n"
        "Given the SOP below, produce EXACTLY 3 queries as a JSON array of 3 objects.\n"
        "Each object MUST have these keys: type, lang, text, target_section.\n"
        "  - object[0].type = 'keyword_it', object[0].lang = 'it'  (short keyword query an operator would type)\n"
        "  - object[1].type = 'natural_it', object[1].lang = 'it'  (natural-language IT question a technician would ask)\n"
        "  - object[2].type = 'cross_lingual_en', object[2].lang = 'en'  (English equivalent of the same question)\n"
        "Return ONLY the JSON array — no markdown, no commentary.\n\n"
        f"SOP TITLE: {title}\n"
        f"SOP LANG:  {lang}\n"
        "SOP BODY:\n"
        f"{body}\n"
    )
    response = llm.invoke(prompt)
    text = response.content if hasattr(response, "content") else str(response)
    try:
        return json.loads(text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_response_parse_failed sop=%s error=%s", sop.name, exc)
        return _placeholder_queries(sop, post)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Use placeholder Q-gen instead of the LLM adapter (CI fallback).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"JSONL output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=CORPUS_ROOT,
        help="Corpus root (default: simulators/synthetic-corpus/).",
    )
    args = parser.parse_args()

    if args.output.exists() and not args.regenerate:
        logger.info("output_exists_skip path=%s (use --regenerate to overwrite)", args.output)
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)

    sop_files = list(_walk_reviewed_sops(args.corpus_root))
    logger.info("reviewed_sops_found count=%d", len(sop_files))

    counter = 0
    out_lines: list[str] = []
    for sop in sop_files:
        post = frontmatter.load(str(sop))
        sop_id = str(post.metadata.get("id") or sop.stem)
        try:
            entries = (
                _placeholder_queries(sop, post)
                if args.skip_llm
                else _llm_queries(sop, post, args.seed)
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm_failed sop=%s falling-back-to-placeholder error=%s", sop.name, exc)
            entries = _placeholder_queries(sop, post)

        for entry in entries[:3]:
            counter += 1
            record = {
                "id": f"q-{counter:03d}",
                "query": str(entry.get("text", "")).strip(),
                "lang": str(entry.get("lang", "it")),
                "type": str(entry.get("type", "natural_it")),
                "gold_sop_id": sop_id,
                "gold_chunk_idx": int(entry.get("target_section", 0) or 0),
            }
            out_lines.append(json.dumps(record, ensure_ascii=False))

    args.output.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    logger.info("testset_written path=%s queries=%d sops=%d", args.output, counter, len(sop_files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
