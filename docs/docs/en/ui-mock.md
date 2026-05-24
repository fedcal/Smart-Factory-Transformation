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
  - screenshot
  - UI-09
---

# User Interface — Mock UI

## Overview

This page documents the key screens of the **Smart Factory Transformation** Angular 19 SSR
application, captured in both Italian (default) and English.
The UI is designed for use on industrial screens and tablets on the factory floor:
touch targets ≥ 64px, WCAG AA contrast, dark theme by default.

!!! info "Auto-generated screenshots"
    The images on this page are generated automatically by the Playwright spec
    `apps/factory-ui-e2e/src/screenshots.spec.ts` during CI. To regenerate manually:
    
    ```bash
    # Start the full stack
    docker compose up -d
    
    # Generate screenshots
    SFT_SKIP_SCREENSHOTS=false nx e2e ui-factory-e2e --spec=screenshots.spec.ts
    ```

---

## Login Screen

**Route:** `/auth/login`  
**Requirement:** UI-01 (design system), UI-09 (mock-UI docs)

The login page is vertically centred on a `--sft-surface` background (`#121418`).
The card has max-width 400px and contains:

- Email field with label "Email address"
- Password field with show/hide toggle
- "Sign In" CTA (mat-flat-button, 64px height, full width)
- Quick chip selectors for the 5 seed personas (dev-mode only)

=== "Italiano (IT)"

    ![Login IT](../assets/screenshots/it/login.png)

=== "English (EN)"

    ![Login EN](../assets/screenshots/en/login.png)

| IT Copy | EN Copy |
|---------|---------|
| "Indirizzo email" | "Email address" |
| "Password" | "Password" |
| "Accedi" | "Sign In" |
| "Credenziali non valide. Controlla email e password." | "Invalid credentials. Check email and password." |
| "Accedi come [Ruolo]" | "Sign in as [Role]" |

---

## Operator Dashboard — Approval Queue

**Route:** `/operator`  
**Roles:** `operator`  
**Requirements:** UI-03 (approval queue), UI-09

The operator dashboard shows the **HITL approval queue** as the primary focal point
(red badge with count + first pending card highlighted) and `AlertFeed` as secondary.

Each `ApprovalCard` includes:

- Header with agent badge, action type, escalation tier, SLA countdown
- `EvidencePanel` open by default (agent input, tool calls, RAG citations, confidence)
- Motivation textarea (min 10 chars, mandatory)
- Action bar: "Reject" (destructive) + "Approve" (accent)

=== "Italiano (IT)"

    ![Operator IT](../assets/screenshots/it/operator-approval.png)

=== "English (EN)"

    ![Operator EN](../assets/screenshots/en/operator-approval.png)

| IT Copy | EN Copy |
|---------|---------|
| "Approvazioni Pendenti" | "Pending Approvals" |
| "Nessuna approvazione pendente" | "No pending approvals" |
| "Approva azione" | "Approve action" |
| "Rifiuta" | "Reject" |
| "Motivazione" | "Reason" |
| "Inserisci la motivazione (min. 10 caratteri)..." | "Enter your reason (min. 10 characters)..." |
| "La motivazione deve contenere almeno 10 caratteri." | "The reason must be at least 10 characters." |

### HITL Interaction Flow

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

---

## Manager Dashboard — KPI Control Room

**Route:** `/manager`  
**Roles:** `shift-supervisor`, `manager`  
**Requirements:** UI-04 (KPI dashboard), UI-09

The manager dashboard shows the **KPI grid** in real time via SSE.
CSS Grid layout: 3 columns on desktop (≥1024px), 2 on tablet, 1 on mobile.

The 6 monitored KPIs with thresholds:

| KPI | Unit | Green | Warning | Red |
|-----|------|-------|---------|-----|
| OEE | % | ≥ 85% | 80–84% | < 80% |
| MTTR | min | ≤ 30 | 30–60 | > 60 |
| MTBF | hours | ≥ 72h | 48–72h | < 48h |
| Scrap Rate | % | ≤ 2% | 2–5% | > 5% |
| Throughput | kg/h | ≥ baseline | 90–99% | < 90% |
| Downtime | % | ≤ 5% | 5–10% | > 10% |

=== "Italiano (IT)"

    ![Manager IT](../assets/screenshots/it/manager-dashboard.png)

=== "English (EN)"

    ![Manager EN](../assets/screenshots/en/manager-dashboard.png)

| IT Copy | EN Copy |
|---------|---------|
| "Sala Controllo" | "Control Room" |
| "In tempo reale" | "Live" |
| "Non connesso" | "Disconnected" |
| "Dati non disponibili. Controlla la connessione al server." | "Data unavailable. Check server connection." |
| "Attenzione: più dell'80% delle azioni recenti è stato auto-approvato." | "Warning: more than 80% of recent actions were auto-approved." |

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
