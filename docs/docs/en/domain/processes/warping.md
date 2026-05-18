# Warping

**Warping** is the preliminary operation before weaving that arranges **warp** threads in parallel on the **warp_beam** with controlled tension and density. The prepared **warp_beam** is then mounted on the **loom**. Correct warping is a necessary condition to avoid **warp_defect** and **broken_end** during **weaving**: any irregularity of tension or density is directly reflected in the quality of the final fabric.

## Process flow

```mermaid
flowchart LR
    accDescr: "Warping flow: yarn bobbins in creels, threads parallelised at constant tension, progressively wound onto warping beam, then mounted on loom."
    A[Yarn bobbins - creel] --> B[Thread guide - reed]
    B --> C[Tension control]
    C --> D[Beam winding]
    D --> E[Finished beam]
    E --> F[Mounting on loom]
```

## Assets involved

- **warp_beam** — Winding cylinder for **warp** threads; diameter 800-1200 mm, capacity up to 1200 m of yarn in cotton Nm 40
- **warp_tension_sensor** — Sensor that detects thread tension during winding; typical value 10-30 N for cotton, with alarm thresholds for deviations >±20%
- **hygrometer** — Humidity control in department (55-65% RH) to avoid tension variations caused by yarn moisture absorption
- **digital_calliper** — Verifies **warp_beam** diameter and mounting tolerances of warper mechanical components

## KPI

- **oee** (%) — range 70-82% in warping (less fragmented process compared to weaving and spinning); main losses are **warp_beam** change setups and **broken_end** during winding
- **yarn_count** (Nm) — Verification of **yarn_count** on incoming batches to ensure consistency with production specifications; deviation >5% Nm leads to batch rejection
- **mtbf** (hours) — range 300-600 hours for sectional/beam warper; critical components are reeds and tension brakes
- **mttr** (hours) — range 0.5-1.5 hours for broken thread in warping; repair is manual and requires precise re-piecing

## Pain points

- **warp_defect** from non-uniform tension — Non-uniform tension during **warping** produces a **warp_defect** visible in the finished fabric as a vertical stripe; the cause is often worn tension brakes or a defective bobbin in the creel.
- **broken_end** during winding — Each **broken_end** interrupts the winding cycle and requires manual re-piecing; in sectional **warping** the cost is high because the defect propagates across the entire section.
- **fibre_contamination** on incoming material — The presence of **fibre_contamination** in **warp** bobbins is not detected during **warping** but emerges as a dark spot in the dyed fabric; visual inspection of the bobbin batch is the critical safeguard.
- Article change planning — Setup for article change (weave pattern, density, **yarn_count**) requires 2-4 hours; fragmentation of small-quantity orders increases the setup/production ratio with direct impact on **oee**.

!!! note "Mantis context"
    Mantis warping handles mainly warps of 2000-3600 threads for outdoor articles in cotton/wool. The sectional warper is preferred for short batches (300-800 m) typical of seasonal sampling. The target warping tension is 15-20 N for cotton/wool Nm 40 blend. The department is climate-controlled at 22°C ±1°C and 60% RH to ensure **yarn_count** stability.

## References

- [Glossary: warping, warp_beam, warp, tension](../../glossary.md)
- [SOP procedures — Loom](../../sop/index.md)
