---
title: Procedure (SOP) sintetiche
description: Corpus sintetico di Standard Operating Procedures per il dominio tessile manifatturiero (KNW-10)
tags:
  - sop
  - corpus
  - knowledge
---

# Procedure (SOP) sintetiche

Questo corpus raccoglie 20 **Standard Operating Procedure** (SOP) bilingui (IT + EN) per il dominio tessile manifatturiero, prodotte come substrato di conoscenza per la piattaforma agentica Smart Factory Transformation (requisito KNW-10).

Le SOP sono strutturate per il **retrieval granulare**: ogni documento ha frontmatter YAML validato che espone `asset`, `role`, `hazard_level`, `status` e altri campi filtrabili dagli agenti di Phase 5 (BGE-M3 + Qdrant).

## Dove vivono le SOP

Le SOP **non sono pagine MkDocs** — sono un dataset di testo strutturato collocato in:

```
simulators/synthetic-corpus/
├── it/
│   ├── loom/           # SOP-LOOM-001..005 (tessitura)
│   ├── dyeing/         # SOP-DYE-001..005 (tintoria)
│   ├── spinning/       # SOP-SPN-001..005 (filatura)
│   └── quality_grading/ # SOP-QLT-001..005 (controllo qualità)
└── en/
    ├── loom/
    ├── dyeing/
    ├── spinning/
    └── quality_grading/
```

Per navigare il corpus direttamente: [simulators/synthetic-corpus/ su GitHub](https://github.com/smart-factory-transformation/smart-factory-transformation/tree/main/simulators/synthetic-corpus).

!!! note "Mantis context"
    Il corpus è calibrato su uno stabilimento tessile italiano di medie dimensioni (riferimento Mantis Textile Group): produzione di tessuti per abbigliamento outdoor, mix filati cotone/lana/lino, due turni produttivi. Le SOP usano unità di misura europee e terminologia di settore italiana/inglese conforme agli standard UNI EN ISO.

## Stato e revisione

Ogni SOP espone un campo `status` nel frontmatter:

| Valore | Significato |
|--------|-------------|
| `reviewed` | Contenuto tecnico revisionato dall'utente — pronto per il retrieval di Phase 5 |
| `draft-unreviewed` | Bozza generata da Claude — **non usare come ground truth** senza revisione |
| `deprecated` | Sostituita da versione più recente |

Questo schema segue il contratto ibrido **D-25** (LLM draft + human review): Claude genera le bozze in formato strutturato; l'utente le rivede e promuove a `reviewed`.

**Contratto di retrieval Phase 5 (Open Question #5):** gli agenti di Phase 5 filtrano di default solo SOP con `status: reviewed`. Le SOP `draft-unreviewed` sono accessibili solo tramite opt-in esplicito del chiamante. Questo evita che errori tecnici nelle bozze non revisionate diventino falsa ground truth nei test RAG.

## Schema frontmatter

Ogni SOP segue lo schema definito in [`packages/sft-domain/src/sft_domain/schemas/sop.schema.json`](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/packages/sft-domain/src/sft_domain/schemas/sop.schema.json).

Campi obbligatori:

| Campo | Tipo | Esempio |
|-------|------|---------|
| `id` | `string` | `SOP-LOOM-001` |
| `title` | `string` | `Diagnosi e riparazione rottura trama` |
| `version` | `string` | `1.0` |
| `lang` | `it` \| `en` | `it` |
| `asset` | `string` | `loom` |
| `asset_family` | `string` | `weaving` |
| `role` | `string` | `technician` |
| `hazard_level` | `low` \| `medium` \| `high` | `medium` |
| `estimated_duration_min` | `integer` | `45` |
| `status` | `reviewed` \| `draft-unreviewed` \| `deprecated` | `draft-unreviewed` |
| `created_in_phase` | `integer` | `2` |

La validazione è eseguita in CI da `python3 scripts/validate-corpus-frontmatter.py --corpus-dir simulators/synthetic-corpus`.

## Esempi

Alcune SOP rappresentative del corpus:

- **SOP-LOOM-001** — [Diagnosi rottura trama (IT)](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/it/loom/SOP-LOOM-001-troubleshoot-broken-end-it.md) / [EN](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/en/loom/SOP-LOOM-001-troubleshoot-broken-end-en.md)
- **SOP-DYE-001** — [Preparazione bagno di tintura (IT)](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/it/dyeing/SOP-DYE-001-bath-preparation-it.md) / [EN](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/en/dyeing/SOP-DYE-001-bath-preparation-en.md)
- **SOP-SPN-001** — [Calibrazione fusi (IT)](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/it/spinning/SOP-SPN-001-spindle-calibration-it.md) / [EN](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/en/spinning/SOP-SPN-001-spindle-calibration-en.md)
- **SOP-QLT-001** — [Ispezione 4-point grading (IT)](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/it/quality_grading/SOP-QLT-001-four-point-grading-it.md) / [EN](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/en/quality_grading/SOP-QLT-001-four-point-grading-en.md)
- **SOP-LOOM-002** — [Deriva tensione ordito (IT)](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/it/loom/SOP-LOOM-002-warp-tension-drift-it.md) / [EN](https://github.com/smart-factory-transformation/smart-factory-transformation/blob/main/simulators/synthetic-corpus/en/loom/SOP-LOOM-002-warp-tension-drift-en.md)
