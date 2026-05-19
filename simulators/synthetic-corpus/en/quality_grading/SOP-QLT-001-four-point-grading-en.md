---
acl_level: internal
asset: inspection table
asset_family: quality_grading
audience: quality
created_in_phase: 2
estimated_duration_min: 20
hazard_level: low
id: SOP-QLT-001
lang: en
prerequisites: []
related_glossary:
- ispezione_rotolo
- controllo_qualita_tessile
- tavolo_ispezione
- difetto_trama
- slub
- mispick
- difetto_catena
- rottura_filo
role: quality-manager
status: reviewed
tags:
- quality
- inspection
- four-point
- grading
- quality-manager
title: Fabric inspection using the four-point grading system
version: '1.0'
---

# Fabric inspection using the four-point grading system

## Scope

This SOP describes the **ispezione_rotolo** (roll inspection) procedure for finished fabric using the four-point grading system (AATCC 96 / ISO 4660 standard for commercial grading). The system assigns a penalty score to defects based on their size in the fabric direction (warp or weft) regardless of inherent severity.

The procedure applies to acceptance inspection of finished fabric before shipment or before garment making. It applies to all substrates (cotton, polyester, blends) produced in-house. The inspection result determines roll classification (First quality / Second quality / Cutting) and the lot decision (CONFORMING / NON-CONFORMING).

**Controllo_qualita_tessile** (textile quality control) via the four-point system is the standard method adopted for commercial grading in European weaving.

## Prerequisites

- The roll to be inspected is identified with a lot label and order number.
- The **tavolo_ispezione** (inspection table) is clean and operational (active rear diffused lighting, fabric advance motor verified).
- The inspector has completed training in visual recognition of textile defects.
- The maximum fabric scroll speed on the table is set to ≤ 20 m/min for cotton and blends (reduce to ≤ 15 m/min for dark or glossy-surface fabrics).
- The defect report form (paper or digital) is available.

## Tools and PPE

- **Tavolo_ispezione** with rear diffused lighting and motorised advance
- Ruler or flexible tape measure (for defect position and size measurement)
- Chalk pencil or coloured adhesive tape for defect marking
- Defect report form (or tablet with inspection software)
- Calculator or spreadsheet for total scoring
- **Calibro_digitale** (optional, for thickness verification in the presence of **slub** defects)
- Reading glasses or magnifying glass (if required for fine defects)
- Thin cotton gloves (to avoid sebum contamination of the fabric surface on white or light fabrics)

## Step-by-step Procedure

1. **Prepare the table and load the roll.** Load the roll onto the **tavolo_ispezione** roll holder with the fabric running at 45° towards the inspector. Verify that the fabric has no abnormal tensions during advance (longitudinal creases indicate non-uniform lateral tension — correct roll positioning).

2. **Set scroll speed.** Set speed to ≤ 20 m/min (15 m/min for dark fabrics). Start scrolling and verify that the rear diffused lighting allows viewing of single-end defects (**rottura_filo**, **slub**) in transmitted light.

3. **Inspect fabric and classify defects.** During scrolling, identify each visible defect and assign the score per the four-point system table:

   | Defect size in weft or warp direction | Points assigned |
   |---------------------------------------|-----------------|
   | ≤ 75 mm (≤ 3 inches)                 | 1 point         |
   | > 75 mm and ≤ 150 mm (3-6 inches)   | 2 points        |
   | > 150 mm and ≤ 230 mm (6-9 inches)  | 3 points        |
   | > 230 mm (> 9 inches)                | 4 points (max)  |

   A single defect accumulates a maximum of 4 points regardless of its total length. Defect types to recognise: **mispick** (missing weft pick), **slub** (yarn thickening), **difetto_catena** (vertical streak), **difetto_trama** (horizontal irregularity), repaired **rottura_filo** (visible knot), stains, holes, oil **aloni**.

4. **Mark and record defects.** For each defect detected: briefly stop the fabric, measure the longitudinal position (distance from roll start in cm or m) and lateral position (distance from left edge in cm), defect dimension in the defect direction, defect type, points assigned. Mark with visible adhesive tape on the fabric edge at the defect level.

5. **Calculate the total roll score.** At end of inspection: sum all assigned points. Calculate "points per 100 linear metres": `Score/100m = (total points × 100) / roll length (m)`.

6. **Classify the roll.** Apply the company acceptance grid (threshold varies by article and destination market — verify with quality manager):
   - Typical industry First quality threshold: ≤ 28 points/100 linear m
   - Typical Second quality: 29-40 points/100 linear m
   - Cutting (defective zone trimming): > 40 points/100 linear m or defect concentrated in specific zone

7. **Complete the inspection report.** Enter in the form: roll/lot number, article, inspected length, defect count by type, total score, score/100 m, classification, inspector signature, date.

## Verification

- The inspection report is completed and signed for each inspected roll.
- Rolls classified as First quality do not exceed the agreed scoring threshold.
- Defects marked on the fabric edge correspond to the entries in the defect report (spot-check of 10% of reported defects).
- The defect rate by type (e.g. % **mispick**, % **slub**) is recorded in the quality system for monthly trend calculation.
- Non-conforming rolls are physically separated from conforming ones (segregation area) and identified with a red block label.

## Troubleshooting

**Inspector cannot see fine defects (slub < 3 mm) at standard speed:**
- Reduce speed to 10 m/min for the critical fabric section.
- Verify that rear lighting is uniform and of sufficient intensity (not less than 400 lux on the inspection plane). Replace lamps if brightness has fallen.
- For very fine fabrics (count > Nm 80): consider using a 3x magnifying glass.

**Defect not classifiable with confidence (uncertain type):**
- Stop the fabric and inspect the defect with supplementary front lighting.
- If still uncertain: take a 5 cm × 5 cm sample and send to laboratory for microscopic classification.
- In case of doubt between First and Second quality: always apply the conservative classification (Second quality).

**Fabric forms lateral creases during inspection:**
- Verify roll holder alignment on the **tavolo_ispezione**.
- If creases are structural (present even at minimum speed): record as a finishing defect (permanent creases) and classify accordingly.

**Total score very close to the acceptance threshold (±2 points):**
- Carry out a second inspection by a second inspector over a sample section of 20% of the length.
- In case of discordance between the two inspectors > 10% of the final score: request quality manager arbitration and document both readings.

## References

- IT textile glossary: [ispezione_rotolo](../../docs/docs/glossary.md#ispezione_rotolo), [tavolo_ispezione](../../docs/docs/glossary.md#tavolo_ispezione), [slub](../../docs/docs/glossary.md#slub), [mispick](../../docs/docs/glossary.md#mispick)
- Related SOPs: SOP-LOOM-001 (warp end break), SOP-LOOM-002 (warp tension drift), SOP-DYE-001 (dye bath preparation)
- Reference standards: AATCC 96 (Four-Point System), ISO 4660 (textile defect classification), UNI EN 388 (PPE)
