---
id: SOP-DYE-002
title: Colour matching procedure for sample dyeing
version: "1.0"
lang: en
asset: jet dyeing machine
asset_family: dyeing
role: technician
hazard_level: low
estimated_duration_min: 60
prerequisites:
  - SOP-DYE-001
related_glossary:
  - tintura
  - delta_e
  - spettrofotometro
  - bagno_colorante
  - deviazione_tono
  - solidita_colore
tags:
  - dyeing
  - color-matching
  - procedure
  - technician
audience: operations
status: reviewed
created_in_phase: 2
---

# Colour matching procedure for sample dyeing

## Scope

This SOP describes the chromatic matching (colour matching) procedure for the production of dye samples during colour development or for the correction of out-of-tolerance batches. The objective is to achieve a **delta_e** CMC value below the agreed threshold relative to the approved reference standard (typically < 1.0 for sample collection, < 0.5 for customer approval sample).

The procedure applies to laboratory-scale dyeing (50-200 g fabric samples) or in a small-capacity sample dyeing machine (**jet_dyeing** of small capacity), with iterative colorimetric measurement and correction cycles. It does not replace the definitive industrial Recipe Sheet: the output of this procedure is the sample recipe to be validated in production.

## Prerequisites

- The colour reference standard is available (customer colour card or approved physical sample).
- The dyehouse laboratory has issued a starting recipe based on a computational prediction (colour matching software) or on a historical recipe for similar colours.
- The **spettrofotometro** is calibrated (daily verification on standard white tile performed and documented).
- The substrate to be dyed (fibre type, count, fabric structure) is identical to the standard sample substrate.

## Tools and PPE

- Bench **spettrofotometro** (d8 or d/8 aperture, D65 illuminant, 10° observer)
- Sample dyeing machine or laboratory beaker (50-500 mL capacity for samples)
- Analytical balance (0.001 g resolution for dyestuffs; 0.01 g for auxiliaries)
- Calibrated digital pH meter
- Dyestuff dissolution baths (100 mL graduated beakers)
- Colour matching software (or empirical dyestuff correction tables)
- Anti-splash safety glasses
- Chemical-resistant gloves category III

## Step-by-step Procedure

1. **Dye the first sample with the starting recipe.** Prepare the **bagno_colorante** following the starting recipe issued by the laboratory (dyestuff concentration, auxiliaries, pH, thermal cycle). Dye the substrate sample (50-100 g) in the sample dyeing machine. Dry the sample per the standard method (flat dry 60 °C, 15 minutes).

2. **Measure the delta_e of the first sample.** Position the dyed sample on the **spettrofotometro** portacampioni (sample holder) and measure at three points (edge, centre, opposite edge). Record the average L*, a*, b* values and calculate the **delta_e** CMC against the standard. A **delta_e** CMC > 3.0 on the first attempt indicates that the starting recipe needs significant correction.

3. **Analyse the deviation direction.** Compare the sample L*, a*, b* values with the standard:
   - Lower L*: sample is darker → reduce total dyestuff concentration by 5-15%.
   - Excess positive a* (+ red): reduce the red component or increase the green component of the recipe.
   - Excess positive b* (+ yellow): reduce the yellow component or adjust the ratio among the triple dyestuffs.
   Use the colour matching software to calculate the correction or apply the laboratory empirical correction table.

4. **Prepare and dye the corrected sample.** Apply the calculated correction to the recipe. Dye a second sample on the same substrate. Dry and measure again. If **delta_e** CMC is < 1.5: proceed to fastness verification. If > 1.5: repeat the correction from step 3 (maximum 3 iterations before consulting the dyehouse supervisor).

5. **Verify colour fastness of the approved sample.** On the sample with **delta_e** CMC < 1.0, carry out the wash fastness test ISO 105-C06 (method C1S, 40 °C, 30 minutes with standard detergent). Measure **delta_e** after washing: it must remain < 1.0 for acceptable sample-level fastness.

6. **Document the final sample recipe.** Complete the sample recipe sheet: substrate, date, dyestuffs (trade name, concentration % o.w.f.), auxiliaries, pH, thermal cycle, pre/post-wash delta_e result, technician signature. This sheet is the basis for the subsequent industrial Recipe Sheet.

7. **Submit the sample for approval.** If **delta_e** CMC < 1.0 and colour fastness is conforming: register the sample as approved in the sample management system and archive the recipe. If the customer requires a second sample (step 2 approval): repeat the dyeing cycle with the final recipe and compare the two samples (**delta_e** sample1/sample2 must be < 0.5 to guarantee reproducibility).

8. **Transfer the recipe to the production department.** Send the sample recipe sheet to the dyehouse supervisor for transposition into the industrial Recipe Sheet (adaptation of volumes, machines and thermal cycles to production scale).

## Verification

- The final sample has **delta_e** CMC < 1.0 against the standard (or < 0.5 for customer approval — verify the specific order requirement).
- The ISO 105-C06 wash fastness test gives a conforming result (**deviazione_tono** post-wash measured with **spettrofotometro** within tolerance).
- The sample recipe is completed, signed and archived in the laboratory document management system.
- No **screziatura** or visual **deviazione_tono** is visible on the sample under standard D65 light conditions.

## Troubleshooting

**Delta_e does not fall below 1.5 after 3 correction iterations:**
- Verify that the substrate used is identical in fibre type, count and structure to the standard substrate: substrate differences make computational colour matching unreliable.
- Check that the **spettrofotometro** is calibrated correctly: re-calibrate on white and black tiles before critical measurements.
- Consult the dyehouse supervisor for a review of the dyestuff family: some L*, a*, b* combinations are not achievable with the laboratory's standard triple dyestuffs.

**The sample shows insufficient colour fastness (post-wash delta_e > 1.5):**
- The most probable cause is incomplete dyestuff fixation: verify the fixation bath pH and process temperature. For reactive dyestuffs, increase the fixation alkali dose by 10% and repeat the cycle.
- If the problem persists: consider changing to a dyestuff family with better affinity for the substrate.

**Spectrophotometric measurement is unstable (variation > 0.3 units between three readings):**
- The sample is probably not sufficiently flat or shows surface **deviazione_tono** variation. Fix it with tape on the **spettrofotometro** sample holder without tension. If the variation persists: assess the presence of structural **screziatura** in the sample.

## References

- IT textile glossary: [delta_e](../../docs/docs/glossary.md#delta_e), [spettrofotometro](../../docs/docs/glossary.md#spettrofotometro), [tintura](../../docs/docs/glossary.md#tintura)
- Related SOPs: SOP-DYE-001 (dye bath preparation), SOP-DYE-003 (shade verification), SOP-QLT-004 (shade deviation report)
- Reference standards: ISO 105-C06 (wash colour fastness), ISO 105-A02 (grey scale), CIE Lab D65
