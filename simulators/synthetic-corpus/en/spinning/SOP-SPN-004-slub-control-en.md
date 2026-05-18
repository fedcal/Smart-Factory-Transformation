---
id: SOP-SPN-004
title: Slub monitoring and control on ring spinning frame
version: "1.0"
lang: en
asset: ring spinning frame
asset_family: spinning
role: technician
hazard_level: low
estimated_duration_min: 25
prerequisites:
  - SOP-SPN-001
  - SOP-SPN-002
related_glossary:
  - filatura
  - slub
  - irregolarita_filato
  - neps
  - titolo_filato
  - filatoio_anello
  - stiro
tags:
  - quality
  - spinning
  - slub-control
  - monitoring
  - technician
audience: maintenance
status: reviewed
created_in_phase: 2
---

# Slub monitoring and control on ring spinning frame

## Scope

This SOP describes the procedure for monitoring and controlling the presence of **slub** in yarn produced by the **filatoio_anello** (ring spinning frame). A **slub** is a localised yarn thickening caused by a fibre concentration; it constitutes a **filatura** (spinning) defect that manifests in fabric as a visible irregular bulge classifiable under the four-point inspection system.

The procedure applies to in-production monitoring (periodic spot-check with Uster Tester or visual assessment) and to root-cause analysis when the **slub** rate exceeds the acceptance threshold. It does not apply to the production of artisan-slub yarns (intentionally irregular yarns): those follow specific draft recipes.

Excessive **slub** is often the first indicator of raw material quality problems (short or contaminated fibre) or worn **stiro** (drafting) cylinders.

## Prerequisites

- A yarn sample taken from the **filatoio_anello** in production is available for evaluation.
- The CVm% and **slub** (count/km) reference values for the article in production are available in the article sheet.
- The Uster Tester (if available) is calibrated and operational.
- PPE: work gloves, safety glasses.

## Tools and PPE

- Uster Tester (yarn regularity analyser — if available in laboratory)
- Yarn sampling bobbin (at least 200 m of yarn for a statistically significant test)
- 5x magnifying glass (for visual **slub** assessment without Uster Tester)
- Lightbox (for yarn inspection against black or white background)
- **Calibro_digitale** (for individual **slub** thickness measurement > 5 mm)
- Work gloves
- Safety glasses

## Step-by-step Procedure

1. **Take the yarn sample.** Take a sample bobbin directly from the **filatoio_anello** in production (preferably from 3-5 positions distributed along the machine, to assess variability between positions). Record the position number, sampling time, **titolo_filato** and article in production.

2. **Instrumental assessment with Uster Tester (if available).** Wind the sample onto the Uster Tester organ and start the analysis (typical speed: 400 m/min for cotton Nm 30-80). The report provides: CVm% (count variation), U% index, **slub** count (count/km) and **neps** count (count/km). Compare with the article reference values: CVm% < 12% for medium-combed yarn, **slub** < 5/km for shirting articles.

3. **Alternative visual assessment (without Uster Tester).** Wind the sample yarn onto a black cardboard sheet (for light yarn) or white (for dark yarn) in regular spirals without tension. Inspect with 5x glass and lightbox: count visible **slub** over 10 m of yarn and multiply by 100 to obtain the count/km estimate. A **slub** is classified as major if the diameter exceeds 2x the normal yarn diameter (verify with **calibro_digitale**).

4. **Identify slub distribution.** Verify whether **slub** are concentrated in specific machine zones (adjacent positions with high count) or uniformly distributed. Zonal concentration indicates a localised problem (drafting cylinder, apron, sliver guide). Uniform distribution indicates a raw material problem (short fibre or excessive **neps** in the feed sliver).

5. **Analyse the cause of excess slubs.** For zonal concentration: inspect the **cilindro_stiro** and aprons of the affected positions (SOP-SPN-002). Verify whether the apron is rigid (Shore A > 65) or deteriorated. For uniform distribution: take a feed sliver sample (roving or sliver) and visually assess its regularity. If the sliver is irregular: report to the carding or combing department.

6. **Carry out corrective action.** Based on the identified cause:
   - Cylinder/apron problem: proceed with SOP-SPN-002 (cleaning) for the affected positions.
   - Raw material problem: quarantine the suspect sliver lot and notify the production manager for evaluation of an alternative supply.
   - Draft ratio parameter problem: correct the parameters following the article technical sheet and verify that the change is applied in a coordinated manner across the whole machine.

7. **Verify improvement.** After corrective action, take a new sample from the same positions. Repeat the assessment (instrumental or visual). Compare the **slub** count pre/post action: it must show a statistically significant improvement (reduction > 30% of count).

8. **Document and report.** Complete the spinning quality control form: date, article, positions sampled, CVm% and **slub** values pre/post action, identified cause, action taken, technician signature. Report to the quality manager if the problem has not been resolved after corrective action.

## Verification

- Post-action **slub** count is within the article acceptance threshold (< 5/km for standard shirting articles, or specific value from the article sheet).
- Post-action CVm% is conforming to the reference value.
- No zonal **slub** concentration is visible in the visual assessment of the post-action sample.
- The quality control form is completed and archived.

## Troubleshooting

**Slub count does not improve after cylinder cleaning:**
- Verify the quality of the feed sliver: take 5 m of roving and wind onto cardboard for visual assessment. If the sliver shows periodic bars or visible **neps**: the problem is upstream of the **filatoio_anello** (carding or combing machine) and cannot be resolved by spinning frame maintenance.
- Check the **rapporto_stiro** (draft ratio) set: too high a ratio for the fibre type causes fragmentation of short fibres into **slub**. Reduce the ratio by 5% and re-verify.

**Slub present but only in a narrow machine zone (3-5 consecutive spindles):**
- Very probable cause: a damaged apron or broken sliver guide in the specific zone. Visually inspect all draft stage components at the affected positions.

**Uster Tester signals slubs but visual assessment does not detect them:**
- The Uster Tester detects **slub** even at 1.5x nominal diameter, not visible to the naked eye. These are classified as "thin slubs" and are nonetheless relevant for the final fabric. Proceed with root-cause analysis normally.

## References

- IT textile glossary: [slub](../../docs/docs/glossary.md#slub), [irregolarita_filato](../../docs/docs/glossary.md#irregolarita_filato), [filatura](../../docs/docs/glossary.md#filatura)
- Related SOPs: SOP-SPN-001 (spindle calibration), SOP-SPN-002 (drafting cylinder cleanup), SOP-QLT-002 (end break detection)
- Reference standards: ISO 5247 (textile terminology), USTER STATISTICS (CVm% references by yarn type)
