---
id: SOP-QLT-005
title: Lot acceptance procedure
version: "1.0"
lang: en
asset: inspection table
asset_family: quality_grading
role: quality-manager
hazard_level: low
estimated_duration_min: 60
prerequisites:
  - SOP-QLT-001
  - SOP-QLT-004
related_glossary:
  - accettazione_lotto
  - aql
  - livello_qualita_accettabile
  - ispezione_4_punti
  - lotto_tintoriale
tags:
  - quality
  - acceptance
  - inspection
audience: operations
status: reviewed
created_in_phase: 2
---

# Lot acceptance procedure

## Scope

This SOP describes the **accettazione_lotto** (lot acceptance) procedure for a finished or semi-finished fabric lot destined for internal delivery (next department) or customer shipment. The procedure integrates the results of the **ispezione_4_punti** (four-point inspection, SOP-QLT-001) and the shade deviation report (SOP-QLT-004) into a formal acceptance or rejection decision per the **livello_qualita_accettabile** (AQL — Acceptable Quality Level) agreed with the customer.

The procedure applies to all dye lots that have passed the fabric inspection and shade verification phases and for which a formal acceptance decision is required before release. The result is a Lot Acceptance Record (LAR) signed by the quality manager, which constitutes the official lot release document.

The reference **aql** level is defined per article/customer in the supply specifications. In the absence of customer specifications, the company standard **aql** applies (2.5% for major defects, 4.0% for minor defects). The final decision follows the AQL sampling tables (ISO 2859-1 or MIL-STD-105E).

## Prerequisites

- Fabric inspection (SOP-QLT-001) is complete for all lot rolls with signed reports.
- The shade deviation report (SOP-QLT-004) is available if the lot had chromatic non-conformances.
- The **ispezione_4_punti** data (score per roll, classification, defect count by type) are consolidated in a lot summary sheet.
- The **aql** specification applicable to the article and customer is available (from management system or article master data).
- The quality manager is available to review and sign the LAR.

## Tools and PPE

- Lot summary sheet (aggregation of SOP-QLT-001 data for all rolls)
- AQL sampling tables (ISO 2859-1 / MIL-STD-105E) or equivalent software
- Individual roll inspection reports (SOP-QLT-001)
- Shade deviation report (SOP-QLT-004) if available
- LAR (Lot Acceptance Record) company form
- Calculator or spreadsheet for **aql** calculation
- Thin cotton gloves (for any re-inspection of physical samples)

## Step-by-step Procedure

1. **Consolidate lot inspection data.** Collect the **ispezione_4_punti** reports (SOP-QLT-001) for all lot rolls. Complete the lot summary sheet with: roll number, inspected length (m), total defect score, score per 100 m, roll classification (First / Second / Cutting), defect count by type (mispick, repaired end break, warp streak, weft defect, stains, holes, other). Verify that all lot rolls have a signed inspection report.

2. **Calculate the aggregate lot score.** From the summary sheet, calculate:
   - Lot average score = (sum of scores per 100 m for all rolls) / number of rolls
   - Percentage First quality rolls = (First rolls / total rolls) × 100
   - Percentage Second quality rolls = (Second rolls / total rolls) × 100
   - Percentage Cutting rolls = (Cutting rolls / total rolls) × 100

   | Roll classification | Typical lot acceptance threshold    |
   |---------------------|--------------------------------------|
   | First quality       | ≥ 80% of rolls                       |
   | Second quality      | ≤ 20% of rolls                       |
   | Cutting             | 0% (no cutting rolls permitted)      |

3. **Determine the AQL sampling level.** Based on lot size (total number of rolls), identify the applicable AQL sampling level per ISO 2859-1 tables (Inspection Level II standard). Determine the number of samples to inspect (n) and the acceptance (Ac) and rejection (Re) numbers for the applicable **aql** levels (2.5% for major defects, 4.0% for minor defects).

   Example for a lot of 20-50 rolls (sampling letter G):
   - n = 32 rolls to inspect (or entire population if lot < 32)
   - Ac = 2 (acceptance if defects found ≤ 2), Re = 3 (rejection if defects found ≥ 3) for **aql** 2.5

4. **Carry out AQL sampling inspection (if not already covered by SOP-QLT-001).** If the number of rolls inspected in SOP-QLT-001 is below the sample size required by the AQL tables: randomly select additional rolls to inspect and complete the **ispezione_4_punti**. For each AQL-sampled roll, classify defects found as:
   - **Major defect:** defect that compromises fabric functionality or appearance (holes, tears, permanent stains, weft defects > 150 mm)
   - **Minor defect:** defect that does not compromise functionality but reduces perceived quality (washable stains, small visible defects < 75 mm, acceptable repairs)

5. **Integrate shade verification into the lot judgement.** Consult the shade deviation report (SOP-QLT-004) if available. Classify the lot shade situation:
   - **Shade conforming:** all rolls within the chromatic **livello_qualita_accettabile** (delta_E CMC ≤ 1.0 on all samples)
   - **Conditionally conforming:** delta_E between 1.0 and 1.5 with accepted and documented customer concession
   - **Shade non-conforming:** delta_E > 1.5 without customer concession, or structural **screziatura** not accepted

   A shade non-conforming lot cannot be accepted regardless of the **ispezione_4_punti** result.

6. **Apply AQL decision rules.** Compare the number of major and minor defects found in the AQL sample with the acceptance and rejection numbers from the tables:
   - Major defects found ≤ Ac (AQL 2.5%) AND minor defects found ≤ Ac (AQL 4.0%): **LOT ACCEPTED**
   - Major defects found ≥ Re (AQL 2.5%) OR minor defects found ≥ Re (AQL 4.0%): **LOT REJECTED**
   - Borderline result (Ac < found < Re): proceed with additional reduced sampling or escalate to senior quality manager

7. **Draft the Lot Acceptance Record (LAR).** Complete the LAR form with: lot number, article, customer (if known), inspection completion date, total number of rolls in lot, AQL sample size inspected, number of major and minor defects found, AQL result (ACCEPTED / REJECTED), shade situation (CONFORMING / CONDITIONAL / NON-CONFORMING), aggregate lot classification (% First, % Second, % Cutting), final decision (ACCEPTED / REJECTED / QUARANTINE), quality manager signature and date.

8. **Execute post-decision actions.** Based on the final decision:
   - **ACCEPTED:** affix green acceptance labels to all lot rolls, update lot status in management system (RELEASED), start shipment or internal transfer process
   - **REJECTED:** physically segregate the lot in the quarantine area, affix red block labels to all rolls, open a Non-Conformance in the quality system with LAR reference, initiate corrective action procedure (rectification, re-dyeing, scrapping, downgrading)
   - **QUARANTINE (AQL borderline):** segregate the lot, suspend the decision, initiate additional sampling or senior quality manager review within 24 hours

## Verification

- The LAR is completed in all sections and signed by the quality manager.
- Lot status in the management system is consistently updated with the LAR decision (RELEASED / BLOCKED / QUARANTINE).
- Accepted rolls are physically identified with green labels and rejected rolls with red labels.
- If the lot was rejected, a Non-Conformance has been opened in the quality system with the LAR number as reference.
- The LAR is archived in the lot quality file and accessible for audit.

## Troubleshooting

**The number of rolls inspected in SOP-QLT-001 is below the required AQL sample (e.g. 100-roll lot with AQL sample of 50 but only 20 inspected):**
- Resume inspection of the missing rolls before proceeding to the LAR decision. It is not possible to accept a lot without reaching the minimum AQL sample size. If time is critical: contact the senior quality manager to assess whether a reduced sampling plan is applicable (Inspection Level I instead of Level II) with documented justification.

**AQL result is borderline (between Ac and Re) and acceptance or rejection cannot be clearly determined:**
- Proceed with additional sampling (ISO 2859-1 switching rules: switch to tightened inspection if the previous lot was also borderline). If the tightened sampling result is still borderline: mandatory escalation to senior quality manager. Document the decision path in the LAR.

**Discordance between customer's qualitative judgement and AQL result (customer rejects a lot that passed AQL):**
- Document the customer dispute in the LAR. Initiate a joint re-inspection with the customer on an agreed sample of rolls. If the re-inspection confirms the AQL result: negotiate with the customer the possible application of a more restrictive **aql** in future contracts. If the re-inspection detects defects not found in the first inspection: open an internal Non-Conformance for the inspection process and re-evaluate inspector training.

**Lot has more than 20% Second quality rolls but all defects are minor:**
- The 20% Second quality threshold is a process quality indicator, not an automatic AQL rejection criterion (AQL rejection is based on the defect count in the sample). Accept the lot if the AQL result is ACCEPTED, but document in the LAR the high Second quality percentage as a process signal to monitor. Communicate to the production department for root-cause analysis.

## References

- IT textile glossary: [accettazione_lotto](../../docs/docs/glossary.md#accettazione_lotto), [aql](../../docs/docs/glossary.md#aql), [livello_qualita_accettabile](../../docs/docs/glossary.md#livello_qualita_accettabile), [ispezione_4_punti](../../docs/docs/glossary.md#ispezione_4_punti), [lotto_tintoriale](../../docs/docs/glossary.md#lotto_tintoriale)
- Related SOPs: SOP-QLT-001 (four-point fabric inspection), SOP-QLT-004 (shade deviation report), SOP-DYE-003 (lot shade verification)
- Reference standards: ISO 2859-1 (Attribute sampling plans), MIL-STD-105E (Sampling procedures and tables), AATCC 96 (Four-Point System), ISO 4660 (textile defect classification)
