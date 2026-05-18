---
id: SOP-QLT-003
title: Mispick defect analysis and classification in fabric
version: "1.0"
lang: en
asset: inspection table
asset_family: quality_grading
role: quality-manager
hazard_level: low
estimated_duration_min: 20
prerequisites:
  - SOP-QLT-001
related_glossary:
  - mispick
  - difetto_trama
  - ispezione_rotolo
  - tavolo_ispezione
  - densita_trama
  - controllo_qualita_tessile
tags:
  - quality
  - inspection
  - mispick
  - analysis
  - quality-manager
audience: quality
status: draft-unreviewed
created_in_phase: 2
---

# Mispick defect analysis and classification in fabric

## Scope

This SOP describes the specialised procedure for detection, analysis and classification of **mispick** defects (missing, double or incorrectly inserted weft picks) during **ispezione_rotolo** (roll inspection) of fabric. A **mispick** is the most frequent **tessitura** (weaving) defect and can manifest in three main forms: missing **trama** (weft) pick (weft drop), double **trama** pick (two picks in one shed), or incorrectly inserted **trama** pick (weft not correctly interlaced with the **ordito** (warp)).

The distinction between **mispick** types is fundamental for diagnosing the loom problem: different types indicate different mechanical causes. The SOP provides the diagnostic keys for process diagnosis beyond simple visual classification.

The procedure applies to **tavolo_ispezione** inspection with backlighting for all substrates.

## Prerequisites

- The base **ispezione_rotolo** (SOP-QLT-001) is in progress or completed.
- The target **densita_trama** (weft density) value and tolerance (picks/cm ± tolerance) for the article under examination are available.
- The **tavolo_ispezione** with backlighting is operational.
- PPE: thin cotton gloves, millimetre rule.

## Tools and PPE

- **Tavolo_ispezione** with adjustable-intensity backlighting
- 5x magnifying glass (for mispick type analysis)
- Pick glass (picker glass — magnifying glass with millimetre grid for **densita_trama** counting)
- Ruler or flexible tape measure (for defect position and size measurement)
- Chalk pencil or tape (for edge defect marking)
- Defect report form

## Step-by-step Procedure

1. **Identify mispick during scrolling.** A **mispick** is recognisable during scrolling by:
   - Visible horizontal line in the fabric (under backlighting): indicates absence of **trama** pick (weft drop)
   - Thicker-than-normal horizontal line: indicates double **trama** pick
   - Horizontal discontinuity with non-interlaced **trama** filament: indicates failed insertion
   Stop the fabric on **mispick** detection and proceed to analysis.

2. **Classify the mispick type.** With 5x magnifying glass and backlighting, analyse the defect structure:
   - **Mispick type 1 (missing weft):** one or more **trama** picks absent — backlighting shows a transparent horizontal stripe. Typical loom cause: **trama** end broke during insertion without activating the detector.
   - **Mispick type 2 (double weft):** two **trama** ends in the same shed — fabric is thicker at that point. Typical cause: insertion mechanism error (double feeding).
   - **Mispick type 3 (non-interlaced weft):** the **trama** end is present but not correctly interlaced with some **ordito** ends — visible as a floating end. Typical cause: shed not completely open at the moment of insertion (slow or mis-synchronised **liccio**).

3. **Measure the defect length.** With the ruler, measure the **mispick** length in the **trama** direction (defect width in fabric). Classify for score per the four-point system (SOP-QLT-001). Also measure how many consecutive picks are affected (e.g. single missing pick vs. 3 consecutive missing picks).

4. **Verify weft density in the defect zone.** With the pick glass, count the number of **trama** picks per cm in zones 5 cm and 10 cm from the **mispick**. Compare with the article target value. A **densita_trama** variation in the zones adjacent to the **mispick** indicates a perturbation of the insertion mechanism extending beyond the visible defect point.

5. **Record the mispick with type and diagnostic cause.** In the defect report form, enter: position, size, four-point score, type (1/2/3), number of consecutive affected picks, any **densita_trama** variations in adjacent zones.

6. **Identify mispick distribution in the roll.** Calculate **mispick** frequency per 100 m and their distribution: regular (recurring at fixed intervals) or random. A **mispick** recurring at regular intervals suggests a cyclic mechanical problem at the loom (e.g. insertion mechanism with periodic wear). A random pattern indicates intermittent problems (brittle **trama** yarn, variable bobbin quality).

7. **Complete the mispick analysis report.** Add to the base report (SOP-QLT-001) the **mispick** analysis section: count by type (1/2/3), frequency/100 m, distribution (regular/random), any regular pattern with indicated pitch. This information is essential for the weaving department in diagnosing the mechanical cause.

8. **Communicate the diagnosis to the weaving department (if frequency exceeds threshold).** If **mispick** count exceeds the company threshold (typically > 2/100 m for standard articles) or if a regular pattern has been identified: communicate the type-specific analysis report to the weaving department head technician. The **mispick** type directly guides mechanical diagnosis.

## Verification

- All roll **mispick** are classified by type (1/2/3) and recorded with position and score.
- **Mispick** frequency per 100 m is calculated and reported.
- If frequency exceeds the threshold, the weaving department has been informed with the typological analysis report.
- The final roll classification correctly accounts for the total **mispick** score.

## Troubleshooting

**Unable to distinguish between mispick type 1 and type 3 with 5x glass:**
- Apply raking backlighting from one side of the fabric: type 3 **mispick** (floating end) shows a physically present end that does not follow the interlacing pattern; type 1 shows complete absence of end. If doubt persists: take a 5×5 cm sample for optical microscope analysis.

**Mispick visible under backlighting but not under direct light:**
- This is a light **mispick** (weft end present but not correctly interlaced in one or few **ordito** meshes). It is nonetheless classifiable and must be recorded. Backlighting is the standard method for these fine defects.

**Mispick frequency varies significantly between the first and second half of the roll:**
- Indicates a change of conditions during production: **trama** bobbin change, tension variation in the loom, or onset of mechanical component wear. Record the changeover position in the report to help temporal diagnosis in the weaving department.

## References

- IT textile glossary: [mispick](../../docs/docs/glossary.md#mispick), [difetto_trama](../../docs/docs/glossary.md#difetto_trama), [ispezione_rotolo](../../docs/docs/glossary.md#ispezione_rotolo)
- Related SOPs: SOP-QLT-001 (four-point fabric inspection), SOP-LOOM-003 (projectile jam), SOP-LOOM-005 (post-event cleanup)
- Reference standards: AATCC 96 (Four-Point System), ISO 4660 (textile defect classification)
