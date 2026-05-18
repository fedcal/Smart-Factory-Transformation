---
id: SOP-LOOM-003
title: Projectile jam removal and resolution on projectile loom
version: "1.0"
lang: en
asset: telaio
asset_family: weaving
role: operator
hazard_level: medium
estimated_duration_min: 20
prerequisites:
  - SOP-LOOM-001
related_glossary:
  - telaio
  - tessitura
  - inceppamento_navetta
  - cassa_battente
  - trama
  - mispick
tags:
  - troubleshooting
  - weaving
  - shuttle-jam
  - operator
audience: operations
status: reviewed
created_in_phase: 2
---

# Projectile jam removal and resolution on projectile loom

## Scope

This SOP describes the rapid intervention procedure for removing an **inceppamento_navetta** (projectile jam) on a projectile loom. A jam occurs when the projectile does not complete its **trama** (weft) insertion stroke and stops inside the **ordito** (warp) shed, causing the machine to stop automatically and creating a risk of **mispick** or warp damage.

The procedure applies to single projectile jams in the insertion zone. It does not apply to failures of the picking mechanism or to structural damage to the **cassa_battente** (reed slay): in those cases the departmental technician must be alerted immediately. Incorrect removal of the jammed projectile can cause multiple weft defects and damage the **liccio** (heddle).

## Prerequisites

- The **telaio** is in automatic stop state (visual and audible alarm active).
- The operator has completed textile machine safety training and knows the location of the manual stop controls.
- Available: projectile extraction hook, LED inspection torch, cut-resistant gloves.
- The control panel is accessible and displays the jam alarm with diagnostic code.

## Tools and PPE

- Projectile extraction hook (specific to the **telaio** model, normally supplied by the manufacturer)
- LED inspection torch
- Cut-resistant gloves category II (projectile handling involves sharp edges)
- **Calibro_digitale** (optional, to verify projectile integrity after extraction)
- Safety glasses

## Step-by-step Procedure

1. **Verify full loom stop.** Check the control panel: status must be STOP with jam alarm active. Do not insert hands into the **trama** insertion zone until the **telaio** is in full stop and the flywheel has decelerated.

2. **Locate the jammed projectile.** Open the side access panel to the insertion zone. Illuminate with the torch to identify the exact position of the projectile in the insertion guide or in the **ordito** shed. Verify that the projectile is not visibly deformed.

3. **Free the projectile with the extraction hook.** Insert the extraction hook into the rear hole of the projectile (do not pull by the wound **trama** yarn — risk of breakage and multiple **mispick**). Extract with a linear movement along the insertion axis, without angling. Apply progressive and constant force; if the projectile does not yield on the first pull, check whether it is blocked by a wound **ordito** end.

4. **Remove the projectile from the guide.** Once extracted, place the projectile in the dedicated storage container. Visually inspect the projectile for deformation, deep scratches or chipped edges: a damaged projectile must be removed from service and reported for replacement.

5. **Inspect the insertion zone.** Verify that no **trama** yarn fragments remain in the **ordito** shed or the insertion guide. Remove any yarn residue with tweezers. Check that the **ordito** ends in the jam zone have not been damaged (partial cut, dislodged from the **liccio** eye).

6. **Check the weft yarn integrity.** Remove the damaged **trama** yarn from the jam area: cut the tail to approximately 5 cm from the interrupted insertion. The system will restart with a new insertion cycle on restart.

7. **Close access panels and verify restart conditions.** Close and lock the side panel. Verify on the control panel that the jam alarm has been reset (RESET button). Run a slow cycle (jog) for 2-3 **trama** picks before restarting at normal speed.

8. **Log the event.** Record on the machine log: date, time, number of jams in the shift, extraction conditions, projectile condition (conforming / reported for replacement), operator.

## Verification

- The **telaio** resumes normal-speed operation without new jam alarms.
- Visual inspection of the first 5 m of fabric produced after restart shows no **mispick** or **trama** irregularities in the pick-up zone.
- The extracted projectile has been entered in the projectile status register (conforming/to be replaced).
- The jam rate in the shift is logged for trend monitoring.

## Troubleshooting

**The projectile cannot be extracted with the standard hook:**
- Check whether the projectile is blocked by a **ordito** end wound around it multiple times: in that case, cut the end with textile scissors (do not pull) before attempting extraction.
- If the projectile is physically deformed and wedged in the guide: do not force further. Stop the attempt and alert the technician; forcing a deformed projectile can damage the insertion guide.

**The jam alarm recurs within a few minutes of restart:**
- Check the picking mechanism: a worn picking mechanism generates insufficient insertion force, causing recurring jams. Escalate to the technician for inspection of the picking mechanism.
- Check the count and tension of the **trama** yarn on the bobbin: an oversized or excessively twisted yarn increases insertion resistance.

**Weft yarn residues visible in the fabric adjacent to the jam:**
- Inspect the 30 cm of fabric preceding the stop for latent **mispick**. If present: mark the zone for quality inspection and classify per SOP-QLT-001.

## References

- IT textile glossary: [telaio](../../docs/docs/glossary.md#telaio), [trama](../../docs/docs/glossary.md#trama), [mispick](../../docs/docs/glossary.md#mispick)
- Related SOPs: SOP-LOOM-001 (warp end break), SOP-LOOM-002 (warp tension drift), SOP-QLT-003 (mispick analysis)
- Reference standards: ISO 5247 (textile terminology), loom manufacturer's technical manual
