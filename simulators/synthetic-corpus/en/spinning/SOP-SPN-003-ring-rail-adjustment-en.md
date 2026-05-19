---
acl_level: internal
asset: ring spinning frame
asset_family: spinning
audience: maintenance
created_in_phase: 2
estimated_duration_min: 35
hazard_level: low
id: SOP-SPN-003
lang: en
prerequisites:
- SOP-SPN-001
related_glossary:
- filatura
- filatoio_anello
- fuso
- anello_rotante
- irregolarita_filato
- titolo_filato
role: technician
status: reviewed
tags:
- maintenance
- spinning
- ring-rail
- adjustment
- technician
title: Ring rail adjustment on ring spinning frame
version: '1.0'
---

# Ring rail adjustment on ring spinning frame

## Scope

This SOP describes the adjustment and verification procedure for the ring rail of the **filatoio_anello** (ring spinning frame). The ring rail supports the traveller rings (**anello_rotante**) on which the traveller runs to feed yarn to the **fuso** (spindle); its vertical oscillating movement determines yarn distribution on the bobbin and the winding cone angle.

A poorly adjusted or worn ring rail causes:
- Non-uniform yarn distribution on the bobbin (irregular cone angle)
- Periodic **titolo_filato** (yarn count) variation (yarn bars every N cm corresponding to the rail stroke)
- Increased **rottura_filo** (end break) rate in the winding zone

Verification is recommended every 500 production hours or following reports of irregularity in the winding pattern.

## Prerequisites

- The **filatoio_anello** is in a planned stop state (shift changeover or end of batch).
- The technician has access to the ring rail adjustment manual (nominal stroke, parallelism, height values) for the specific manufacturer.
- Measuring instruments are available and calibrated.
- PPE: work gloves, safety glasses.

## Tools and PPE

- Precision level (0.01 mm/m resolution) for ring rail parallelism verification
- **Calibro_digitale** for ring-to-guide distance and spindle clearance verification
- Ring rail adjustment key (machine model specific)
- LED inspection torch
- Work gloves
- Safety glasses

## Step-by-step Procedure

1. **Verify ring rail parallelism.** With the **filatoio_anello** stopped and the ring rail in the start position (lower stroke limit), position the precision level on the rail at three points: left edge, centre, right edge. Record the deviation from horizontal at each point. Typical tolerance: deviation < 0.2 mm/m across the full machine width. A deviation above this indicates collapse of the lateral rail guides.

2. **Verify ring rail vertical stroke.** Using a dial gauge or millimetre rule, measure the vertical stroke of the ring rail (distance between the lowest and highest points of oscillation). Compare with the machine nominal value for the article in production. The stroke determines the winding layer length: a reduced stroke causes bobbins with less yarn per layer, increasing bobbin changes.

3. **Verify ring-to-spindle centring.** With the **calibro_digitale**, measure the distance between the centre of the traveller ring (**anello_rotante**) and the centre of the corresponding **fuso** at 5 sample positions distributed along the machine. Typical tolerance: decentring < 0.3 mm. An off-centre ring relative to the **fuso** generates asymmetric traveller friction and increases **irregolarita_filato**.

4. **Inspect the lateral rail guides.** Visually check the lateral guides (rail sliding columns) for wear, deformation or fibre accumulations. Excessive guide wear causes lateral play in the rail stroke, which translates into periodic **titolo_filato** variation (bars). Clean guides with lint-free cloth.

5. **Adjust the rail to correct detected deviations.** If parallelism is out of tolerance: adjust the lateral levelling screws (typically 2 per side for machines with 1000-1500 spindles). Adjust in 0.05 mm increments and re-verify after each increment. If ring centring is out of tolerance: correct the lateral rail position using the positioning guides.

6. **Verify the rail drive system.** Check the chain or belt driving the vertical rail movement: a slack belt causes irregular variation in oscillation speed, which generates yarn bars. Correct belt tension: verify per manual method (typically deflection < 5 mm under 10 N load).

7. **Run a reduced-speed trial.** Restart the **filatoio_anello** at reduced speed (50-60% of nominal speed) for at least 10 minutes. Observe the winding pattern on bobbins: yarn must distribute uniformly on the bobbin with a regular cone. No visible bars on the wound yarn.

8. **Bring to production speed and log.** Gradually bring the **filatoio_anello** to nominal speed. Verify that the **rottura_filo** rate in the first 15 minutes does not exceed the normal threshold. Record: detected deviations, adjustments performed, date, technician.

## Verification

- Precision level on the ring rail (at rest position) shows deviation < 0.2 mm/m across the full machine width.
- Ring-to-spindle centring is within 0.3 mm at 5 sample positions.
- Bobbins produced in the trial cycle show a uniform winding pattern without visible bars.
- **Rottura_filo** rate in the 15 minutes post-adjustment is conforming to the article normal threshold.

## Troubleshooting

**Ring rail progressively tilts during production (parallelism drift):**
- Levelling screws loosen from vibration: apply thread-locking compound (Loctite or equivalent) after adjustment, following the manufacturer's manual. If the problem persists, the lateral guides may be worn: escalate to maintenance for structural verification.

**Yarn shows periodic bars with pitch equal to the ring rail stroke:**
- This indicates a rail drive fault (slack belt or excessive lateral guide play). Verify belt tension and lateral guide play: repeat from steps 4 and 6.

**One or more rings are off-centre relative to the spindle but adjustment is not possible with standard screws:**
- Probable permanent deformation of the ring rail in that zone: report to the maintenance supervisor to evaluate replacement of the affected rail segment.

## References

- IT textile glossary: [filatoio_anello](../../docs/docs/glossary.md#filatoio_anello), [anello_rotante](../../docs/docs/glossary.md#anello_rotante), [fuso](../../docs/docs/glossary.md#fuso)
- Related SOPs: SOP-SPN-001 (spindle calibration), SOP-SPN-002 (drafting cylinder cleanup), SOP-SPN-005 (preventive lubrication)
- Reference standards: ISO 5247 (textile terminology), spinning frame manufacturer's technical documentation
