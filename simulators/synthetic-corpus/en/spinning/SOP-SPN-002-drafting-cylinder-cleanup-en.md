---
id: SOP-SPN-002
title: Drafting cylinder cleanup on ring spinning frame
version: "1.0"
lang: en
asset: ring spinning frame
asset_family: spinning
role: technician
hazard_level: low
estimated_duration_min: 40
prerequisites:
  - SOP-SPN-001
related_glossary:
  - filatura
  - filatoio_anello
  - stiro
  - cilindro_stiro
  - irregolarita_filato
  - titolo_filato
tags:
  - maintenance
  - spinning
  - cleanup
  - cylinder
  - technician
audience: maintenance
status: draft-unreviewed
created_in_phase: 2
---

# Drafting cylinder cleanup on ring spinning frame

## Scope

This SOP describes the periodic cleaning procedure for **cilindro_stiro** (drafting cylinders) on the **filatoio_anello** (ring spinning frame). The **stiro** (drafting) cylinders are the components that progressively draft the fibre sliver or roving, reducing the **titolo_filato** (yarn count) to the target value; their surface condition has a direct impact on **irregolarita_filato** (yarn irregularity) and **rottura_filo** (end break) frequency.

Cleaning is recommended every 250-500 production hours (depending on fibre quality processed) or whenever the **irregolarita_filato** (CVm%) exceeds the alert threshold of 10% above the article reference value. The procedure applies to both rubber-covered cylinders (aprons) and metallic pressure cylinders.

## Prerequisites

- The **filatoio_anello** is in a planned stop state (shift changeover, article changeover).
- The technician has access to the specific cleaning kit for the cylinder covering type (manufacturer specifications).
- The apron hardness values (Shore A) from the previous shift are known (if available from the maintenance register).
- PPE: work gloves (not cut-resistant — tactile sensitivity required), safety glasses.

## Tools and PPE

- Cylinder cleaning brush (soft bristles specific to textiles)
- Cylinder cleaning solution (specific for rubber and metal, non-corrosive, silicone-free)
- Lint-free cloth
- Shore A **durometro** (durometer) for rubber apron hardness verification after cleaning
- **Calibro_digitale** for cylinder diameter verification
- Apron extractor (for safe removal of aprons from the cylinder pair)
- Work gloves (not cut-resistant)
- Safety glasses

## Step-by-step Procedure

1. **Stop the assigned machine section.** Identify the **filatoio_anello** section to be cleaned. Stop fibre feed and lower the pressure cylinders (if the model has pneumatic lift). Do not physically separate the cylinders without having stopped the machine and feed.

2. **Remove residual sliver from cylinders.** Cut the roving or sliver fed to the **stiro** cylinders with scissors (do not pull: risk of fibre spreading and contamination). Collect fibre residues in the waste fibre bin.

3. **Clean the upper metallic cylinders.** Apply cleaning solution to a lint-free cloth and clean the metallic cylinder surfaces (typically stainless steel or chrome) with a rotary movement. Pay special attention to lateral edges where trapped fibres accumulate. Dry with a clean dry cloth.

4. **Remove and clean rubber aprons.** With the apron extractor, remove the aprons from the lower cylinder pair (standard procedure: lift with extractor without lateral forcing). Clean aprons with the specific cleaning solution (do not use solvent-based cleaners that degrade rubber). Inspect the surface: cracks, cuts or hardening (Shore A > 65) indicate replacement is needed.

5. **Verify apron hardness with durometer.** Measure Shore A hardness of aprons at 3 points (left edge, centre, right edge). Typical acceptable range: 45-65 Shore A (verify against manufacturer data). An apron with out-of-range hardness causes irregular drafting and increased **irregolarita_filato**.

6. **Clean lower apron cradles.** Clean the lower guides (cradle) over which the aprons run: fibre and wax deposits on the guides create non-uniform friction that is reflected in **irregolarita_filato**. Use brush and cleaning solution.

7. **Refit aprons and verify tensioning.** Refit aprons on the cylinder pair. Verify that the apron is centred and that tensioning is uniform across the full width. A poorly tensioned or off-centre apron causes drafting irregularity and **rottura_filo**.

8. **Run a trial cycle and measure CVm%.** After cleaning, restart the section and produce a yarn sample of at least 200 m. Measure CVm% with the Uster Tester (if available) or visually assess the yarn sample wound on the bobbin. CVm% must be equal to or lower than the article reference value.

## Verification

- Rubber aprons have Shore A hardness in the range specified by the manufacturer (typically 45-65 Shore A).
- **Calibro_digitale** confirms that metallic cylinder diameters are within nominal tolerance (+/- 0.05 mm from the tabulated value).
- CVm% of the yarn produced in the post-cleaning trial is conforming to the article reference value.
- Replaced or flagged aprons have been recorded in the machine maintenance form.

## Troubleshooting

**CVm% does not improve after cleaning:**
- Verify the **rapporto_stiro** (draft ratio) set for the article: excessive draft ratio causes structural irregularity not resolvable by cleaning. Compare with the article nominal parameters.
- Check the quality of the feed sliver: an already irregular sliver cannot be corrected by the drafting system. Request a sliver sample from the carding or combing department for analysis.

**Apron breaks or deforms during removal:**
- Do not reuse a broken apron: replace it. Verify that the apron extractor is the correct type for the machine model; using the wrong extractor causes mechanical damage to the apron during removal.

**Wax deposits on metallic cylinders resistant to normal cleaning:**
- Ring traveller wax may contaminate the drafting cylinders if the traveller lubrication system is poorly adjusted. Clean with a non-aggressive solvent (e.g. isopropanol) applied with a cloth: do not spray directly onto the machine. Verify the traveller lubrication system adjustment.

## References

- IT textile glossary: [filatura](../../docs/docs/glossary.md#filatura), [stiro](../../docs/docs/glossary.md#stiro), [cilindro_stiro](../../docs/docs/glossary.md#cilindro_stiro)
- Related SOPs: SOP-SPN-001 (spindle calibration), SOP-SPN-003 (ring rail adjustment), SOP-SPN-004 (slub control)
- Reference standards: ISO 5247 (textile terminology), spinning frame manufacturer's technical documentation
