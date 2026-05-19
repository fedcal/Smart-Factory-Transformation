---
acl_level: internal
asset: jet dyeing machine
asset_family: dyeing
audience: quality
created_in_phase: 2
estimated_duration_min: 30
hazard_level: low
id: SOP-DYE-003
lang: en
prerequisites:
- SOP-DYE-001
related_glossary:
- delta_e
- spettrofotometro
- deviazione_tono
- solidita_colore
- tintura
- ispezione_rotolo
role: quality-manager
status: reviewed
tags:
- dyeing
- shade-verification
- quality
- quality-manager
title: Shade verification and dye lot approval
version: '1.0'
---

# Shade verification and dye lot approval

## Scope

This SOP describes the shade verification and final approval procedure for a dye lot before release to the next department (finishing or warehouse). The verification includes colorimetric measurement with **spettrofotometro** (spectrophotometer), comparison with the approved standard and shade uniformity verification across the rolls of the lot.

The procedure applies to every completed dye lot, regardless of article or colour. The approval decision rests with the quality manager or an authorised quality inspector. A lot with **deviazione_tono** (shade deviation) exceeding the agreed tolerance cannot be released without explicit authorisation from the quality manager.

## Prerequisites

- The dye lot is complete and the rolls are dry (flat dry or tumble dry per procedure).
- The approved colour standard (or Recipe Sheet with target L*, a*, b* values) is available in the laboratory.
- The **spettrofotometro** is calibrated (daily verification on white and black tile performed and documented).
- Fabric samples have been taken from the beginning, middle and end of each roll in the lot (or per the company sampling plan).

## Tools and PPE

- Bench **spettrofotometro** (d8 aperture, D65 illuminant, 10° observer)
- Standardised sample holder (to ensure consistent sample flatness and pressure)
- Shade report form (paper or digital in the quality system)
- ISO 105-A02 grey scale (for supplementary visual evaluation)
- Standard D65 light (colour assessment lightbox) for visual inspection

## Step-by-step Procedure

1. **Prepare fabric samples for measurement.** For each lot roll, take 10×10 cm samples from the beginning, middle and end of the roll (3 samples per roll). Flatten each sample without ironing (ironing pressure alters surface chromatic properties). Condition for at least 30 minutes in an environment with humidity 65±5% RH and temperature 20±2 °C (ISO 139 standard conditions).

2. **Measure the reference standard sample.** Position the standard sample on the **spettrofotometro** sample holder (double layer for opacity). Carry out 3 measurements rotating the sample 90° between each measurement. Record the average L*, a*, b* values and verify repeatability (deviation between readings < 0.1 unit).

3. **Measure the lot samples.** For each production sample: position on the sample holder and measure with the same method (3 readings at 90°). Calculate the **delta_e** CMC or CIEDE2000 against the standard for each sample.

4. **Evaluate the delta_e distribution within the lot.** Build the results matrix: roll × position (beginning, middle, end) × **delta_e**. Evaluate:
   - Maximum **delta_e** in the lot: must be < 1.0 (typical production tolerance), or < 0.8 for premium articles.
   - Difference in **delta_e** between the beginning and end of the same roll (intra-roll uniformity): must be < 0.5 to avoid visible **deviazione_tono** within the roll.
   - Difference in **delta_e** between rolls of the lot (inter-roll uniformity): variation > 0.8 between different rolls of the same lot is acceptable only if the rolls are destined for separate batches.

5. **Carry out visual assessment on D65 lightbox.** Position the sample with the highest **delta_e** and the standard sample on the D65 lightbox. Evaluate visually under D65 and incandescent light (metamerism check): if the difference is visible under both lighting conditions, the lot cannot be approved as a single batch.

6. **Make the approval decision.** Apply the company decision grid:
   - **delta_e** CMC < 1.0, no visual **deviazione_tono**, intra-roll uniformity OK → CONFORMING: lot approved for release.
   - **delta_e** CMC 1.0-2.0, **deviazione_tono** not visible under standard D65 → CONDITIONAL CONFORMITY: request customer written authorisation for possible release with concession.
   - **delta_e** CMC > 2.0 or visible **deviazione_tono** → NON-CONFORMING: block the lot, start root-cause analysis (SOP-DYE-002) and decide corrective action (rectification / re-dyeing / downgrading).

7. **Complete the shade approval report.** Enter in the quality system: lot number, article, date, delta_e values for each sample, decision (CONFORMING / CONDITIONAL / NON-CONFORMING), quality manager signature. For NON-CONFORMING lots: open a non-conformance in the system and indicate the planned corrective action.

8. **Release or block the lot.** For conforming lots: issue the release bulletin and update the lot status in the management system (status: CONFORMING). For non-conforming lots: affix a red block label to all rolls in the lot and segregate physically in the quarantine area.

## Verification

- All lot samples have **delta_e** CMC within the agreed tolerance (< 1.0 for standard production).
- The shade approval report is completed, signed and archived in the quality system.
- Non-conforming lots are physically segregated and identified with red labels.
- Lot status is updated in the management system (CONFORMING / QUARANTINE / NON-CONFORMING).

## Troubleshooting

**Spectrophotometric measurement shows non-reproducible values (variation > 0.3 between repetitions):**
- Verify sample flatness on the sample holder: folds or non-uniform thicknesses cause measurement variability. Cut a fresh sample from the same point and repeat.
- Check **spettrofotometro** calibration: if the deviation persists across multiple samples, re-calibrate.

**Delta_e is borderline (0.8-1.2) and decision is uncertain:**
- Request a second visual comparison by a second qualified inspector independently: in case of discordance > 0.2 points in visual judgement, apply the more conservative classification.
- Consider the article end-use context: a **delta_e** of 1.1 for upholstery fabric is less critical than the same value for a solid-colour garment article.

**Lot with conforming delta_e but visual deviation between rolls (metamerism):**
- This indicates that the rolls have the same **delta_e** against the standard but a different reflectance curve: metamerism problem from a different dyestuff batch. Separate the rolls into distinct chromatic batches and document in the report.

## References

- IT textile glossary: [delta_e](../../docs/docs/glossary.md#delta_e), [deviazione_tono](../../docs/docs/glossary.md#deviazione_tono), [spettrofotometro](../../docs/docs/glossary.md#spettrofotometro)
- Related SOPs: SOP-DYE-001 (dye bath preparation), SOP-DYE-002 (colour matching), SOP-QLT-004 (shade deviation report)
- Reference standards: ISO 105-A02 (grey scale), CIE L*a*b* D65, ISO 139 (textile conditioning)
