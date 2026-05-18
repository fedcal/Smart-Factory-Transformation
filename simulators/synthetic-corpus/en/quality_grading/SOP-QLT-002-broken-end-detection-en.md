---
id: SOP-QLT-002
title: Warp end break detection and recording during fabric inspection
version: "1.0"
lang: en
asset: inspection table
asset_family: quality_grading
role: quality-manager
hazard_level: low
estimated_duration_min: 25
prerequisites:
  - SOP-QLT-001
related_glossary:
  - rottura_filo
  - ispezione_rotolo
  - difetto_catena
  - tavolo_ispezione
  - controllo_qualita_tessile
  - sistema_quattro_punti
tags:
  - quality
  - inspection
  - broken-end
  - detection
  - quality-manager
audience: quality
status: draft-unreviewed
created_in_phase: 2
---

# Warp end break detection and recording during fabric inspection

## Scope

This SOP describes the specialised methodology for systematic detection and recording of repaired **rottura_filo** (warp end breaks — mended ends) visible during **ispezione_rotolo** (roll inspection) of finished fabric. A repaired **rottura_filo** appears as a knot or colour/structure discontinuity in the **ordito** (warp) end, distinguishable from **trama** (weft) defects and classifiable under the four-point system.

This specialisation is necessary because repaired **rottura_filo** tend to be underestimated in general inspection (the repair appears intact at first glance) but are often associated with latent **difetto_catena** (warp streaks) that manifest only during finishing or dyeing.

The procedure applies to **ispezione_rotolo** on **tavolo_ispezione** with backlighting, for greige or finished fabrics with a density greater than 18 ends/cm (above this density repaired **rottura_filo** are less visible to the naked eye at standard speed).

## Prerequisites

- The base **ispezione_rotolo** (SOP-QLT-001) is in progress or has been completed for the roll under examination.
- The **tavolo_ispezione** is equipped with high-intensity LED backlighting ≥ 600 lux (high intensity needed for detection of fine repairs).
- The base inspection report (SOP-QLT-001) is available with already-recorded defects.
- PPE: thin cotton gloves, reading glasses or magnifying glass (if required).

## Tools and PPE

- **Tavolo_ispezione** with high-intensity backlighting (≥ 600 lux)
- 3x-5x magnifying glass (for verification of doubtful repairs in fine fabrics)
- Ruler or flexible tape measure (for repair position and size)
- Chalk pencil or coloured tape (for marking significant repairs)
- Defect report form (integrated with the SOP-QLT-001 report)
- Thin cotton gloves

## Step-by-step Procedure

1. **Set the optimal scroll speed for detection.** Reduce fabric scroll speed to ≤ 15 m/min (vs. 20 m/min standard). For fabrics with **densita_trama** (weft density) > 25 picks/cm or **titolo_filato** (yarn count) > Nm 60: reduce to ≤ 10 m/min. Reduced speed is necessary to allow the eye to detect fine repairs.

2. **Position lighting correctly.** Verify that backlighting covers the entire fabric width uniformly during scrolling. For dark fabrics: supplement with a raking side light (30-45 degree angle to the fabric plane) which highlights surface irregularities of repairs.

3. **Recognise the visual signature of a repaired end break.** A repaired **rottura_filo** is recognisable by:
   - Visible knot in the **ordito** end (structural discontinuity point, typically 1.3-2x the end diameter)
   - Slight colour variation in the repaired **ordito** end (the reserve yarn may have a slightly different twist or lot)
   - Tension asymmetry in the adjacent **ordito** (the repaired end may be slacker or tighter)
   - Presence of **difetto_catena** within 5-10 cm adjacent to the repair point

4. **Classify each repaired end break.** For each repair identified, assign the score per the four-point system (SOP-QLT-001). In addition to the standard score, classify the repair quality:
   - **Acceptable repair:** clean knot, minimal visual variation, no adjacent **difetto_catena**
   - **Borderline repair:** visible but contained knot (< 2x end diameter), slight chromatic variation in the pick-up zone
   - **Unacceptable repair:** coarse knot (> 2x diameter), extended **difetto_catena**, structural discontinuity visible at 1 m distance

5. **Record repairs in the inspection report.** For each identified repair, add to the defect report form: longitudinal position, lateral position, four-point score, repair quality classification, associated defect type (e.g. **difetto_catena** if present). Mark unacceptable repairs with visible tape.

6. **Calculate repair frequency per 100 m and per width.** At end of roll inspection: calculate the number of repairs per 100 linear metres and per metre of width. A value > 3 repairs/100 linear metres is often indicative of systematic problems in the weaving process (unstable **ordito** tension, worn heddle, low-quality yarn).

7. **Evaluate correlation with the lot classification decision.** Unacceptable repairs contribute to the total **sistema_quattro_punti** (four-point system) score and may lead to roll downgrading. Report to the quality manager if repair frequency exceeds the company threshold: this is a process indicator requiring escalation to the weaving department.

8. **Complete the report integrating repair data with the base classification.** Finalise the **ispezione_rotolo** report including repair count and classification. The final roll classification (First / Second / Cutting) takes into account both the total score and the frequency of unacceptable repairs.

## Verification

- Unacceptable repairs are physically marked on the roll and recorded in the report with position and classification.
- Repair frequency per 100 m is calculated and reported.
- If frequency exceeds the company threshold, the quality manager and the weaving department head technician have been informed.
- The final roll classification correctly takes into account repairs in the total score.

## Troubleshooting

**Repair is visible with backlighting but not to the naked eye under normal light:**
- Transparent repairs are high-quality repairs (reserve yarn identical to the original, minimal knot). They are classifiable as acceptable if there is no associated chromatic variation. Record the position anyway for process frequency tracking.

**Impossible to distinguish a repair from a natural yarn count variation:**
- If doubt persists after inspection with 5x glass and raking light: apply the conservative benefit-of-the-doubt rule — classify as borderline repair. In the event of lot dispute, the specific doubtful point sample can be analysed by microscope.

**High repair frequency concentrated in a lateral zone of the fabric:**
- Indicates probable problem in a specific **liccio** (heddle) or group of **ordito** ends with abnormal tension. Note the lateral zone in the report (e.g. "repairs concentrated between cm 40 and 60 from left edge") to enable diagnosis in the weaving department.

## References

- IT textile glossary: [rottura_filo](../../docs/docs/glossary.md#rottura_filo), [ispezione_rotolo](../../docs/docs/glossary.md#ispezione_rotolo), [difetto_catena](../../docs/docs/glossary.md#difetto_catena)
- Related SOPs: SOP-QLT-001 (four-point fabric inspection), SOP-LOOM-001 (warp end break), SOP-LOOM-002 (warp tension drift)
- Reference standards: AATCC 96 (Four-Point System), ISO 4660 (textile defect classification)
