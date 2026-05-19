---
acl_level: internal
asset: jet dyeing machine
asset_family: dyeing
audience: quality
created_in_phase: 2
estimated_duration_min: 90
hazard_level: low
id: SOP-DYE-004
lang: en
prerequisites:
- SOP-DYE-001
- SOP-DYE-003
related_glossary:
- solidita_colore
- delta_e
- spettrofotometro
- tintura
- deviazione_tono
role: quality-manager
status: reviewed
tags:
- dyeing
- fastness
- quality
- quality-manager
title: Colour fastness to washing and rubbing verification
version: '1.0'
---

# Colour fastness to washing and rubbing verification

## Scope

This SOP describes the **solidita_colore** (colour fastness) test procedures for dyed fabrics, focusing on wash fastness (ISO 105-C06) and rubbing fastness (ISO 105-X12). **Solidita_colore** measures the resistance of colour to physical and chemical stresses during fabric use and determines its suitability for the intended market.

The procedure applies to lot acceptance tests (one sample per dye lot) and to laboratory colour development tests. It does not apply to light fastness tests (ISO 105-B02) which require specific equipment (Xenotest): those follow a separate procedure.

Failure to meet minimum **solidita_colore** thresholds causes lot rejection and mandates dyeing rectification or article downgrading.

## Prerequisites

- The dyed fabric sample is dry and conditioned (ISO 139: 65±5% RH, 20±2 °C, minimum 4 hours).
- Multi-fibre adjacent fabrics (ISO 105-F10 or equivalent) are available in the laboratory.
- The **spettrofotometro** is calibrated.
- The laboratory has standard wash equipment (Launder-Ometer or ISO 105-C06 compliant apparatus) and a rubbing dynamometer (Crockmeter ISO 105-X12).
- ISO reference detergent (IEC-A or ECE without optical brightener, depending on test).

## Tools and PPE

- ISO 105-C06 washing apparatus (Launder-Ometer or equivalent)
- Crockmeter ISO 105-X12 (manual or motorised)
- Bench **spettrofotometro** for post-test **delta_e** measurement
- ISO 105-A02 grey scale (for visual evaluation of colour change and staining)
- Precision balance (0.01 g) for detergent weighing
- Bath temperature control thermometer (for washing temperature verification)
- Scissors, needle and thread for composite assembly preparation
- Latex gloves (to avoid sebum contamination during sample preparation)

## Step-by-step Procedure

1. **Prepare the composite sample for wash fastness testing.** Cut a 10×4 cm sample from the fabric under test. Sew an ISO 105-F10 multi-fibre adjacent fabric (or two mono-fibre fabrics per the standard: one of the main substrate, one in cotton) to the sample along one of the 4 cm sides. The composite sample has total dimensions 10×10 cm.

2. **Run the ISO 105-C06 wash test.** Insert the composite sample in a Launder-Ometer capsule with the standard detergent solution (concentration for the selected method — typically C1S: 4 g/L ECE without OBA, 40 °C, 30 minutes, 10 steel balls). Start the cycle. At completion: rinse in cold water and dry the separated components (main sample + adjacent fabric) flat at room temperature.

3. **Evaluate colour change on the main sample.** Compare the post-wash sample with an unwashed sample of the same fabric under D65 light. Assess using ISO 105-A02 grey scale: a grade 4-5 indicates good fastness; grade 3 is the minimum acceptable limit for most garment articles; grade 1-2 indicates insufficient fastness.

4. **Evaluate staining on the adjacent fabric.** Compare each strip of the adjacent fabric with an untreated sample of the same fabric. Assess staining (colour transfer) using the grey scale or staining scale (chromatic scale) ISO 105-A03: a grade ≥ 3 on cotton is the minimum limit for garment articles.

5. **Measure instrumental post-wash delta_e.** With the **spettrofotometro**, measure the **delta_e** between the pre-wash and post-wash sample. The instrumental value complements the grey scale visual assessment and reduces subjectivity. A **delta_e** CMC < 1.0 after washing indicates excellent fastness; 1.0-2.0 acceptable; > 2.0 non-conforming for standard articles.

6. **Run the ISO 105-X12 rubbing fastness test.** Mount the fabric sample (10×4 cm) on the Crockmeter with the fabric to be tested taut and flat. Run the dry test (dry rubbing cloth in conditioned cotton) and the wet test (rubbing cloth moistened: 100% distilled water, 9 N load, 10 rubbing cycles in 10 seconds). Assess staining on the adjacent fabric with the grey scale: minimum acceptable grade 3 dry, grade 2-3 wet.

7. **Complete the colour fastness report.** For each lot tested, complete the sheet: article, lot number, date, test method, grey scale values (colour change + staining), instrumental **delta_e**, result (CONFORMING / NON-CONFORMING), signature. Archive in the quality system.

8. **Communicate result and initiate corrective actions if necessary.** If CONFORMING: attach the report to the lot release bulletin. If NON-CONFORMING: immediately communicate to the dyehouse supervisor, block the lot and start root-cause analysis: wrong dyestuff choice, incomplete fixation, insufficient post-dyeing soaping.

## Verification

- Post-wash sample has grey scale grade ≥ 3 for colour change and ≥ 3 for staining on cotton.
- Post-wash **delta_e** CMC is < 2.0 for standard articles, < 1.0 for premium articles.
- Rubbing test shows staining ≥ 3 dry and ≥ 2 wet on the grey scale.
- The **solidita_colore** report is archived and attached to the lot documentation.

## Troubleshooting

**Wash fastness is insufficient (grey scale < 3) for reactive dyestuffs:**
- The most probable cause is insufficient post-dyeing soaping: unfixed reactive dyestuff remains on the fibre and transfers on first wash. Repeat the soaping cycle (fresh bath 90 °C, 15 minutes, with 1-2 g/L non-ionic detergent) and re-test.
- If fastness remains insufficient after repeated soaping: the cause is probably in the dyestuff or fixation temperature. Consult the dyestuff supplier.

**Staining is high on the polyester adjacent fabric (> grade 2):**
- For blended fabrics with disperse dyestuffs for the synthetic component: verify that the reduction clearing cycle (to remove unfixed disperse dyestuff) was correctly carried out. Unremoved disperse dyestuffs cause high staining on polyester.

**Result is borderline (grade 3-) and assessment is uncertain:**
- Have a second qualified inspector carry out an independent assessment and calculate the rounded average. In case of discordance, apply the lower grade.

## References

- IT textile glossary: [solidita_colore](../../docs/docs/glossary.md#solidita_colore), [delta_e](../../docs/docs/glossary.md#delta_e), [tintura](../../docs/docs/glossary.md#tintura)
- Related SOPs: SOP-DYE-001 (dye bath preparation), SOP-DYE-003 (shade verification), SOP-QLT-004 (shade deviation report)
- Reference standards: ISO 105-C06 (wash fastness), ISO 105-X12 (rubbing fastness), ISO 105-A02 (grey scale)
