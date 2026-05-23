---
lang: it
agent: event-taxonomy
requirements:
  - MNT-05
tags:
  - agents
  - maintenance
  - MNT-05
  - taxonomy
---

# Tassonomia degli eventi di manutenzione

Questa pagina documenta la tassonomia degli eventi di manutenzione
(`reason_code`) usata dal cluster maintenance di **Mantis Textile Group**.

La sorgente canonica è
`packages/sft-domain/src/sft_domain/failure_modes.yaml`
(07-02 extension D-MNT-TAX); il validator CI
`scripts/validate-failure-modes.py` assicura:

- unicità del `reason_code` nell'intero registro;
- risoluzione di `intervention_steps_sop_id` verso il corpus SOP Phase 5;
- coerenza dei campi `mttr_target_minutes` e `severity`.

## Convenzione di Naming

I `reason_code` seguono la convenzione ispirata allo spirito ISO 14224:

```
<MODULO>-<ABBREVIAZIONE_DIFETTO>-<NNN>
```

Esempi:

| Codice | Modulo | Difetto | Numero |
|--------|--------|---------|--------|
| `WEAVING-BE-001` | Tessitura | Broken End | 001 |
| `WEAVING-MP-002` | Tessitura | Mispick | 002 |
| `SPINNING-SL-001` | Filatura | Slub | 001 |
| `DYEING-SD-001` | Tintura | Shade Deviation | 001 |

I moduli riconosciuti sono: `WEAVING`, `SPINNING`, `DYEING`.
I numeri sono assegnati in ordine di registrazione nel registry e non vengono
riutilizzati dopo una deprecazione.

## Registro reason_code

La tabella seguente rispecchia il contenuto attuale di `failure_modes.yaml`
per i difetti che hanno un blocco `maintenance:` con `reason_code` definito.

| reason_code | Nome IT | Nome EN | Asset families | MTTR target (min) | SOP ID | Check interval (h) | Severity |
|---|---|---|---|---|---|---|---|
| `WEAVING-BE-001` | rottura filo ordito | broken end | weaving | 30 | SOP-LOOM-001 | 168 | medium |
| `WEAVING-MP-002` | trama mancata | mispick | weaving, quality_grading | 15 | SOP-LOOM-002 | — | medium |
| `WEAVING-SF-003` | difetto cimosa | selvage fault | weaving | 45 | SOP-LOOM-004 | 336 | low |
| `SPINNING-SL-001` | ingrossamento filato | slub | spinning, quality_grading | 20 | SOP-SPN-004 | — | medium |
| `SPINNING-NP-002` | filato neppy | neppy yarn | spinning, quality_grading | 25 | SOP-SPN-002 | — | medium |
| `DYEING-SD-001` | deviazione cromatica | shade deviation | dyeing, quality_grading | 60 | SOP-DYE-003 | — | medium |
| `DYEING-UD-002` | tintura non uniforme | unlevel dyeing | dyeing, quality_grading | 90 | SOP-DYE-001 | 720 | medium |

**Totale reason_code documentati: 7** (corrispondenti ai 7 failure mode con
blocco `maintenance:` nel registry D-65).

## Uso cross-agent

| Agente | Uso del reason_code |
|--------|---------------------|
| `PredictiveMaintenance` | Non usa direttamente il `reason_code`; opera su `health_index` calcolato dai sensori. Il `reason_code` è incluso nel payload NATS di trigger da `AnomalyDetector` come contesto opzionale. |
| `RCASpecialist` | Il `problem_statement` spesso include il `reason_code` dell'evento scatenante; `rag_search` usa il codice per filtrare le SOP pertinenti. |
| `MaintenanceCoach` | Il `reason_code` in input seleziona il corpus SOP corretto (`rag_search`) e il thread Coach è iniziato con il codice come contesto primario. |
| `DowntimeAnalyzer` | Persiste il `reason_code` in ogni riga `maintenance.downtime_events`; l'analisi Pareto `top_5_downtime_reason_codes` aggrega per questo campo. |

## Aggiungere una nuova reason_code

1. **Aggiungere la voce nel registry**:
   Modificare `packages/sft-domain/src/sft_domain/failure_modes.yaml`
   aggiungendo un entry con blocco `maintenance:` contenente almeno:
   ```yaml
   maintenance:
     reason_code: <MODULO>-<ABBR>-<NNN>
     mttr_target_minutes: <int>
     intervention_steps_sop_id: <SOP-ID>
   ```

2. **Aggiungere la SOP corrispondente**:
   Il file SOP referenziato da `intervention_steps_sop_id` deve esistere nel
   corpus `simulators/synthetic-corpus/` prima che il validator CI accetti la PR.

3. **Eseguire il validator**:
   ```bash
   python scripts/validate-failure-modes.py
   ```
   Il validator verifica: unicità del `reason_code`, esistenza del `sop_id`
   nel corpus, coerenza di `severity` rispetto agli altri difetti del modulo.

4. **Aggiornare questa pagina**:
   Aggiungere la nuova riga alla tabella "Registro reason_code" sopra e
   incrementare il contatore "Totale reason_code documentati".

5. **PR review**:
   Il reviewer deve verificare che il `reason_code` rispetti la convenzione
   di naming (ISO 14224 spirit) e che `mttr_target_minutes` sia basato su
   dati storici o stime ingegneristiche documentate.
