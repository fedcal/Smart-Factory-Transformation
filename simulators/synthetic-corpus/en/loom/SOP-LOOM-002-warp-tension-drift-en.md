---
acl_level: internal
asset: telaio
asset_family: weaving
audience: maintenance
created_in_phase: 2
estimated_duration_min: 30
hazard_level: medium
id: SOP-LOOM-002
lang: en
prerequisites:
- SOP-LOOM-001
related_glossary:
- telaio
- ordito
- subbio
- liccio
- misuratore_tensione_ordito
- rottura_filo
- densita_trama
- tessitura
role: technician
status: reviewed
tags:
- troubleshooting
- weaving
- tension
- preventive
- technician
title: Warp tension drift diagnosis and correction
version: '1.0'
---

# Warp tension drift diagnosis and correction

## Scope

This SOP describes the diagnostic and corrective procedure for progressive warp tension drift on a rapier or projectile **telaio** (loom). Drift manifests as a gradual increase or decrease of tension beyond the ±15% tolerance relative to the nominal value, detected by the **misuratore_tensione_ordito** (warp tension meter) or diagnosed by the appearance of **difetto_catena** (warp streaks) in the fabric.

The procedure is intended for the departmental technician (not for the production operator) as it requires access to the let-off system adjustment parameters and use of measuring instruments.

It does not apply to sudden single-end breaks (see SOP-LOOM-001) or to electromechanical failures of the let-off system (escalate to maintenance technician).

## Prerequisites

- The **telaio** is in a planned stop state or during a shift changeover (do not interrupt ongoing production without justification).
- The technician has access to the let-off system adjustment panel (maintenance key level 2).
- The nominal warp tension value for the article in production is available (from the production sheet or MES system).
- Measuring instruments are available and calibrated.
- PPE: cut-resistant gloves, safety glasses when working near the rotating **subbio** (warp beam).

## Tools and PPE

- Portable **misuratore_tensione_ordito** (direct-contact tensiometer type)
- **Calibro_digitale** for verifying yarn or mechanical component thickness
- Warp beam brake adjustment key (specific to machine model)
- LED inspection torch
- Parameter recording sheet (or tablet with MES access)
- Cut-resistant gloves category I
- Safety glasses

## Step-by-step Procedure

1. **Measure the current tension.** With the **telaio** in slow cycle (jog), apply the **misuratore_tensione_ordito** at three representative positions across the beam width (left edge, centre, right edge). Record the three values in N. Typical industry range for cotton Nm 30-60: 10-25 N per end.

2. **Compare with the nominal value.** Calculate the percentage deviation: `deviation% = (measured - nominal) / nominal × 100`. If the deviation is within ±15%: tension is within tolerance; proceed to the Troubleshooting section for alternative causes. If deviation exceeds ±15%: proceed to step 3.

3. **Identify the cause of drift.** Check:
   - **Beam diameter:** a nearly depleted beam has a reduced diameter, which at the same brake setting produces increased tension. Measure the remaining diameter with the **calibro_digitale**. Diameter < 200 mm on an 800 mm nominal beam indicates imminent depletion.
   - **Beam brake condition:** check wear of friction linings and cleanliness of the contact surface (oil, yarn residues).
   - **Tension compensator (take-up arm) condition:** verify that the compensator arm moves freely and that the return weight/spring is intact.

4. **Correction for drift due to beam diameter change (most frequent cause).** Adjust the **subbio** brake by increasing or reducing the clamping tension according to the machine adjustment table. Make adjustments in 5% increments and re-measure tension after each step. Target: return within ±10% of nominal.

5. **Correction for dirty or worn beam brake.** Stop the **telaio** and lock the **subbio** mechanically. Clean the friction surface with a dry cloth. If the friction linings show wear (thickness < 3 mm or uneven seating): replace the linings according to the machine-specific procedure and log the intervention.

6. **Correction for jammed or malfunctioning compensator.** Verify free movement of the compensator arm with the loom stopped. If jammed: remove yarn residues or dust with compressed air. If the component is damaged: notify the maintenance technician and suspend production of the current article.

7. **Run a production trial.** After correction, restart the **telaio** at normal speed for 50 m of fabric. Measure tension every 10 m. Verify that the drift has stabilised and that the fabric shows no **difetto_catena** or **densita_trama** variations.

8. **Log the intervention.** Record on the machine log or MES: date, time, pre/post-correction tension value, identified cause, corrective action, responsible technician.

## Verification

- Tension measured at the left edge, centre and right edge of the **subbio** is within ±10% of the nominal value for the article in production.
- The **misuratore_tensione_ordito** does not report alarms in the following 30 minutes of production.
- Visual inspection of the last 10 m of fabric produced shows no **difetto_catena** or **densita_trama** variations compared with fabric produced before the drift.
- The **subbio** brake parameter has been recorded in the machine maintenance sheet.
- The **rottura_filo** rate in the 30 minutes following intervention does not exceed the normal threshold for the article (typically < 3 breaks/hour for standard cotton shirting).

## Troubleshooting

**Tension does not stabilise after brake correction:**
- Verify that the automatic tension feedback system (if present: electronic control) is not compensating in the opposite direction to the manual correction. Consult the machine manual for manual override mode.
- Check the **subbio** bearings: unusual noise or lateral play indicates wear. Escalate to maintenance technician.

**Drift occurs only in a lateral zone of the fabric (asymmetric):**
- Check individual **ordito** end tension at the edges using the point-contact tensiometer.
- Verify the alignment of the **liccio** corresponding to the affected zone: a laterally misaligned heddle frame generates asymmetric tension.
- Verify that the beam is mounted perfectly perpendicular to the machine axis (typical tolerance: < 0.5 mm misalignment over 2 m width).

**Drift recurs with a cycle < 2 hours:**
- Document the drift frequency and open a preventive maintenance work order for a full overhaul of the **subbio** let-off system (brake, compensator, tension sensor).
- Assess whether the article in production has a nominal tension at the machine specification limit.

**Fabric shows periodic horizontal bars:**
- Periodic bars at regular intervals (typically every 20-100 cm) are often caused by tension variation synchronised with the **subbio** rotation frequency: check beam eccentricity or brake irregularity.

## References

- IT textile glossary: [ordito](../../docs/docs/glossary.md#ordito), [subbio](../../docs/docs/glossary.md#subbio), [misuratore_tensione_ordito](../../docs/docs/glossary.md#misuratore_tensione_ordito)
- Related SOPs: SOP-LOOM-001 (single end break), SOP-QLT-001 (fabric quality inspection)
- Reference standards: ISO 5247 (textile terminology), loom manufacturer's technical manual
