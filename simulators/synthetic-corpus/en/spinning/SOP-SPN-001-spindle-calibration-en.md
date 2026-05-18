---
id: SOP-SPN-001
title: Spindle calibration and verification on ring spinning frame
version: "1.0"
lang: en
asset: ring spinning frame
asset_family: spinning
role: technician
hazard_level: low
estimated_duration_min: 25
prerequisites: []
related_glossary:
  - filatura
  - filatoio_anello
  - fuso
  - irregolarita_filato
  - titolo_filato
  - stiro
  - igrometro
  - calibro_digitale
tags:
  - maintenance
  - spinning
  - calibration
  - preventive
  - technician
audience: maintenance
status: draft-unreviewed
created_in_phase: 2
---

# Spindle calibration and verification on ring spinning frame

## Scope

This SOP describes the periodic calibration and verification procedure for **fuso** (spindles) on the **filatoio_anello** (ring spinning frame) as part of the **filatura** (spinning) department preventive maintenance. The objective is to maintain spindle concentricity and verticality within design tolerances, preventing abnormal vibration, **irregolarita_filato** (yarn irregularity) and excessive **rottura_filo** (end breaks).

Verification is recommended every 500 production hours or following repeated reports of vibration or yarn defects in specific machine zones. The procedure applies to standard ring-traveller type spindles. It does not apply to open-end rotor frames (separate specific procedure).

## Prerequisites

- The **filatoio_anello** is in a planned stop state (shift changeover or maintenance stop).
- The technician has access to the machine technical documentation (spindle tolerance sheet from the manufacturer).
- Department relative humidity as read from the **igrometro** (hygrometer) is within the operating range 55-65% RH (out of range: concentricity measurement may be influenced by thermal expansion).
- Measuring instruments are available and calibrated.

## Tools and PPE

- **Calibro_digitale** (0.01 mm resolution) for spindle and ring diameter verification
- Dial gauge on magnetic stand (for spindle head eccentricity verification)
- Spindle verticality instrument (spinning-sector specific — e.g. vertical calibration pin)
- Spindle extractor (machine-model specific, from maintenance kit)
- Low-viscosity mineral oil lubricant (specified by machine manufacturer)
- Lint-free cleaning cloth
- LED inspection torch
- **Igrometro** (to verify ambient conditions at time of measurement)
- Work gloves (not cut-resistant — tactile sensitivity required for spindle handling)

## Step-by-step Procedure

1. **Record ambient conditions.** Read the department **igrometro** and note temperature (°C) and relative humidity (% RH). Optimal range for precise measurements: 20-25 °C, 55-65% RH. If out of range: record the deviation and indicate it in the calibration report.

2. **Identify spindles to verify.** For a scheduled calibration, systematically verify all **fuso** in the assigned machine section (typically 50-100 spindles per cycle). For a spot check following a report: focus on spindles within ±5 positions of the reported zone.

3. **Preliminary spindle cleaning.** Remove wound yarn residues from the spindle with tweezers or fingers (never with a cutter — risk of scratching the surface). Clean the spindle surface with a dry lint-free cloth. The spindle surface must be free of excess oil and traveller wax deposits.

4. **Verify spindle head concentricity.** Attach the dial gauge on magnetic stand to the machine frame, positioning the contact point on the upper diameter of the **fuso** (approximately 5 mm from the top). Rotate the spindle manually through 360° and record the reading variation. Maximum tolerance: 0.05 mm eccentricity (verify against manufacturer data). Spindles with eccentricity > 0.08 mm: flag for replacement.

5. **Verify spindle verticality.** Apply the verticality instrument (or sector-specific calibration pin) to the **fuso** and verify the angular deviation from vertical. Typical industry tolerance: < 0.3 mm/100 mm of spindle height. Spindles with inclination > 0.5 mm/100 mm: adjust the spindle support base (adjustment screw) or flag for replacement if deformation is permanent.

6. **Spindle lubrication (if due in this cycle).** Apply 2-3 drops of manufacturer-specified lubricating oil at the lower lubrication point of the **fuso** (bearing or bush). Excess oil contaminates the **filatura** yarn and causes stains on the final fabric. Do not lubricate the upper part of the spindle (yarn and traveller contact zone).

7. **Traveller ring verification.** Visually inspect the traveller ring associated with the **fuso** under verification. Signs of wear requiring replacement: oval ring (verify with **calibro_digitale** — typical circularity tolerance < 0.1 mm), scored or corroded inner surface, signs of overheating (browning discolouration). A worn ring increases **irregolarita_filato** and the **rottura_filo** rate.

8. **Record outcomes.** Complete the calibration sheet (or enter in MES): machine number, spindle position number, measured eccentricity, measured verticality, ring condition, action taken (none / lubrication / flagged for replacement). Sign and date the document.

## Verification

- Verified conforming spindles show no audible or abnormal vibrations on machine restart (auditory check in the following 10 minutes of production).
- **Titolo_filato** (yarn count) produced in the 30 minutes after calibration is within specification (verification on Uster Tester sample if available, or visual inspection of the produced package).
- **Irregolarita_filato** (CVm%) in the 30 minutes post-calibration does not exceed the limit value specified for the article in production.
- Spindles flagged for replacement have been entered in the extraordinary maintenance list with priority and position number.
- The calibration form is signed and archived in the machine file.

## Troubleshooting

**Spindle shows eccentricity in the 0.05-0.08 mm range (grey zone):**
- Verify eccentricity at 3 different spindle height points. If eccentricity is constant throughout: probable permanent deformation (replacement). If it varies only at the top: possible localised head deposit or damage — clean and re-verify.

**Impossible to extract spindle with standard extractor:**
- Do not force: the spindle may be locked by oxidation or support deformation. Apply penetrant (specific spray, observe waiting times) and re-check. If still locked: escalate to senior maintenance technician.

**Abnormal vibration persists after spindle calibration:**
- Check the traveller ring: an unbalanced or wrong-mass traveller generates vibrations even with a concentric spindle. Replace the traveller with the correct number for the **titolo_filato** in production.
- Verify that the spindle group transmission joint (tangential belt) does not have excessive play.

**Relative humidity out of range during calibration (> 70% or < 40%):**
- Concentricity measurements remain valid (not humidity-influenced). Record the ambient deviation in the report.
- If humidity is chronically out of range (> 70%): report to the facilities manager for verification of the **filatura** department air-conditioning system (high humidity increases **rottura_filo** from static charge).

## References

- IT textile glossary: [fuso](../../docs/docs/glossary.md#fuso), [filatoio_anello](../../docs/docs/glossary.md#filatoio_anello), [irregolarita_filato](../../docs/docs/glossary.md#irregolarita_filato)
- Related SOPs: SOP-SPN-002 (drafting cylinder cleanup), SOP-SPN-003 (ring rail adjustment)
- Reference standards: ISO 5247 (textile terminology), spinning frame manufacturer's technical documentation
