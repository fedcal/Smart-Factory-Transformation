---
acl_level: public
asset: jet dyeing machine
asset_family: dyeing
audience: operations
created_in_phase: 2
estimated_duration_min: 45
hazard_level: medium
id: SOP-DYE-001
lang: en
prerequisites: []
related_glossary:
- tintura
- jet_dyeing
- bagno_colorante
- delta_e
- deviazione_tono
- spettrofotometro
role: technician
status: reviewed
tags:
- dyeing
- bath-preparation
- color
- procedure
- technician
title: Dye bath preparation for jet dyeing
version: '1.0'
---

# Dye bath preparation for jet dyeing

## Scope

This SOP describes the **bagno_colorante** (dye bath) preparation procedure for pressurised **jet_dyeing** machine **tintura** (dyeing). The procedure covers the dosing, dissolution and bath verification sequence before starting the dyeing cycle, with the objective of ensuring uniform colouration and keeping chromatic variation within the **delta_e** tolerance agreed with the customer.

The procedure applies to reactive and disperse dyestuffs on cellulosic and synthetic substrates. It does not apply to hank or beam dyeing (separate specific procedure). It does not replace the Recipe Sheet, which must be issued by the dyehouse laboratory for every article/colour.

Warning: the chemicals used in **tintura** (dyestuffs, auxiliaries, acids/alkalis) require specific PPE and waste disposal conforming to local regulations.

## Prerequisites

- The Recipe Sheet for the article to be dyed is available and signed by the laboratory supervisor.
- The fabric load (**tessuto_grezzo** or semi-finished) is already loaded in the **jet_dyeing** machine and the machine is in pre-fill state (demineralised water at the target liquor ratio level).
- The dyestuffs and chemical auxiliaries specified by the recipe are available in the stockroom in the correct quantities (weighed in the laboratory or at the dosing station).
- The technician has completed the chemical safety training (PPE, spill management, SDS sheets).
- PPE worn: anti-splash safety glasses, chemical-resistant gloves (category III), waterproof apron, safety footwear.

## Tools and PPE

- Portable **spettrofotometro** (spectrophotometer) for colour verification on withdrawal samples (e.g. DataColor 800 or equivalent)
- Precision balance (0.1 g resolution for dyestuffs; 1 g for auxiliaries)
- Graduated dissolution containers (min. 2 L for dyestuffs; 10 L for auxiliaries)
- Digital thermometer for dissolution water temperature verification
- Volumetric measure and pipettes for liquid auxiliaries
- Calibrated digital pH meter (for bath pH verification before starting cycle)
- Manual or magnetic stirrer for dyestuff dissolution
- Anti-splash safety glasses (EN 166)
- Chemical-resistant gloves category III (nitrile 0.35 mm)
- Waterproof apron
- FFP2 half-face mask (for fine powder dyestuffs)

## Step-by-step Procedure

1. **Verify machine parameters.** Check on the **jet_dyeing** machine panel: water level (target liquor ratio as per Recipe Sheet, typically 1:6 – 1:10 for modern jet dyeing), water temperature (initial value, typically 40-60 °C), initial bath pH (target: neutral-acid or neutral-alkaline depending on substrate — verify Recipe Sheet).

2. **Prepare the dyestuff solution.** Dissolve the dyestuffs in hot water (60-80 °C) in a separate container, using the water quantity indicated in the Recipe Sheet (typically 10-20 L per 100 kg of fabric). Stir until complete dissolution. For poorly soluble dyestuffs: use a mechanical stirrer for 10 minutes. Do not add dyestuff directly into the machine without pre-dissolution: risk of undissolved dyestuff stains (**screziatura**).

3. **Prepare auxiliary solutions.** Prepare separately the solutions of: wetting agent, levelling agent, anti-crease agent (if specified by the Recipe Sheet). Dose per the g/L values indicated relative to the bath volume. For alkaline auxiliaries (caustic soda, carbonate): prepare in dedicated containers and add AFTER the dyestuff (never mix with reactive dyestuffs dry — risk of premature hydrolysis).

4. **Add the dyestuff to the machine bath.** With the machine circulating (pump ON), slowly add the dyestuff solution through the addition vessel. Add over 5-10 minutes to ensure uniform distribution. Avoid rapid addition: causes **screziatura** from chromatic shock.

5. **Add auxiliaries according to the Recipe Sheet sequence.** Typical sequence for cotton reactive: (a) wetting agent, (b) salt (NaCl or Na2SO4), (c) dyestuff, (d) alkalis (caustic soda/carbonate). Observe the waiting times between additions as indicated in the recipe. Deviations from the sequence can cause **delta_e** final deviation.

6. **Verify bath pH.** Before starting the temperature cycle, measure bath pH with the calibrated pH meter. Compare with the Recipe Sheet range (typically pH 10-11 for reactives with alkalis; pH 4.5-5.5 for disperse with acetic acid). If pH is out of range: correct by adding alkali or acid as indicated in the recipe, in small increments, measuring after each addition.

7. **Start the programmed temperature cycle.** Confirm the thermal profile start on the machine panel (heating ramp, process temperature, hold time). The thermal profile is pre-programmed in the machine recipe; verify that the recalled recipe number matches the article in production.

8. **Mid-cycle control withdrawal (if specified by Recipe Sheet).** For some articles a sample withdrawal is required at an intermediate temperature for preliminary colour verification with **spettrofotometro**. If the **delta_e** measured exceeds the alert threshold (typically 3.0 CMC units at mid-cycle): consult the laboratory supervisor before completing the cycle.

## Verification

- At end of cycle, withdraw a fabric sample, dry it and measure colour with the **spettrofotometro** per the laboratory standard method.
- The **delta_e** CMC between sample and standard must be within the agreed tolerance (typically delta-E CMC < 1.0 for production, < 0.5 for sample collection).
- Absence of **screziatura** or **deviazione_tono** visible at 1 m distance under standard D65 light.
- The exhausted bath pH must fall within the permitted discharge range (check with the environmental officer — typically pH 6-9 for industrial sewer discharge).
- Record on the dyeing sheet: date, machine, recipe number, dyestuff lot, operator, measured delta-E, result (CONFORMING / NON-CONFORMING).

## Troubleshooting

**Final delta-E out of tolerance (colour excess — dark shade):**
- Open a soaping cycle (**tintura** in fresh bath with detergent) to remove unfixed dyestuff. Measure **delta_e** again after soaping.
- If still out of tolerance: consider lot downgrading or correction with a stripping bath (specific procedure by dyestuff type — consult laboratory).

**Streakiness (**screziatura** — non-uniform colouration) visible on fabric:**
- Most frequent cause: dyestuff added too quickly or not fully dissolved. For the current cycle: check whether **screziatura** can be reduced with a levelling cycle at temperature (60-80 °C for 20 minutes with levelling agent).
- If **screziatura** is structural (bands along the fabric axis): probably caused by insufficient fabric circulation in the **jet_dyeing** — check haul-off speed (typically 200-400 m/min).

**Bath pH does not reach target after alkali addition:**
- Verify that the pH meter is calibrated (buffer solutions pH 7.0 and pH 10.0). Recalibrate if necessary.
- Increase alkali addition in 10% steps of the planned dose and measure after each addition. Do not exceed 20% above the nominal dose without consulting the laboratory.

**Dyestuff not fully dissolved (visible particles in solution):**
- Filter the dyestuff solution through gauze or 100 µm filter before adding to the machine.
- Do not add turbid solution: risk of particle stains (**screziatura** puntiforme).

## References

- IT textile glossary: [tintura](../../docs/docs/glossary.md#tintura), [jet_dyeing](../../docs/docs/glossary.md#jet_dyeing), [bagno_colorante](../../docs/docs/glossary.md#bagno_colorante), [delta_e](../../docs/docs/glossary.md#delta_e)
- Related SOPs: SOP-QLT-001 (quality inspection and delta-E), SOP-DYE-002 (colour matching procedure)
- Reference standards: ISO 105 (colour fastness), ISO 13938 (bursting strength), specific dyestuff SDS sheets
