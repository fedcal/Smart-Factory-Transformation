#!/usr/bin/env python3
"""spot_check_testset.py — interactive 10% manual review of the RAG testset (Plan 05-10 Task 4 + Task 5 checkpoint).

Per D-71 LOCKED: required to mitigate Qwen-self-bias in the LLM-generated testset.

Sample 10% of queries (uniformly, seeded), present each to the operator, and
record y/n answers for two gates:

    realistic?     — "is this query something a textile factory operator could
                      plausibly type into the system?"
    gold_correct?  — "is the proposed gold chunk actually the right answer?"

Output: reject_rate = (rejects / sampled). Exit 1 if > 20%, else exit 0.

This is the manual checkpoint (Task 5) of the autonomous=false plan.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TESTSET = WORKSPACE_ROOT / "tests" / "data" / "rag_eval" / "testset.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("spot_check_testset")


def _prompt_yn(label: str) -> bool:
    """Prompt the operator for y/n; loops until a clean answer is given."""
    while True:
        ans = input(f"{label} (y/n): ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please answer y or n.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--testset", type=Path, default=DEFAULT_TESTSET)
    parser.add_argument("--sample-rate", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.20,
        help="Acceptance gate: exit 1 if reject_rate > threshold (default 0.20 per D-71).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Print the sample plan and exit 0 without prompting (CI sanity).",
    )
    args = parser.parse_args()

    if not args.testset.exists():
        logger.error("testset_missing path=%s", args.testset)
        return 1

    records: list[dict] = []
    for line in args.testset.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))

    n = len(records)
    if n == 0:
        logger.error("testset_empty path=%s", args.testset)
        return 1

    random.seed(args.seed)
    k = max(1, int(round(n * args.sample_rate)))
    sample = random.sample(records, k=k)
    logger.info("spot_check_sampled total=%d sampled=%d rate=%.2f", n, k, args.sample_rate)

    if args.non_interactive:
        for r in sample:
            print(f"  - {r['id']} [{r['type']}] {r['query']!r} → {r['gold_sop_id']}#chunk{r['gold_chunk_idx']}")
        return 0

    rejects = 0
    for i, r in enumerate(sample, start=1):
        print("=" * 72)
        print(f"[{i}/{k}] id={r['id']} type={r['type']} lang={r['lang']}")
        print(f"  query:     {r['query']}")
        print(f"  gold SOP:  {r['gold_sop_id']}#chunk{r['gold_chunk_idx']}")
        realistic = _prompt_yn("  query realistic?")
        gold_ok = _prompt_yn("  gold chunk correct?")
        if not realistic or not gold_ok:
            rejects += 1

    reject_rate = rejects / k
    print()
    print(f"sampled={k} rejects={rejects} reject_rate={reject_rate:.2%}")
    if reject_rate > args.threshold:
        print(
            f"FAIL: reject_rate {reject_rate:.2%} > threshold {args.threshold:.0%}; "
            "regenerate testset with `--regenerate` and revise the Q-gen prompt."
        )
        return 1
    print("PASS: reject_rate within threshold; testset accepted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
