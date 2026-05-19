---
acl_level: public
asset: telaio
asset_family: weaving
audience: operations
created_in_phase: 2
estimated_duration_min: 15
hazard_level: low
id: SOP-LOOM-001
lang: en
prerequisites: []
related_glossary:
- rottura_filo
- telaio
- ordito
- trama
- liccio
- tessitura
role: operator
status: reviewed
tags:
- troubleshooting
- weaving
- broken-end
- operator
title: Warp end break troubleshooting on rapier loom
version: '1.0'
---

# Warp end break troubleshooting on rapier loom

## Scope

This SOP describes the rapid intervention procedure following a **rottura_filo** (warp end break) on a rapier **telaio** (loom) during **tessitura** (weaving). The objective is to minimise machine downtime by restoring yarn continuity and restarting production with conforming fabric quality.

The procedure applies to single **ordito** (warp) end breaks that trigger an automatic loom stop via electronic broken-end detector. It does not apply to multiple simultaneous breaks (> 3 ends) or to mechanical loom failures: in those cases contact the departmental technician.

## Prerequisites

- The operator has completed basic textile machine safety training.
- The loom is in automatic stop state (indicator lamp active).
- The following items are available: mending needle, reserve **ordito** yarn of the correct count, cutting scissors, drawing-in comb.
- The operator wears the required PPE: cut-resistant gloves (category I), **otoprotettori** (hearing protection) if working in a high-noise department.

## Tools and PPE

- Mending needle (15-20 cm length, cross-section suited to the yarn count)
- Reserve **ordito** yarn (same count and twist as the yarn in production)
- Textile cutting scissors
- Drawing-in comb or yarn threader
- **Calibro_digitale** (optional, to verify reserve yarn count if in doubt)
- **Otoprotettori** SNR ≥ 28 dB (mandatory if department noise level > 85 dB(A))
- Cut-resistant gloves category I

## Step-by-step Procedure

1. **Identify the break location.** Observe the **telaio** surface and locate the missing **ordito** end in the warp sheet. The electronic detector indicates the harness number involved on the machine display.

2. **Make the work area safe.** Verify that the loom is in full stop (control panel: STOP state). Do not insert hands into the **liccio** (heddle) mechanism before this verification.

3. **Locate the broken yarn end.** Trace the broken end back from the break point towards the warp beam (**subbio** di ordito). If the end has withdrawn into the beam, draw out 20-30 cm by pulling gently.

4. **Mend the end.** Insert the mending needle through the corresponding **liccio** eye and through the reed dent (**cassa_battente**). Tie the reserve **ordito** end to the needle with a slip knot. Pull the needle to draw the yarn through heddle and reed.

5. **Adjust yarn tension.** Apply manual tension to the mended end comparable to the visible tension of the adjacent **ordito** ends. A too-slack end will cause **tessitura** defects; a too-tight end will cause a new break.

6. **Secure the end to the fabric.** Tie the repaired **ordito** end to the already-woven fabric (pick-up point) with a weaver's knot. Trim the tail to 2-3 cm from the knot.

7. **Restart the loom in slow mode.** Press the slow-start (jog) button for 2-3 **trama** (weft) picks, visually verifying that the mended end integrates correctly into the fabric without forming a **difetto_catena** (warp streak) or **densita_trama** (weft density) irregularity.

8. **Resume production at normal speed.** If the first slow picks are correct, bring the loom up to production speed.

## Verification

- Visual check: no **rottura_filo** in the next 20 m of fabric produced.
- Fabric surface check: the mended end must not be visible as a colour or structure discontinuity (no **difetto_catena**).
- **Densita_trama** check: compare visually with the fabric produced before the stop; no compactness variations should be evident in the pick-up zone.
- The **conta_trama** (pick counter, if fitted) must not signal anomalies in the pick-up zone.
- Log the intervention on the machine record: date, time, heddle number, presumed cause (if identified), operator.

## Troubleshooting

**The end breaks again within a few metres:**
- Check the reserve yarn count: it must match the nominal warp count. Use the **calibro_digitale** if available.
- Verify that the mending knot is not positioned in a high-friction zone (heddle eye or reed dent): reposition the knot upstream.
- If more than 3 consecutive breaks occur on the same end: escalate to the departmental technician (possible defect in the supply bobbin or damaged heddle eye).

**Impossible to locate the broken end in the warp beam:**
- Use an inspection torch to illuminate the warp beam (**subbio** di ordito) from the rear.
- If the end has completely withdrawn into the beam, free 30-40 cm manually by unwinding the beam with the reverse-motion handwheel (follow the machine-specific safety procedure).

**The loom does not restart after the jog:**
- Verify that no scissors or tools remain inside the **liccio** or reed zone.
- Check the control panel for additional alarms (e.g. weft break, air-jet pressure issue, etc.).
- If the alarm persists, call the technician: do not force a restart.

**The fabric shows horizontal streaks in the pick-up zone:**
- The mended end tension was probably excessive. Loosen the knot and re-mend with reduced tension.
- Verify that the **cassa_battente** (beat-up mechanism) did not shift its stroke during the stop.

## References

- IT textile glossary: [rottura_filo](../../docs/docs/glossary.md#rottura_filo), [telaio](../../docs/docs/glossary.md#telaio), [ordito](../../docs/docs/glossary.md#ordito)
- Related SOPs: SOP-LOOM-002 (warp tension drift), SOP-QLT-001 (fabric quality inspection)
- Reference standards: ISO 5247 (textile terminology), UNI EN 388 (PPE cut-resistant gloves)
