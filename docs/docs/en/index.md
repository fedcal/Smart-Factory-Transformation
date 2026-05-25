# Smart Factory Transformation

> **Every critical AI decision passes through an informed human, but no human is ever alone facing an operational problem.**

---

## What This Is

Smart Factory Transformation is a **self-hostable opensource platform** that orchestrates a team of GenAI agents to support operators, maintenance technicians, knowledge workers, and warehouse managers in a textile manufacturing facility. Agents read signals from PLCs, MES systems, and industrial sensors, suggest or execute actions always subject to human control, and capitalize on the company knowledge base to reduce expertise silos.

The project is simultaneously:

- a **reference architecture** documented bilingually (IT/EN) served via GitHub Pages
- a **Python SDK** for writing custom agents extensible to other industrial verticals
- a **working PoC** on simulated data and public datasets (NASA C-MAPSS, UCI Manufacturing)
- a **realistic economic proposal** modeled on the OEPV framework (Base Price €108,000)

The foundational architectural principle is **Human-in-the-Loop (HITL)**: no critical action is executed without an informed human having approved it or being able to intervene. This is not a technical constraint — it is the ethical premise of the project.

## Audience

| Audience | What They Find Here |
|----------|-------------------|
| **Competition evaluators** | Technical and economic documentation for 70/30 assessment; architecture, workflows, use cases, ROI |
| **Opensource community** | Extensible SDK, 16 reference agents documented, reusable HITL patterns for other Industry 4.0 verticals |
| **Mantis stakeholders (fictional)** | Operational workflows, dashboards, approval/override runbooks, textile domain analysis |

## Project Status

![Phase 1: Foundation & Monorepo](https://img.shields.io/badge/Phase_1-Foundation_%26_Monorepo-blue)

The project develops across successive phases:

| Phase | Title | Status |
|-------|-------|--------|
| **1** | Foundation & Monorepo | In progress |
| **2** | Documentation & Domain Analysis | Next |
| **3** | OT Integration & Simulation | — |
| **4** | Core Agentic Runtime | — |
| **5** | Frontend & UX | — |
| **6+** | Reference Agents, Observability, Security, Economic Model | — |

## Navigation

- [Getting Started](getting-started.md) — Requirements, local setup, and first runs
- [Architecture](architecture/overview.md) — High-level diagram and guiding principles
- [Contributing](contributing/index.md) — Conventions, toolchain, and CI workflow

---

*Project: [smart-factory-transformation/smart-factory-transformation](https://github.com/smart-factory-transformation/smart-factory-transformation) — License: Apache 2.0*
