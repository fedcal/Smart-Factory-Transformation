---
id: SOP-LOOM-005
title: Loom cleaning and recovery after serial defect event
version: "1.0"
lang: en
asset: telaio
asset_family: weaving
role: technician
hazard_level: medium
estimated_duration_min: 45
prerequisites:
  - SOP-LOOM-001
  - SOP-LOOM-002
related_glossary:
  - telaio
  - tessitura
  - rottura_filo
  - difetto_catena
  - mispick
  - densita_trama
  - liccio
  - subbio
tags:
  - maintenance
  - weaving
  - cleanup
  - post-event
  - technician
audience: maintenance
status: draft-unreviewed
created_in_phase: 2
---

# Loom cleaning and recovery after serial defect event

## Scope

This SOP describes the systematic cleaning and restoration procedure for the **telaio** (loom) following a serial defect event: a production period during which multiple **rottura_filo** (end breaks), repeated **mispick**, or extensive **difetto_catena** (warp streaks) occurred over a significant fabric length (> 10 m). The objective is to remove yarn residues, fibre debris and wax or oil deposits accumulated during the event, restore nominal mechanical conditions and verify fabric quality before returning to normal production.

The procedure applies after defect events requiring a planned machine stop for diagnosis (not for the single end break managed by SOP-LOOM-001). It does not apply to scheduled preventive maintenance: that follows the machine-specific maintenance plan.

## Prerequisites

- The **telaio** is in a planned stop state; the defect event has been documented in the machine log.
- The technician has identified the primary cause of the event (tension, yarn quality, mechanism) and has already carried out the root-cause correction.
- The quality department has been alerted to evaluate the fabric produced during the event.
- Full PPE: cut-resistant gloves, safety glasses, FFP2 dust mask.

## Tools and PPE

- Textile dust vacuum cleaner (with HEPA filter for fine fibres)
- Dry-cleaning brush (stiff bristles, for lint removal)
- Lint-free cloth (for cleaning metal surfaces)
- Textile component cleaning spray (non-corrosive, specific to metals and ceramics)
- Lubricating oil (type specified by **telaio** manufacturer)
- **Calibro_digitale** (to verify mechanical component integrity after cleaning)
- Cut-resistant gloves category II
- Safety glasses
- FFP2 mask (for fine fibre dust)

## Step-by-step Procedure

1. **Document the initial state.** Before starting cleaning, photograph or note the position and quantity of visible yarn residues (fibre tufts, broken **trama** fragments, traveller wax accumulations). This enables monitoring cleaning effectiveness and correlating abnormal accumulations with the event cause.

2. **Remove coarse residues from the heddle zone.** With the **telaio** stopped, manually remove with tweezers or fingers all visible yarn fragments from **liccio** (heddle) eyes, between reed dents (**cassa_battente**) and in the **trama** insertion guide. Do not use compressed air at this stage: risk of dispersing fibres into sensitive components.

3. **Vacuum accumulated fibre dust.** Using the HEPA vacuum cleaner, proceed from top to bottom: first the **subbio** (warp beam) zone and let-off system, then the **liccio** zone, then the **cassa_battente** and the fabric take-up zone. Take care not to vacuum taut **ordito** ends which could break if suctioned.

4. **Clean the reed of the beat-up mechanism.** With the dry brush, remove fibre residues accumulated between reed dents. A dirty reed increases friction on the **trama** and can cause **trama** breaks and **densita_trama** (weft density) defects. If deposits are stubborn: spray specific cleaner and wipe with lint-free cloth.

5. **Inspect and clean the heddle eyes.** Each **liccio** eye must slide freely without friction. Encrusted fibre residues or hardened traveller wax in the eyes cause asymmetric friction and recurring **rottura_filo**. Clean with brush; if the eye is damaged or the contact surface is rough, flag it for heddle replacement.

6. **Verify and lubricate the specified lubrication points.** Identify the **telaio** lubrication points per the maintenance manual (typically: **subbio** bearings, insertion guides, shed-change mechanism). Apply 2-3 drops of specified lubricating oil. Do not over-lubricate: excess oil contaminates the **ordito** yarn and causes **aloni** (oil stains) on the fabric.

7. **Verify mechanical integrity of key components.** With the **calibro_digitale**, check:
   - Reed dent thickness (excessive wear causes **densita_trama** defects)
   - **Liccio** eye condition (deformation reduces freedom of movement)
   - Lateral alignment of the **subbio** (typical tolerance < 0.5 mm over 2 m width)
   Report any out-of-tolerance components in the extraordinary maintenance list.

8. **Run a trial cycle and verify quality.** Restart the **telaio** at reduced speed (60%) for 15 m of fabric. Perform continuous visual inspection of the produced fabric: absence of **difetto_catena**, **mispick**, **densita_trama** irregularities. Bring to full speed only after positive verification. Record results in the machine log.

## Verification

- Visual inspection of the first 15 m of fabric after recovery shows no **difetto_catena**, **mispick** or **densita_trama** irregularities compared with fabric produced before the event.
- The **rottura_filo** rate in the 30 minutes following intervention does not exceed the normal article threshold.
- All inspected components are within tolerance or have been flagged for scheduled replacement.
- The cleaning performed, components inspected and trial cycle result are logged in the machine record.

## Troubleshooting

**Serial defects resume within a few minutes of restart:**
- The primary cause of the event has not been fully corrected. Stop the **telaio** and re-examine: **ordito** tension (SOP-LOOM-002), **trama** bobbin yarn quality, or residual mechanical anomaly. Do not continue production if defects recur at the same frequency.

**Abnormal fibre dust accumulation found during cleaning:**
- An above-normal accumulation for the production cycle indicates a yarn quality problem (excess short fibres, **neps**) or an excessive production speed for the current article. Log and report to the department supervisor.

**Mechanical component found out of tolerance during inspection:**
- Do not restart the **telaio** without performing the replacement or without explicit authorisation from the maintenance supervisor. Running a **telaio** with out-of-tolerance components generates structural defects that compromise the entire batch.

## References

- IT textile glossary: [telaio](../../docs/docs/glossary.md#telaio), [liccio](../../docs/docs/glossary.md#liccio), [difetto_catena](../../docs/docs/glossary.md#difetto_catena)
- Related SOPs: SOP-LOOM-001 (warp end break), SOP-LOOM-002 (warp tension drift), SOP-QLT-001 (quality inspection)
- Reference standards: ISO 5247 (textile terminology), loom manufacturer's technical manual
