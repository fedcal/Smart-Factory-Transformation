# Quality manager

The quality manager supervises the textile quality control system for the entire site, from raw material receipt (**yarn_count** incoming) to finished batch acceptance. They own the 4-point grading inspection process, defect taxonomy and batch decisions (acceptance, downgrading, rejection). They interact with all production departments and with yarn and dye suppliers.

## Responsibilities

- Definition and maintenance of quality standards: **delta_e**, **pick_density**, **yarn_irregularity** tolerances for each article in production
- Supervision of **roll_inspection** at the **inspection_table**: inspector training, method calibration, management of inter-inspector discrepancies
- Defect taxonomy management: systematic classification of **mispick**, **slub**, **warp_defect**, **shade_deviation**, **halo**, **streakiness**, **pilling**, **selvedge_defect**
- Batch decision: acceptance, second-choice downgrading, re-dyeing, total rejection based on **delta_e** data and 4-point inspection score
- Monthly reporting to stakeholders: quality **oee**, defect rate per article, **mttr** quality restoration trend

## Typical interaction with assets and processes

The quality manager operates mainly in the final inspection department but intervenes upstream when a systematic defect indicates a process problem. They use the **spectrophotometer** for **delta_e** verification on dyed fabric samples and interact with the **dyeing** department to analyse causes of **shade_deviation** between batches. They collaborate with the maintenance technician when a systematic defect (**barring**, **warp_defect**) originates from a mechanical failure of the **loom** or the **beating_mechanism**.

## Critical daily decision

The critical decision is: accept, downgrade or reject a batch in the presence of **delta_e** measurements or inspection scores at the tolerance limits. A borderline batch can be accepted with a customer waiver, downgraded (sold at reduced price), sent for re-dyeing or rejected. Each decision has a direct economic impact; the quality manager balances the risk of returns vs the cost of re-dyeing or batch loss, coordinating with commercial management for batches on critical customer orders.

## Pain points

- **shade_deviation** difficult to anticipate — **Shade_deviation** between rolls of the same batch emerges at the final **roll_inspection**, when the **dye_bath** is already spent and the only remedy is re-dyeing; the lack of inline **delta_e** monitoring during the dyeing cycle is the main gap.
- Inconsistent defect classification — Classification of borderline defects (**slub** 4 mm vs 5 mm, **pilling** grade 3 vs 3.5) varies between inspectors; inter-inspector variability produces inconsistent batch decisions that generate customer disputes.
- **neps** and **yarn_irregularity** traceability on incoming material — The quality of **yarn_count** purchased from external suppliers is not always verified on arrival; a yarn batch with high **yarn_irregularity** (CVm% >12%) generates **slub** defects visible only after weaving and dyeing, when the damage is already irreversible.

!!! note "Mantis context"
    Mantis quality operates with **delta_e** CMC tolerance <1.0 for production and <0.5 for seasonal sampling destined for outdoor buyers. **Roll_inspection** is carried out 100% for batches destined for the premium segment; for standard batches, 10% sampling. The quality manager participates in the night-morning shift handover for batches with ongoing waivers.

## References

- [Glossary: roll_inspection, delta_e, four_point_system, weft_defect](../../glossary.md)
- [Related role: Shift supervisor](shift-supervisor.md)
- [Related role: Maintenance technician](technician.md)
