# Weaving

**Weaving** is the process of interlacing **warp** and **weft** threads to produce flat fabric. The **loom** is the central machine: **warp** threads arranged on the **warp_beam** are crossed with **weft** threads inserted by the insertion mechanism, compacted by the **beating_mechanism** up to the programmed **pick_density**.

## Process flow

```mermaid
flowchart LR
    accDescr: "Weaving flow: warp beam feeds the loom, healds form the shed, the beating mechanism compacts the weft, grey fabric exits on the roll."
    A[Warp beam] --> B[Shed formation - healds]
    B --> C[Weft insertion]
    C --> D[Beat-up - beating mechanism]
    D --> E[Grey fabric]
    E --> F[Broken-end detection]
    F --> G[Roll winding]
```

## Assets involved

- **loom** — Picanol OptiMax / Toyota JAT810 rapier; operating parameters: 600-900 picks/min, warp tension 10-30 N for medium cotton
- **warp_beam** — Warp unwinding cylinder; typical capacity 600-1200 m of warp in cotton Nm 40-60
- **heald** — Metal frames with eyes for shed formation; number of frames 4-16 depending on the weave pattern
- **beating_mechanism** — Oscillating mechanism for weft compaction; frequency 10-15 Hz correlated with picks/min speed
- **pick_counter** — Optical device for **pick_density** verification every 10 cm of fabric

## KPI

- **oee** (%) — typical range 65-75% in European weaving; formula: Availability × Performance × Quality
- **pick_density** (picks/cm) — range 18-32 picks/cm for standard cotton-wool fabrics; formula: weft thread count per cm
- **mtbf** (hours) — range 80-200 hours for modern rapier loom; indicates intrinsic machine reliability
- **mttr** (hours) — range 0.5-2 hours for **broken_end** and **mispick**; measures corrective maintenance efficiency

## Pain points

- Frequent **broken_end** — A rate above 5 **broken_end**/hour/**loom** signals tension problems or **yarn_count** quality issues; each stop results in efficiency loss and risk of **warp_defect** if the re-piecing is not precise.
- **pick_density** variability — Fluctuation of **pick_density** by even ±1 pick/cm causes density defects and horizontal lines (**barring**) visible in final inspection; the origin is often in the **beating_mechanism** mechanism.
- Recurring **mispick** — A **mispick** every 10 m is at the limit of acceptability; the defect requires roll downgrading or manual repair, with direct impact on department **oee**.
- Unplanned **warp_beam** change — Replacing the **warp_beam** requires 30-60 minutes of machine downtime; preventive planning of the **warp_beam** change is critical to maintain **oee** within shift windows.

!!! note "Mantis context"
    Mantis weaves mainly cotton/wool blends (70/30) and cotton/linen for the outdoor segment. The target **pick_density** is 22-26 picks/cm. Looms operate on 3×8h shifts; Saturday mornings are dedicated to preventive maintenance and scheduled warp beam changes. Noise in the department exceeds 98 dB(A): **ear_protection** SNR 30 dB are mandatory.

## References

- [Glossary: weaving, loom, warp_beam, pick_density](../../glossary.md)
- [SOP procedures — Loom](../../sop/index.md)
