---
id: SOP-LOOM-004
title: Selvage fault diagnosis and recovery on rapier loom
version: "1.0"
lang: en
asset: telaio
asset_family: weaving
role: technician
hazard_level: low
estimated_duration_min: 35
prerequisites:
  - SOP-LOOM-001
  - SOP-LOOM-002
related_glossary:
  - telaio
  - tessitura
  - cimosa
  - difetto_orlatura
  - liccio
  - ordito
  - densita_trama
tags:
  - troubleshooting
  - weaving
  - selvage
  - technician
audience: maintenance
status: draft-unreviewed
created_in_phase: 2
---

# Selvage fault diagnosis and recovery on rapier loom

## Scope

This SOP describes the diagnostic and corrective procedure for **difetto_orlatura** (selvage faults) on a rapier **telaio** (loom). A selvage fault manifests as irregularities at the lateral edges of the fabric: loose edge, **ordito** border ends not correctly interlaced, **densita_trama** (weft density) irregularities at the margins, or frayed edge after selvage trimming.

The procedure is intended for the departmental technician, as it requires adjustment of the border heddles, the selvage mechanism and the lateral tensioners. It does not apply to selvage faults caused by problems with the selvage-cutting system (tucking device): in that case follow the machine-specific manufacturer procedure.

Continuous **difetto_orlatura** over more than 2 m causes roll downgrading; early identification and timely correction are critical.

## Prerequisites

- The **telaio** is in a planned stop state (preferably during shift changeover or article changeover).
- The technician has access to the technical documentation (manufacturer's manual, border heddle adjustment parameters).
- Border **ordito** tension values are available from the article sheet (MES or paper).
- PPE: cut-resistant gloves, safety glasses.

## Tools and PPE

- LED inspection torch
- **Calibro_digitale** (to verify border heddle pitch and selvage end tension)
- Lateral tension adjustment key (machine-specific)
- Angled inspection mirror (for verification of hard-to-access zones)
- Cut-resistant gloves category I
- Safety glasses

## Step-by-step Procedure

1. **Inspect the fabric edge on the roll in production.** Before stopping the machine, observe the last 2-3 m of fabric already wound on the roll to characterise the fault: regular or random, single-sided or bilateral, associated with specific **liccio** frames or spread across the full selvage width. Photograph or note the fault type.

2. **Stop the loom in the diagnostic position.** Bring the **telaio** to a stop with the shed open (mid-cycle) to have visibility of the border heddles and selvage **ordito** ends. Use the jog function to position the machine.

3. **Inspect the selvage warp ends.** Visually verify the tension of the border **ordito** ends relative to the central ends. Visible tension asymmetry (border ends looser or tighter than adjacent ends) indicates a border tensioner adjustment problem or a selvage **ordito** end with a different count.

4. **Check the border heddles (temple and selvage heddle).** Check the eyes of the **liccio** dedicated to the selvage: damaged or cut eyes generate asymmetric friction and cause **difetto_orlatura**. Replace damaged eyes.

5. **Check the selvage device (tucking device or temple).** Verify that the temple (fabric lateral presser) exerts uniform pressure on both edges. Reduced pressure causes edge fraying; excessive pressure causes **densita_trama** irregularities at the margins. Adjust to the manual values.

6. **Adjust selvage end tension.** Identify the specific border tensioner (usually a separate spring or weight system from the main tensioner). Adjust incrementally (5% at a time) and measure tension with the **calibro_digitale** applied to the border ends. Target: border tension no more than +20% above the average central warp tension.

7. **Run a slow-speed trial.** Restart the **telaio** at reduced speed (60% of nominal speed) for 20 m of fabric. Inspect the produced edge: the **cimosa** (selvage) must be uniform, without loosening or fraying. If the fault persists: repeat the diagnosis from step 3.

8. **Resume normal-speed production and log.** Bring the **telaio** to production speed after a positive slow-speed verification. Record on the machine log: fault type, identified cause, adjustment performed, technician, date.

## Verification

- Visual inspection of the 10 m of fabric produced after intervention: the **cimosa** edge is uniform, without loosening, fraying or **densita_trama** irregularities at the margins.
- Border **ordito** end tension is within +20% of the average central end tension (verified with the tensiometer).
- The **difetto_orlatura** does not recur in the 30 minutes following intervention.
- The intervention is logged in the machine record with identified cause and corrective action.

## Troubleshooting

**Selvage fault persists after border tensioner adjustment:**
- Check whether the border **ordito** end has a count different from the central ends (error in the warping phase). Measure with **calibro_digitale**: if the difference is >10% of the nominal count, the problem is upstream (warping) and cannot be resolved at the **tessitura** stage without a beam change.
- Check that the number of **ordito** ends in the selvage matches the parameters of the article in production.

**Continuous edge fraying even after temple adjustment:**
- Inspect the selvage-cutting device (knife or tucking needle): a worn blade or bent needle causes irregular cutting that manifests as fraying. Replace the blade or needle.
- Verify that the selvage is being formed correctly on both sides (single-sided vs bilateral helps isolate the defective side).

**Selvage fault on one side only:**
- Problem is likely localised to the border tensioner or selvage heddle on one side. Repeat the diagnosis focusing on the affected side.

## References

- IT textile glossary: [cimosa](../../docs/docs/glossary.md#cimosa), [difetto_orlatura](../../docs/docs/glossary.md#difetto_orlatura), [liccio](../../docs/docs/glossary.md#liccio)
- Related SOPs: SOP-LOOM-001 (warp end break), SOP-LOOM-002 (warp tension drift), SOP-QLT-001 (fabric quality inspection)
- Reference standards: ISO 5247 (textile terminology), loom manufacturer's technical manual
