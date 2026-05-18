# Spinning

**Spinning** is the process of transforming textile fibres (cotton, wool, linen) into continuous yarn through drawing, twisting and winding. The **ring_frame** is the main machine for short-fibre spinning: the sliver from **carding** or **combing** is drafted by the drawing rollers, twisted by the rotating ring and wound onto the **spindle**. The resulting **yarn_count** determines the weight and mechanical properties of the final fabric.

## Process flow

```mermaid
flowchart LR
    accDescr: "Ring spinning flow: raw fibre passes through card, progressive drawing in rollers, twisting in ring frame, winding onto spindle."
    A[Raw fibre] --> B[Card / Comber]
    B --> C[Drawing - rollers]
    C --> D[Ring frame]
    D --> E[Spindle winding]
    E --> F[Finished yarn bobbin]
```

## Assets involved

- **ring_frame** — Main machine for short-fibre spinning; 500-1500 spindles per machine, spindle speed 8,000-20,000 rpm
- **card** — Opens and parallelises short fibres producing the feed sliver; main cylinder speed 200-350 m/min
- **comber** — Eliminates short fibres to produce fine **yarn_count** (Nm >60); up to 500 nips/min in modern configuration
- **spindle** — Rotating element that imparts twist to the yarn; an unbalanced **spindle** generates vibrations detectable at 50-200 Hz
- **hygrometer** — Monitors relative humidity (55-65% RH) to reduce **broken_end** and electrostatic charges

## KPI

- **oee** (%) — range 60-72% in spinning departments; the main loss is due to **broken_end** and spindle maintenance
- **yarn_count** (Nm) — range 20-80 Nm for fabric cotton; formula: length(km)/mass(kg); determines final weight
- **mtbf** (hours) — range 200-500 hours for modern **ring_frame**; spindles and rotating rings are the most critical components
- **yarn_irregularity** (CVm%) — acceptable range <12% for combed cotton; measured with Uster Tester on each bobbin

## Pain points

- Frequent **broken_end** — A **broken_end** frequency above 10 breaks/1000 spindle-hours indicates worn rotating rings or insufficient fibre quality; each break requires operator intervention for manual re-piecing.
- High **yarn_irregularity** — A CVm% above 15% produces **slub** and **neps** in the yarn, which become visible defects in the fabric after **weaving**; the main cause is uneven **drafting** in the rollers.
- **spindle** wear — An unbalanced **spindle** increases mechanical vibration, degrading yarn quality and increasing **broken_end**; preventive maintenance requires calibration with **digital_calliper** every 500 hours.
- **neps** accumulation from **carding** — Excessive **carding** speed increases **neps** in the sliver, which become visible irregularities in the finished fabric; balancing productivity vs fibre quality is the shift supervisor's critical daily decision.

!!! note "Mantis context"
    The Mantis spinning department produces mainly Nm 40-60 yarns in combed cotton and wool/cotton blends for outdoor technical fabrics. The **yarn_irregularity** CVm% target is <10% for combed cotton. The 3×8h shifts ensure production continuity; spindle maintenance is planned in the Friday night shift to minimise impact on weekly **oee**.

## References

- [Glossary: spinning, ring_frame, yarn_count, yarn_irregularity](../../glossary.md)
- [SOP procedures — Spinning](../../sop/index.md)
