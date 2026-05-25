---
title: Synthetic SOP corpus
description: Synthetic Standard Operating Procedures corpus for the textile manufacturing domain (KNW-10)
tags:
  - sop
  - corpus
  - knowledge
---

# Synthetic SOP corpus

This corpus contains 20 bilingual **Standard Operating Procedures** (SOPs) for the textile manufacturing domain, produced as a knowledge substrate for the Smart Factory Transformation agentic platform (requirement KNW-10).

The SOPs are structured for **granular retrieval**: each document carries validated YAML frontmatter exposing `asset`, `role`, `hazard_level`, `status`, and other agent-filterable fields used by Phase 5 (BGE-M3 + Qdrant).

## Where the SOPs live

The SOPs are **not MkDocs pages** — they are a structured text dataset located at:

```
simulators/synthetic-corpus/
├── it/
│   ├── loom/           # SOP-LOOM-001..005 (weaving)
│   ├── dyeing/         # SOP-DYE-001..005 (dyeing)
│   ├── spinning/       # SOP-SPN-001..005 (spinning)
│   └── quality_grading/ # SOP-QLT-001..005 (quality grading)
└── en/
    ├── loom/
    ├── dyeing/
    ├── spinning/
    └── quality_grading/
```

Browse the corpus directly: [simulators/synthetic-corpus/ on GitHub](https://github.com/smart-factory-transformation/smart-factory-transformation/tree/main/simulators/synthetic-corpus).

!!! note "Mantis context"
    The corpus is calibrated to an Italian medium-sized textile plant (Mantis Textile Group reference): outdoor apparel fabric production, cotton/wool/linen blend yarns, two-shift operation. SOPs use European units and textile terminology aligned with UNI EN ISO standards.

## Status and review

Each SOP exposes a `status` field in its frontmatter:

| Value | Meaning |
|-------|---------|
| `reviewed` | Technical content reviewed by a human — ready for Phase 5 retrieval |
| `draft-unreviewed` | Claude-generated draft — **do not use as ground truth** without review |
| `deprecated` | Superseded by a newer version |

This scheme follows the **D-25** hybrid contract (LLM draft + human review): Claude generates structured drafts; the user reviews and promotes them to `reviewed`.

**Phase 5 retrieval contract (Open Question #5):** Phase 5 agents default-filter to `status: reviewed` only. SOPs with `draft-unreviewed` are accessible only via explicit caller opt-in, preventing unreviewed drafts from becoming false ground truth in RAG evaluation.

## Frontmatter schema

Every SOP follows the schema defined in [`packages/sft-domain/src/sft_domain/schemas/sop.schema.json`](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/packages/sft-domain/src/sft_domain/schemas/sop.schema.json).

Required fields:

| Field | Type | Example |
|-------|------|---------|
| `id` | `string` | `SOP-LOOM-001` |
| `title` | `string` | `Broken end diagnosis and repair` |
| `version` | `string` | `1.0` |
| `lang` | `it` \| `en` | `en` |
| `asset` | `string` | `loom` |
| `asset_family` | `string` | `weaving` |
| `role` | `string` | `technician` |
| `hazard_level` | `low` \| `medium` \| `high` | `medium` |
| `estimated_duration_min` | `integer` | `45` |
| `status` | `reviewed` \| `draft-unreviewed` \| `deprecated` | `draft-unreviewed` |
| `created_in_phase` | `integer` | `2` |

CI validation is performed by `python3 scripts/validate-corpus-frontmatter.py --corpus-dir simulators/synthetic-corpus`.

## Examples

Representative SOPs from the corpus:

- **SOP-LOOM-001** — [Broken end diagnosis (IT)](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/it/loom/SOP-LOOM-001-troubleshoot-broken-end-it.md) / [EN](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/en/loom/SOP-LOOM-001-troubleshoot-broken-end-en.md)
- **SOP-DYE-001** — [Dyebath preparation (IT)](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/it/dyeing/SOP-DYE-001-bath-preparation-it.md) / [EN](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/en/dyeing/SOP-DYE-001-bath-preparation-en.md)
- **SOP-SPN-001** — [Spindle calibration (IT)](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/it/spinning/SOP-SPN-001-spindle-calibration-it.md) / [EN](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/en/spinning/SOP-SPN-001-spindle-calibration-en.md)
- **SOP-QLT-001** — [4-point grading inspection (IT)](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/it/quality_grading/SOP-QLT-001-four-point-grading-it.md) / [EN](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/en/quality_grading/SOP-QLT-001-four-point-grading-en.md)
- **SOP-LOOM-002** — [Warp tension drift (IT)](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/it/loom/SOP-LOOM-002-warp-tension-drift-it.md) / [EN](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/en/loom/SOP-LOOM-002-warp-tension-drift-en.md)
