# Domain: textile manufacturing analysis

This section documents the domain of medium-sized Italian textile manufacturing, with reference to the Mantis Textile Group case. The analysis is organized into process pages — natural retrieval units for the RAG agents of Phase 5 — and role pages, which support retrieval filtering by operational persona.

The dual purpose is: to provide a reusable open-source reference for the Italian textile manufacturing sector and to offer the knowledge substrate that will feed the platform agents (OperatorAssistant, MaintenanceCoach, QualityInspector, etc.).

!!! note "Mantis context"
    Mantis Textile Group is a medium-sized Italian textile company, active in the outdoor and sportswear apparel segment. It produces technical fabrics in cotton/wool/linen blends on 3×8h shifts. The production site has weaving, warping, dyeing and finishing departments in a single Lombardy facility.

## High-level map

```mermaid
flowchart LR
    accDescr: "Textile production flow: warping → weaving → dyeing → finishing, with spinning upstream."
    A[Spinning] --> B[Warping]
    B --> C[Weaving]
    C --> D[Dyeing]
    D --> E[Finishing]
```

> Process vs asset_family. The 5 *processes* (weaving/spinning/warping/dyeing/finishing) are the linear production flows defined by decision D-21. The `asset_family` attribute of SOPs extends that set with `quality_grading` — a transversal inspection scope that operates across all processes (4-point grading, broken-end detection, etc., per D-27) and is not a standalone process. Quality inspection intervenes transversally at each phase of the flow, not sequentially after finishing. See `packages/sft-domain/src/sft_domain/schemas/sop.schema.json` for the complete enum (6 values).

## Process pages

The five process pages document the linear production flow, each with a Mermaid diagram, assets involved, KPIs and pain points:

- [Spinning](processes/spinning.md)
- [Warping](processes/warping.md)
- [Weaving](processes/weaving.md)
- [Dyeing](processes/dyeing.md)
- [Finishing](processes/finishing.md)

## Role pages

The four role pages describe the operational figures that interact with processes and assets, focusing on critical decisions and daily pain points:

- [Operator](roles/operator.md)
- [Maintenance technician](roles/technician.md)
- [Quality manager](roles/quality-manager.md)
- [Shift supervisor](roles/shift-supervisor.md)
