---
lang: en
requirements:
  - UI-09
  - UI-07
  - UI-01
  - UI-02
  - UI-03
  - UI-04
tags:
  - ui
  - mock-ui
  - i18n
  - UI-09
---

# User Interface — Mock UI

## Overview

This page documents the main user flows of the **Smart Factory Transformation** Angular 19 SSR
application via Mermaid diagrams by persona and Angular SSR component references.
The UI is designed for use on industrial screens and tablets on the factory floor:
touch targets ≥ 64px, WCAG AA contrast, dark theme by default.

!!! note "On-demand screenshots"
    UI screenshots are not included in the static documentation.
    They can be regenerated on-demand from the Playwright spec
    `apps/factory-ui-e2e/src/screenshots.spec.ts` with:

    ```bash
    # Start the full stack
    docker compose up -d

    # Generate screenshots (outside docs/)
    SFT_SKIP_SCREENSHOTS=false nx e2e ui-factory-e2e --spec=screenshots.spec.ts
    ```

---

## Login Screen

**Route:** `/auth/login`
**Component:** `LoginPage`
**Requirement:** UI-01 (design system), UI-09 (mock-UI docs)

The login page is vertically centred on a `--sft-surface` background (`#121418`).
The card has max-width 400px and contains:

- Email field with label "Email address"
- Password field with show/hide toggle
- "Sign In" CTA (mat-flat-button, 64px height, full width)
- Quick chip selectors for the 5 seed personas (dev-mode only)

### Login Flow — Operator

```mermaid
flowchart TD
    A([User opens /auth/login]) --> B[Login form<br/>email + password]
    B --> C{Valid credentials?}
    C -- No --> D[Error: 'Invalid credentials.<br/>Check email and password.']
    D --> B
    C -- Yes --> E{Dev-mode?}
    E -- Yes --> F[Quick persona chips:<br/>'Sign in as Operator'<br/>'Sign in as Manager' ...]
    E -- No --> G[Redirect to role dashboard<br/>from JWT claims]
    F --> G
    G --> H([Persona dashboard])
```

| IT Copy | EN Copy |
|---------|---------|
| "Indirizzo email" | "Email address" |
| "Password" | "Password" |
| "Accedi" | "Sign In" |
| "Credenziali non valide. Controlla email e password." | "Invalid credentials. Check email and password." |
| "Accedi come [Ruolo]" | "Sign in as [Role]" |

**Relevant data-testids:** `email-input`, `password-input`, `login-btn`, `persona-chip-*`

---

## Operator Dashboard — Approval Queue

**Route:** `/operator`
**Component:** `OperatorComponent` → `ApprovalQueueFeed` + `AlertFeed`
**Roles:** `operator`
**Requirements:** UI-03 (approval queue), UI-09

The operator dashboard shows the **HITL approval queue** as the primary focal point
(red badge with count + first pending card highlighted) and `AlertFeed` as secondary.

Each `ApprovalCard` includes:

- Header with agent badge, action type, escalation tier, SLA countdown
- `EvidencePanel` open by default (agent input, tool calls, RAG citations, confidence)
- Motivation textarea (min 10 chars, mandatory)
- Action bar: "Reject" (destructive) + "Approve" (accent)

### Operator Flow — HITL Approval / Rejection

```mermaid
flowchart TD
    START([Operator opens /operator]) --> QUEUE[ApprovalQueueFeed<br/>red badge with pending count]
    QUEUE --> CARD[First ApprovalCard highlighted<br/>agent • action type • SLA countdown]
    CARD --> EP[EvidencePanel open<br/>agent input • tool calls • RAG citations • confidence]
    EP --> MOT{Operator enters motivation}
    MOT -- less than 10 chars --> VAL[Validation: 'The reason must be<br/>at least 10 characters.']
    VAL --> MOT
    MOT -- 10+ chars OK --> ACT{Action}
    ACT -- Approve --> APP[POST /v1/approvals/id/decide<br/>decision=APPROVED]
    ACT -- Reject --> REJ[POST /v1/approvals/id/decide<br/>decision=REJECTED]
    APP --> SSE[SSE approval_resolved<br/>Card → green 'Approved']
    REJ --> SSE2[SSE approval_resolved<br/>Card → red 'Rejected']
    SSE --> NEXT[Next card in queue]
    SSE2 --> NEXT
```

### Full HITL Sequence — Agent → UI → Operator

```mermaid
sequenceDiagram
    participant O as Operator
    participant UI as Angular UI
    participant GW as API Gateway
    participant AG as AI Agent

    AG->>GW: POST /v1/approvals (pending)
    GW-->>UI: SSE approval_pending
    UI->>O: Red badge + card at top
    O->>UI: Opens EvidencePanel
    O->>UI: Enters motivation (≥10 chars)
    O->>UI: Clicks "Approve"
    UI->>GW: POST /v1/approvals/{id}/decide
    GW->>AG: resume(ApprovalDecision)
    GW-->>UI: SSE approval_resolved
    UI->>O: Card → "Approved" (green)
```

| IT Copy | EN Copy |
|---------|---------|
| "Approvazioni Pendenti" | "Pending Approvals" |
| "Nessuna approvazione pendente" | "No pending approvals" |
| "Approva azione" | "Approve action" |
| "Rifiuta" | "Reject" |
| "Motivazione" | "Reason" |
| "Inserisci la motivazione (min. 10 caratteri)..." | "Enter your reason (min. 10 characters)..." |
| "La motivazione deve contenere almeno 10 caratteri." | "The reason must be at least 10 characters." |
| "2 min rimasti" | "2 min remaining" |
| "Limite di 12 alert/ora raggiunto. Nuovi alert sospesi temporaneamente." | "12 alerts/hour limit reached. New alerts temporarily suspended." |

**Relevant data-testids:** `approval-queue-feed`, `approval-card`, `evidence-panel`,
`motivation-textarea`, `approve-btn`, `reject-btn`, `alert-feed`

---

## Technician Dashboard — RCA / Maintenance View

**Route:** `/technician`
**Component:** `TechnicianComponent`
**Roles:** `technician`, `maintenance-engineer`
**Requirements:** UI-02, UI-09

The technician dashboard is the entry point for Root Cause Analysis and maintenance
intervention flows suggested by the `RCASpecialist` and `PredictiveMaintenance` agents.

### Technician Flow — RCA and Maintenance

```mermaid
flowchart TD
    START([Technician opens /technician]) --> ALERTS[AlertFeed: anomalies detected<br/>by AnomalyDetector/PredictiveMaintenance]
    ALERTS --> SEL{Select alert}
    SEL --> RCA[RCA view:<br/>root cause suggested by agent<br/>+ sensor evidence + confidence]
    RCA --> DEC{Technician evaluates}
    DEC -- Approves intervention plan --> HITL[HITL approval:<br/>POST /v1/approvals/id/decide APPROVED]
    DEC -- Modifies plan --> MOD[Enters modification reason<br/>+ updated parameters]
    MOD --> HITL
    DEC -- Escalation --> ESC[Escalate to shift-supervisor<br/>tier 2 HITL]
    HITL --> WO[Work order created<br/>in MES system]
    WO --> DONE([Intervention scheduled])
```

---

## Manager / CIO Dashboard — KPI Control Room

**Route:** `/manager` (CIO Elena also redirected here)
**Component:** `ManagerComponent` → `KpiGrid` + `ChartsRow`
**Roles:** `shift-supervisor`, `manager`, `cio`
**Requirements:** UI-04 (KPI dashboard), UI-09

The manager dashboard shows the **KPI grid** in real time via SSE.
CSS Grid layout: 3 columns on desktop (≥1024px), 2 on tablet, 1 on mobile.

### Manager Flow — Real-Time KPI Monitoring

```mermaid
flowchart TD
    START([Manager opens /manager]) --> SSE_CONN[SseService connects to<br/>/v1/stream/kpi + /v1/stream/approvals]
    SSE_CONN --> KPI[KpiGrid: 6 live tiles<br/>OEE • MTTR • MTBF • Scrap Rate • Throughput • Downtime]
    KPI --> THRES{Threshold breached?}
    THRES -- No --> KPI
    THRES -- Yes --> TILE_RED[Tile turns red<br/>Governor alert if >80% AUTO]
    TILE_RED --> REVIEW{Manager reviews}
    REVIEW -- Drill-down --> CHART[ChartsRow: trend charts<br/>LineChart OEE • BarChart downtime]
    REVIEW -- Corrective action --> HITL[Manual HITL override<br/>via ApprovalQueue]
    CHART --> KPI
    HITL --> KPI
```

The 6 monitored KPIs with thresholds:

| KPI | Unit | Green | Warning | Red |
|-----|------|-------|---------|-----|
| OEE | % | ≥ 85% | 80–84% | < 80% |
| MTTR | min | ≤ 30 | 30–60 | > 60 |
| MTBF | hours | ≥ 72h | 48–72h | < 48h |
| Scrap Rate | % | ≤ 2% | 2–5% | > 5% |
| Throughput | kg/h | ≥ baseline | 90–99% | < 90% |
| Downtime | % | ≤ 5% | 5–10% | > 10% |

| IT Copy | EN Copy |
|---------|---------|
| "Sala Controllo" | "Control Room" |
| "In tempo reale" | "Live" |
| "Non connesso" | "Disconnected" |
| "Dati non disponibili. Controlla la connessione al server." | "Data unavailable. Check server connection." |
| "Attenzione: più dell'80% delle azioni recenti è stato auto-approvato." | "Warning: more than 80% of recent actions were auto-approved." |

**Relevant data-testids:** `kpi-grid`, `kpi-tile-oee`, `kpi-tile-mttr`, `charts-row`,
`sse-indicator`, `governor-alert`

### Real-Time KPI via SSE

The `SseService` manages the Server-Sent Events connection with automatic reconnection
(exponential backoff: 1s → 2s → 4s → max 30s).

| SSE Event | Subject | UI Action |
|-----------|---------|-----------|
| `kpi_update` | `/v1/stream/kpi` | Updates KPI Signal in real time |
| `approval_pending` | `/v1/stream/approvals` | Red badge on "Approvals" nav item |
| `alert_new` | `/v1/stream/alerts` | Append to AlertFeed (max 12/hour) |
| `approval_resolved` | `/v1/stream/approvals` | Card → approved/rejected |
| `sse_heartbeat` | all | Reset reconnection timer |

---

## Language Toggle (IT / EN)

**Position:** TopBar, always visible.
**Requirement:** UI-07 (i18n runtime switch)

The language toggle uses `@jsverse/transloco` to switch language at runtime without
a page reload. State is persisted in `localStorage['sft_locale']`.

| Locale | Behaviour |
|--------|-----------|
| IT (default) | SSR rendering in Italian; no browser dependency |
| EN | Lazy-loads the transloco bundle `/en.json` (≤ 500ms) |

**data-testid:** `language-toggle` — used in the screenshot spec and E2E tests.

---

## Component Architecture

```
AppShell
├── TopBar (64px)
│   ├── LanguageToggle [data-testid="language-toggle"]
│   ├── ThemeToggle [data-testid="theme-toggle"]
│   └── SSE LiveIndicator [data-testid="sse-indicator"]
├── NavigationRail (72px desktop) / BottomNav (mobile)
└── RouterOutlet
    ├── /auth/login → LoginPage
    ├── /operator   → OperatorComponent (ApprovalQueueFeed + AlertFeed)
    ├── /manager    → ManagerComponent (KpiGrid + ChartsRow)
    ├── /technician → TechnicianComponent
    ├── /admin      → AdminComponent
    └── /demo       → DemoComponent (PersonaWalkthrough)
```

All components use Angular Signals for reactivity and are protected by
the RBAC guard (`JwtService` via `RBAC_GUARD_SERVICE_TOKEN`).
