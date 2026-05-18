# Maintenance technician

The maintenance technician is responsible for preventive and corrective maintenance of all textile machines on site. They operate both in planned mode (periodic maintenance programmes) and in emergency mode on call from the operator or shift supervisor. The technician has mechanical, electrical and pneumatic skills on the main assets: **loom**, **ring_frame**, **jet_dyeing** and **finishing_plant**.

## Responsibilities

- Execution of preventive maintenance plans (calibration of **spindle**, replacement of **heald**, cleaning of **card**, verification of **warp_tension_sensor**)
- Corrective intervention on failure: diagnosis, disassembly, component replacement, post-repair testing
- Spare parts warehouse management: verification of critical spare parts availability, restocking notification to shift supervisor
- Maintenance documentation updates: **mtbf**, **mttr** per machine, intervention log
- Support to the operator for complex defect classification (**warp_defect**, **streakiness**, **pilling**)

## Typical interaction with assets and processes

The technician interacts with all production processes but dedicates 60-70% of time to the **weaving** department (**warp_beam** changes, **heald** calibration, **beating_mechanism** adjustment). They use the **digital_calliper** to measure mechanical tolerances and the **durometer** to check rubber seal wear on **jet_dyeing** and **finishing_plant**. In **spinning**, they carry out **spindle** calibration every 500 operating hours and check the balance of rotating rings with **hygrometer** to verify department environmental conditions.

## Critical daily decision

The technician's critical decision is: repair on-the-spot or wait for the scheduled downtime. A **loom** failure during the production shift may require 30-90 minutes of repair; if the component to be replaced is not in stock, the downtime extends. The technician decides whether to attempt a temporary workaround (speed reduction, bypass of non-critical sensor) to complete the shift, or to stop definitively and wait for the spare part. The threshold is: if the risk of secondary damage is high (e.g., progressive **warp_defect** on warp), they stop.

## Pain points

- Intermittent failure diagnosis — Intermittent failures of the **broken_end** detection system or the **pick_density** control system are the most difficult to diagnose; the technician must replicate the failure conditions during the shift, with the risk of producing rejects in the meantime.
- Spare parts availability — The lack of critical spare parts (**ring_frame** rings, **jet_dyeing** nozzles) is the main cause of high **mttr**; the spare parts management system is often manual and subject to stock errors.
- Intervention documentation — Completing the maintenance log is perceived as bureaucracy; the lack of structured historical data makes it impossible to calculate reliable **mtbf** and **mttr** per machine, penalising predictive maintenance planning.

!!! note "Mantis context"
    The Mantis maintenance team consists of 3-4 technicians covering morning and afternoon shifts; the night shift is covered on call. Critical machines (rapier looms) have a target **mtbf** of 150 hours and target **mttr** of 1.5 hours. Saturday morning maintenance is the scheduled intervention time for multiple **warp_beam** changes and **spindle** calibrations.

## References

- [Glossary: loom, ring_frame, mtbf, mttr](../glossary.md)
- [Related role: Operator](operator.md)
- [Related role: Shift supervisor](shift-supervisor.md)
