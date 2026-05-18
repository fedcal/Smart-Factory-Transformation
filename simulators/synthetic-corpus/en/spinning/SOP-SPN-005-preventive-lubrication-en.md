---
id: SOP-SPN-005
title: Preventive lubrication of ring spinning frame
version: "1.0"
lang: en
asset: ring spinning frame
asset_family: spinning
role: technician
hazard_level: medium
estimated_duration_min: 50
prerequisites:
  - SOP-SPN-001
related_glossary:
  - filatura
  - filatoio_anello
  - fuso
  - anello_rotante
  - irregolarita_filato
  - manutenzione_predittiva
tags:
  - maintenance
  - spinning
  - lubrication
  - preventive
  - technician
audience: maintenance
status: reviewed
created_in_phase: 2
---

# Preventive lubrication of ring spinning frame

## Scope

This SOP describes the preventive lubrication procedure for the **filatoio_anello** (ring spinning frame), covering the critical lubrication points: **fuso** (spindle) bearings or bushes, tangential drive shaft, traveller rings (**anello_rotante**) and ring rail sliding guides.

Inadequate lubrication (insufficient or excessive) is among the leading causes of:
- Increased **fuso** operating temperature with consequent accelerated wear
- Increased **irregolarita_filato** (yarn irregularity) from vibration
- Yarn oil contamination with risk of **aloni** (oil stains) in the dyed fabric

The lubrication frequency varies per point (from every shift for the traveller/ring system to every 1000 hours for main bearings): follow the manufacturer's specific lubrication plan, adapted to the article and production speed. This SOP describes the complete cycle; partial cycles follow the same method applied only to the points specified by the plan.

## Prerequisites

- The **filatoio_anello** is in a planned stop state (shift stop or maintenance stop).
- The lubricants specified by the manufacturer are available in the stockroom (do not substitute with generic lubricants without authorisation).
- The technician has the lubrication plan specific to the machine model and the register of previous lubrication cycles.
- PPE: oil-resistant work gloves, safety glasses, safety footwear.

## Tools and PPE

- Oil gun (for oil lubrication points) with specific tip for narrow access
- Grease gun (for main bearings — if applicable)
- Low-viscosity mineral oil (manufacturer specific — typically ISO VG 32 or 46 for spindles)
- Bearing grease (manufacturer specific for rolling bearings)
- Traveller/ring lubricant (specific traveller wax: composition indicated by manufacturer)
- Lint-free cloth (for cleaning lubrication points before application)
- **Igrometro** (hygrometer — to verify ambient conditions, as humidity affects traveller lubricant properties)
- Oil-resistant work gloves
- Safety glasses

## Step-by-step Procedure

1. **Verify ambient conditions and the lubrication plan.** Read the department **igrometro**: relative humidity in the 55-65% RH range is optimal for traveller lubrication (out of range: record the deviation in the register). Consult the lubrication plan and the previous cycle register to identify the points to lubricate in this cycle.

2. **Lubricate lower spindle bearings.** For each assigned section, apply 2-3 drops of low-viscosity mineral oil at the lower lubrication point of each **fuso** (typical position: between the spindle base and the support plate). Do not exceed: excess oil contaminates the yarn. Do not lubricate the upper part of the **fuso** (yarn and traveller contact zone).

3. **Lubricate tangential drive systems.** Verify the condition of the tangential drive belt (if the model uses one): visually check and lubricate the lateral belt supports (not the belt itself) per the plan. For drive shafts with rolling bearings: apply specified grease with grease gun (dose: indicated in the manual, typically 5-10 g per bearing for a quarterly cycle).

4. **Lubricate the ring rail and its guides.** Apply low-viscosity oil to the rail sliding points along the vertical guides. Distribute evenly along the full guide length with a cloth. A poorly lubricated guide causes irregular ring rail speed variation and yarn bars.

5. **Carry out traveller lubrication (if due in this cycle).** The traveller ring (**anello_rotante**) lubrication system uses specific waxes applied by an automatic wax dispenser (if fitted) or manually. Check the wax level in the automatic dispenser (if fitted) and replenish if necessary. For manual lubrication: apply wax to the traveller with the specific brush, passing over each ring. Excess wax causes deposits on the **fuso** and yarn contamination.

6. **Clean lubrication points and adjacent areas.** Remove with a clean cloth any excess oil or grease from surrounding points. Visually verify that no lubricant has come into contact with the **filatura** (spinning) yarn or with the **stiro** (drafting) cylinder aprons.

7. **Check sample spindle temperatures after restart.** After restarting the **filatoio_anello**, check the surface temperature of a sample of 10 **fuso** distributed along the machine after 15 minutes of production. The surface temperature of a correctly lubricated **fuso** must not exceed 50-60 °C (measure with contact thermometer or IR pyrometer). Temperatures above this indicate insufficient lubrication or bearing wear.

8. **Log the lubrication cycle.** Complete the lubrication register: date, machine, section, points lubricated, type and quantity of lubricant used, ambient conditions (temperature and humidity), technician signature. Update the lubrication plan with the next scheduled cycle date.

## Verification

- No sample **fuso** exceeds 60 °C after 15 minutes of post-lubrication production.
- No oil stains are visible on the yarn produced in the 30-minute post-lubrication sample.
- The **rottura_filo** rate in the 30 minutes post-lubrication is conforming to the article normal threshold.
- The lubrication register is updated and signed.

## Troubleshooting

**A sample spindle shows elevated temperature (> 65 °C) after 15 minutes of production:**
- Verify that the lower lubrication point of the **fuso** was reached correctly (the gun tip must enter the specified point). Re-apply oil and re-verify after 10 minutes of production.
- If temperature does not drop: the **fuso** bearing may be worn or seized. Stop the **fuso** and flag for replacement.

**Produced yarn shows oil stains or aloni:**
- Excess oil has come into contact with the yarn. Identify the contamination zone (the stain concentrates in the first 100 m of yarn post-lubrication). Clean the lubrication zone with a dry cloth, verify that the lubrication point is not adjacent to the yarn-spindle contact zone. Flag the potentially contaminated lot for quality inspection.

**Automatic traveller lubrication system does not dispense wax uniformly:**
- Verify that the wax tray is at the correct level (too much wax causes dispenser blockage; too little causes insufficient lubrication). Clean the dispenser with a damp cloth and verify that the dispensing nozzles are clear.

## References

- IT textile glossary: [filatoio_anello](../../docs/docs/glossary.md#filatoio_anello), [fuso](../../docs/docs/glossary.md#fuso), [manutenzione_predittiva](../../docs/docs/glossary.md#manutenzione_predittiva)
- Related SOPs: SOP-SPN-001 (spindle calibration), SOP-SPN-003 (ring rail adjustment)
- Reference standards: ISO 5247 (textile terminology), spinning frame manufacturer's lubricant documentation
