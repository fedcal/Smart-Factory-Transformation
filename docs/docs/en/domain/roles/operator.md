# Operator

The operator is the front-line figure who manages textile machines (looms, ring frames, warpers) during the production shift. Their role is to ensure production continuity, detect anomalies and decide when to escalate intervention to the maintenance technician. The operator interacts directly with the machine HMI and with the monitoring system based on **opc_ua**.

## Responsibilities

- Start-up, operation and supervision of machines assigned to the shift (looms, ring frames, warpers)
- Continuous monitoring of operating parameters (**warp** tension, **pick_density**, **yarn_irregularity**) via HMI and control panels
- Detection and classification of textile defects (**broken_end**, **mispick**, **slub**, **neps**) during production
- Execution of re-piecing manoeuvres and **warp_beam** realignment in case of machine stoppage
- Completion of shift production log: pieces produced, stops, anomalies, **warp_beam** consumption

## Typical interaction with assets and processes

The operator works primarily on **weaving** and **spinning** processes. They interact with the **loom** via HMI to set or read **pick_density** and picks/min speed parameters. On the **warping** process, they verify **warp** tension on the **warp_tension_sensor** and report anomalies to the technician. They use the **pick_counter** for spot-check density verification during the shift. In case of prolonged **mispick** or **warp_defect**, they contact the shift supervisor to assess batch stoppage.

## Critical daily decision

The operator's critical decision is: stop the **loom** or continue production in the presence of **broken_end** or emerging defect. Stopping costs time and lowers the shift's **oee**; not stopping risks amplifying the defect over tens of metres of fabric, leading to roll downgrading. The rule of thumb in use is: if **broken_end** exceeds 3 occurrences in 15 minutes on the same **loom**, the operator stops and alerts the technician; below threshold, re-pieces and records in the log.

## Pain points

- Department noise — The noise level in the **weaving** department exceeds 95-105 dB(A); **ear_protection** reduces verbal communication between operators, increasing the risk of errors in shift coordination.
- Frequent **broken_end** diagnosis — The operator is the first to identify the cause of **broken_end** (tension, **yarn_count** quality, ring wear); without diagnostic support tools, classification is empirical and inconsistent between different operators.
- Access to machine historical data — The operator has no direct access to **oee** and **mttr** trends per machine; they must rely on the paper log or the memory of the previous shift to contextualise anomalies.

!!! note "Mantis context"
    Mantis operators manage on average 4-6 rapier looms per shift in the weaving department. The morning shift (6-14h) includes the hot handover of production instructions from the night shift supervisor. Average experience is 3-8 years; know-how on **warp** tension recipes for cotton/wool blends is predominantly tacit and undocumented.

## References

- [Glossary: operator, loom, broken_end, oee](../../glossary.md)
- [Related role: Maintenance technician](technician.md)
- [Related role: Shift supervisor](shift-supervisor.md)
