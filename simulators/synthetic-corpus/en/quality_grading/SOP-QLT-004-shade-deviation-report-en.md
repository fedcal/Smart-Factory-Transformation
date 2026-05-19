---
acl_level: internal
asset: inspection table
asset_family: quality_grading
audience: quality
created_in_phase: 2
estimated_duration_min: 30
hazard_level: low
id: SOP-QLT-004
lang: en
prerequisites:
- SOP-QLT-001
- SOP-DYE-003
related_glossary:
- deviazione_tono
- delta_e
- spettrofotometro
- solidita_colore
- ispezione_rotolo
- controllo_qualita_tessile
role: quality-manager
status: reviewed
tags:
- quality
- inspection
- shade-deviation
- reporting
- quality-manager
title: Shade deviation report for dye lot
version: '1.0'
---

# Shade deviation report for dye lot

## Scope

This SOP describes the procedure for drafting the formal **deviazione_tono** (shade deviation report) for a dye lot that has exceeded the accepted **delta_e** threshold or shows inter-roll or intra-roll chromatic variations above the agreed tolerance.

The **deviazione_tono** report is the formal document that:
- Traces the nature and extent of the chromatic problem
- Provides the dyehouse department with diagnostic information
- Forms the basis for the corrective action decision (rectification, re-dyeing, concession, downgrading)
- Serves as documentary evidence for customer disputes

The procedure applies to lots with **delta_e** CMC > 1.0 or with visible **screziatura** (streakiness) defects classified as non-conforming in the shade verification process (SOP-DYE-003).

## Prerequisites

- The lot has already passed shade verification (SOP-DYE-003) with a NON-CONFORMING or CONDITIONAL result.
- Colorimetric measurement data (L*, a*, b* values per sample) are available from the SOP-DYE-003 report.
- The reference standard sample is available in the laboratory.
- The **spettrofotometro** is calibrated.
- The **deviazione_tono** report form (company or standardised) is available.

## Tools and PPE

- Bench **spettrofotometro** (calibrated, d8 aperture, D65)
- Approved reference standard sample (approved by customer or quality management)
- Non-conforming lot samples (one per roll, taken in standard position)
- D65 lightbox for visual assessment
- ISO 105-A02 grey scale
- Thin cotton gloves

## Step-by-step Procedure

1. **Collect all available measurement data.** Retrieve from the SOP-DYE-003 report the L*, a*, b* and **delta_e** CMC values for each lot sample. If data is incomplete (not all rolls were sampled): carry out the additional measurements before proceeding to report drafting.

2. **Build the lot deviation matrix.** Organise data in a matrix: roll × position (beginning, middle, end) × **delta_e** CMC. Calculate:
   - Average **delta_e** for the lot
   - Maximum **delta_e** for the lot (roll and position)
   - Inter-roll variation range (delta_e_max - delta_e_min)
   - Rolls and positions exceeding the acceptance threshold

3. **Characterise the deviation direction.** Analyse L*, a*, b* values to determine the **deviazione_tono** direction:
   - Reduced L* (sample darker than standard): excess dyestuff or too-high fixation
   - Excess a* (more red): triple-dyestuff imbalance towards the red component
   - Excess b* (more yellow): process thermal profile not optimal for the dyestuff used
   The deviation direction is essential for orienting the corrective action in the dyehouse.

4. **Classify the non-conformance type.** Based on the matrix:
   - **Uniform deviation:** all rolls have the same **delta_e** in the same direction — indicates a systematic error in the recipe or process (dyestuff dosing, pH, thermal profile)
   - **Inter-roll deviation:** rolls have different **delta_e** from each other — indicates process variability in the machine (non-uniform temperature between cycles, liquor ratio variation)
   - **Intra-roll deviation:** beginning and end of the same roll have different **delta_e** — indicates drift during the cycle (pH or temperature variation in the course of the cycle)

5. **Document visual assessment on lightbox.** Position the most critical lot sample and the standard sample on the D65 lightbox. Assess visually and note in the report: whether **deviazione_tono** is visible, from which distance (cm), and whether it is uniform or patchy (**screziatura** puntiform vs. homogeneous **deviazione_tono**).

6. **Define the recommended corrective action.** Based on non-conformance type and **delta_e** magnitude, indicate the recommended action in the report:
   - **delta_e** 1.0-1.5, uniform deviation: in-machine dyeing rectification (corrective bath with dyestuff in the opposite direction to the deviation)
   - **delta_e** 1.5-2.5, inter-roll deviation: separate re-dyeing by roll or by homogeneous group
   - **delta_e** > 2.5 or structural **screziatura**: full re-dyeing or downgrading; assess economically with the commercial manager
   - Deviation within 1.0-1.2 and non-visual: customer concession proposal with colorimetric documentation attached

7. **Complete the formal shade deviation report.** Structure the report per the company format including: lot number, article, dyeing date, customer (if known), tabulated colorimetric values, deviation matrix, classified NC type, visual assessment, recommended corrective action, quality manager signature.

8. **Distribute the report and initiate the corrective action process.** Send the report to the dyehouse supervisor (for technical corrective action) and the commercial manager (if the lot is destined for a customer with contractually defined standards). Update lot status in the management system: QUARANTINE + corrective action in progress.

## Verification

- The **deviazione_tono** report is completed with all required sections (matrix, NC type, recommended action).
- The recommended corrective action is consistent with the type of non-conformance diagnosed.
- The report has been distributed to all specified recipients and receipt confirmed.
- Lot status in the management system is updated with the NC report number.

## Troubleshooting

**L*, a*, b* values measured are inconsistent between samples from the same roll (variation > 0.5 units):**
- Verify measurement conditions: same operator, same **spettrofotometro**, same d8 aperture. If variability persists: the fabric has a structural **screziatura** (not a measurement issue). Document **screziatura** as an additional defect to the uniform **deviazione_tono**.

**Unable to determine the deviation direction (grey deviation — only L* out of range, a* and b* within norm):**
- A purely L* deviation (intensity only, no hue drift) indicates a total dyestuff concentration problem (too much or too little). The corrective action is simpler: only concentration correction with the same triple dyestuff.

**Customer does not accept the concession proposal and requests re-dyeing:**
- Document the customer response in the NC report. Start the re-dyeing procedure. Verify that the re-dyeing machine is internally washed before inserting the fabric (risk of contamination from the previous dyestuff).

## References

- IT textile glossary: [deviazione_tono](../../docs/docs/glossary.md#deviazione_tono), [delta_e](../../docs/docs/glossary.md#delta_e), [screziatura](../../docs/docs/glossary.md#screziatura)
- Related SOPs: SOP-DYE-003 (lot shade verification), SOP-DYE-002 (colour matching), SOP-QLT-001 (fabric inspection)
- Reference standards: CIE L*a*b* D65, ISO 105-A02 (grey scale), ISO 105-A03 (staining scale)
