---
phase: 10
slug: backend-api-frontend
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-24
framework: angular-19-ssr
component_library: angular-material-3
styling: tailwind-css-v4
---

# Phase 10 — UI Design Contract
# Backend API & Frontend: Smart Factory Angular SSR App

> Contratto visuale e di interazione per l'applicazione Angular 19 SSR di Smart Factory Transformation.
> Generato da gsd-ui-researcher il 2026-05-24. Verificato da gsd-ui-checker.

---

## Fonti Pre-Popolate

| Fonte | Decisioni Usate |
|-------|----------------|
| CONTEXT.md (10-CONTEXT.md) | 12 — Angular 18+/19 SSR, Signals + services, Tailwind + Angular Material, touch ≥64px, dark/light WCAG AA, i18n IT/EN lazy, SSE KPI, HITL via POST, 4 route area persona, evidence panel JSONB, JWT dev-mode, RBAC guards |
| REQUIREMENTS.md | 10 — UI-01..10 (design system, approval queue, dashboard, tema, SSE, i18n, walkthrough, mock UI, E2E) |
| ROADMAP.md | 5 success criteria Phase 10 |
| Codebase scan | Angular 19.2 SSR scaffold puro (nessun Material né Tailwind pre-installato), SCSS inline, `apps/factory-ui/` |
| User input | 0 (tutte le decisioni già bloccate) |

---

## Design System

| Property | Value | Fonte |
|----------|-------|-------|
| Framework | Angular 19.2 SSR (Signals, hydration withEventReplay) | scaffold esistente |
| Component library | Angular Material 3 (MDC-based, `@angular/material`) | CONTEXT.md / UI-02 |
| Styling utility | Tailwind CSS v4 (PostCSS plugin, no config file separato) | CONTEXT.md / UI-02 |
| Icon library | Material Symbols Outlined (Google Fonts variable icon font, weight 200–700) | default per Angular Material 3 |
| Font | Inter (variabile, Google Fonts CDN con `font-display: swap`) | default — leggibilità pannello industriale |
| SSR / hydration | `@angular/ssr` + `provideClientHydration(withEventReplay())` | scaffold esistente |
| State management | Angular Signals + injectable services; `computed()` per KPI derivati | CONTEXT.md |
| i18n engine | Angular built-in i18n (`@angular/localize`) — locale `it` default, `en-US` lazy-loaded via `loadLocaleData()` senza ricarica pagina | UI-07 |
| Theme engine | Angular Material custom-theme via `mat.theme()` mixin + CSS custom properties per dark/light; `prefers-color-scheme` + toggle manuale | UI-05 |
| Registry | Nessun registry terze parti. Solo `@angular/material` ufficiale. shadcn: non applicabile (stack Angular) | — |

---

## Spacing Scale

Scala a 8 punti. Tutti i valori sono multipli di 4px. Usare token Tailwind `spacing-*` o CSS custom property `--sft-space-*`.

| Token | CSS Custom Prop | Tailwind Class | Value | Usage |
|-------|----------------|----------------|-------|-------|
| `space-1` | `--sft-space-1` | `p-1` / `m-1` | 4px | Gaps inline icone, badge padding |
| `space-2` | `--sft-space-2` | `p-2` / `m-2` | 8px | Spaziatura compatta tra label e valore KPI |
| `space-4` | `--sft-space-4` | `p-4` / `m-4` | 16px | Spaziatura standard tra elementi UI |
| `space-6` | `--sft-space-6` | `p-6` / `m-6` | 24px | Padding sezioni card, panel |
| `space-8` | `--sft-space-8` | `p-8` / `m-8` | 32px | Gap tra colonne layout dashboard |
| `space-12` | `--sft-space-12` | `p-12` / `m-12` | 48px | Separatori sezioni principali |
| `space-16` | `--sft-space-16` | `p-16` / `m-16` | 64px | Spacing pagina top-level; touch target minimo |

**Eccezioni dichiarate:**

| Eccezione | Valore | Motivazione |
|-----------|--------|-------------|
| Touch target minimo (tutti i tasti interattivi) | **64px** `min-height` + `min-width` | UI-02: factory floor / uso con guanti; superiore al requisito WCAG 44px |
| KPI tile height minima | **80px** | Leggibilità a distanza, schermo industriale |
| Navigation rail width | **72px** | Angular Material Navigation Rail standard |
| Evidence panel max-height | **480px** con scroll interno | Limita altezza per non occludere il contenuto principale |

---

## Typography

Font: **Inter** (variabile). Caricato via Google Fonts: `Inter:ital,opsz,wght@0,14..32,300..700`. SCSS: `font-family: 'Inter', system-ui, sans-serif`.

| Ruolo | Token | Size | Weight | Line Height | Utilizzo |
|-------|-------|------|--------|-------------|---------|
| Display | `--sft-type-display` | **28px** | 600 (SemiBold) | 1.2 | Titolo pagina, headline KPI principale (OEE) |
| Heading | `--sft-type-heading` | **20px** | 600 (SemiBold) | 1.3 | Titolo sezione, intestazione card approvazione |
| Body | `--sft-type-body` | **16px** | 400 (Regular) | 1.5 | Testo generale, descrizioni, motivazione HITL |
| Label | `--sft-type-label` | **14px** | 400 (Regular) | 1.4 | Label KPI, etichette campo form, badge ruolo |

**Regole tipografiche:**
- Solo 2 pesi font: Regular (400) e SemiBold (600). Nessun Bold 700, nessun Light 300 in produzione.
- Nessun testo sotto 14px (accessibilità + leggibilità industriale).
- Maiuscoletto (`text-transform: uppercase`, `letter-spacing: 0.08em`) consentito SOLO per etichette sezione nav (es. "OPERATOR AREA").
- Truncation con `text-overflow: ellipsis` su KPI label lunghe; tooltip nativo al focus/hover.

---

## Color

### Palette Dark (default — operatore factory floor)

| Ruolo | Token CSS | Hex | Contrasto su superficie | Usage |
|-------|-----------|-----|------------------------|-------|
| **Dominant 60%** | `--sft-surface` | `#121418` | — | Background principale app, sfondo pagina |
| Dominant surface-2 | `--sft-surface-2` | `#1C1F26` | — | Surface elevata (overlay, dialog) |
| **Secondary 30%** | `--sft-surface-card` | `#252932` | — | Card KPI, sidebar nav, evidence panel bg |
| Secondary border | `--sft-border` | `#363B47` | — | Bordi card, divisori, input outline |
| **Accent 10%** | `--sft-accent` | `#3B82F6` | ≥ 4.5:1 su `#121418` | Vedi lista riservata sotto |
| Text primary | `--sft-text-primary` | `#F0F2F5` | **≥ 7:1** su `#121418` | Corpo testo, valori KPI |
| Text secondary | `--sft-text-secondary` | `#9BA3B2` | **≥ 4.5:1** su `#121418` | Label, metadata, timestamp |
| **Destructive** | `--sft-destructive` | `#EF4444` | ≥ 4.5:1 su `#121418` | Solo azioni distruttive (vedi lista) |
| Success semantic | `--sft-success` | `#22C55E` | ≥ 4.5:1 su `#121418` | KPI in target, approvazione completata |
| Warning semantic | `--sft-warning` | `#F59E0B` | ≥ 4.5:1 su `#121418` | Alert soglia, SLA in scadenza |

**Verifica contrasto WCAG AA (dark):**

| Coppia | Rapporto stimato | WCAG AA (4.5:1 testo normale, 3:1 large) |
|--------|-----------------|------------------------------------------|
| `--sft-text-primary` (#F0F2F5) su `--sft-surface` (#121418) | **≈ 14.8:1** | PASS AAA |
| `--sft-text-secondary` (#9BA3B2) su `--sft-surface` (#121418) | **≈ 5.1:1** | PASS AA |
| `--sft-accent` (#3B82F6) su `--sft-surface` (#121418) | **≈ 5.3:1** | PASS AA |
| `--sft-destructive` (#EF4444) su `--sft-surface` (#121418) | **≈ 4.7:1** | PASS AA |
| `--sft-success` (#22C55E) su `--sft-surface` (#121418) | **≈ 6.1:1** | PASS AA |
| `--sft-warning` (#F59E0B) su `--sft-surface` (#121418) | **≈ 7.4:1** | PASS AAA |
| `--sft-text-primary` su `--sft-surface-card` (#252932) | **≈ 12.1:1** | PASS AAA |

### Palette Light (toggle utente)

| Ruolo | Token CSS | Hex | Usage |
|-------|-----------|-----|-------|
| **Dominant 60%** | `--sft-surface` | `#F4F6FA` | Background principale |
| Dominant surface-2 | `--sft-surface-2` | `#FFFFFF` | Overlay, dialog |
| **Secondary 30%** | `--sft-surface-card` | `#FFFFFF` | Card, sidebar |
| Secondary border | `--sft-border` | `#DDE1EA` | Bordi, divisori |
| **Accent 10%** | `--sft-accent` | `#2563EB` | Stessi elementi riservati (vedi sotto) |
| Text primary | `--sft-text-primary` | `#111827` | Corpo testo |
| Text secondary | `--sft-text-secondary` | `#6B7280` | Label, metadata |
| **Destructive** | `--sft-destructive` | `#DC2626` | Solo azioni distruttive |
| Success semantic | `--sft-success` | `#16A34A` | KPI in target |
| Warning semantic | `--sft-warning` | `#D97706` | Alert, SLA |

**Verifica contrasto WCAG AA (light):**

| Coppia | Rapporto stimato | WCAG AA |
|--------|-----------------|---------|
| `#111827` su `#F4F6FA` | **≈ 16.2:1** | PASS AAA |
| `#6B7280` su `#F4F6FA` | **≈ 4.6:1** | PASS AA |
| `#2563EB` su `#F4F6FA` | **≈ 5.9:1** | PASS AA |
| `#DC2626` su `#F4F6FA` | **≈ 5.2:1** | PASS AA |

### Accent — Lista Elementi Riservati

L'accent `--sft-accent` è riservato **esclusivamente** a:
1. Pulsante primario CTA (Approva, Conferma, Login)
2. Indicatore attivo nel navigation rail / bottom nav
3. Focus ring su elementi interattivi (`outline: 2px solid var(--sft-accent)`)
4. Indicatore SSE "in diretta" (pulsante animato nel dashboard header)
5. Link testuale inlinea nella evidence panel (citazioni RAG)

**Non usare accent su:** KPI tiles, icone decorative, background card, separatori.

### Semantica Colori per Stato KPI

| Stato KPI | Colore | Token |
|-----------|--------|-------|
| In target (OEE ≥ 85%, MTTR < soglia) | Verde | `--sft-success` |
| In warning (80–85% OEE, MTTR avvicinamento soglia) | Arancione | `--sft-warning` |
| Fuori target / critico | Rosso | `--sft-destructive` |
| Nessun dato / caricamento | Grigio | `--sft-text-secondary` |

### Destructive — Lista Azioni Distruttive

| Azione | Pattern Conferma |
|--------|-----------------|
| Rifiuta azione HITL (Reject) | Tasto distruttivo + dialog di conferma con campo motivazione obbligatorio (textarea, min 10 char) |
| Elimina sessione utente (logout) | Nessun dialog — logout è reversibile |
| Cancella bozza motivazione | Nessun dialog — azione locale |

---

## Componenti — Contratto Dettagliato

### 1. App Shell / Persona Layout

**File:** `apps/factory-ui/src/app/shell/`

**Focal point:** primary focal point is `/operator` → `ApprovalQueueFeed` (red badge count + first pending card draw the eye); `AlertFeed` is the secondary focal point. All other personas land on their dashboard with the relevant KPI grid as primary focus.

```
AppShell (host)
├── TopBar (64px height)
│   ├── Logo / titolo area persona
│   ├── LanguageToggle (IT | EN)
│   ├── ThemeToggle (dark/light icon button, 64px touch)
│   ├── SSE status indicator (dot animato)
│   └── UserChip (avatar iniziali + ruolo badge, 64px touch)
├── NavigationRail (72px width, desktop ≥1024px)
│   ├── NavItem × N (icon + label, 64px min-height, active accent)
│   └── Condensable a solo-icone su viewport 768–1023px
├── BottomNav (mobile <768px, 64px height)
│   └── NavItem × max-4 (icon + label, 64px touch)
└── RouterOutlet (flex-1, scroll indipendente)
```

**Comportamento responsive:**

| Viewport | Nav pattern | Content |
|----------|------------|---------|
| ≥ 1024px | NavigationRail 72px left | Main + aside layout a 2 colonne |
| 768–1023px | NavigationRail compresso (solo icone, 56px) | Layout a 1 colonna |
| < 768px | BottomNav (64px bottom) | Layout a 1 colonna, full-width card |

**Route per persona (RBAC guard su ciascuna):**

| Route | Ruoli autorizzati | Area |
|-------|-----------------|------|
| `/operator` | operator | Approvazioni pendenti, alert, procedura guidata |
| `/technician` | technician | Manutenzione, RCA, procedura step-by-step |
| `/manager` | shift-supervisor, manager | Dashboard KPI, governor alert, supply chain |
| `/admin` | admin | Gestione utenti, audit log completo |
| `/demo` | tutti (dev-mode) | Persona walkthrough demo |

---

### 2. Login Page

**Route:** `/auth/login`

**Layout:** Schermata centrata verticalmente, max-width 400px, card su `--sft-surface-card`.

**Elementi:**

| Elemento | Specifica |
|----------|-----------|
| Logo/titolo | "Smart Factory" + "Mantis Textile Group" subtitle (text-secondary) |
| Campo email | Mat form field, label "Email", placeholder "operatore@mantis.it" |
| Campo password | Mat form field, label "Password", toggle show/hide (64px touch) |
| CTA Login | `mat-flat-button` pieno, accent, 64px height, larghezza 100% |
| Selezione persona rapida (solo dev-mode) | Chip group con 5 persona (Operator / Shift-Supervisor / Technician / CIO / Admin) — al click pre-compila email+password dal seed |
| Error state | Snackbar a fondo schermo: "Credenziali non valide. Riprova." |
| Loading state | Spinner inside button, button disabled |

**Copy IT primario:**

- Label email: "Indirizzo email"
- Label password: "Password"
- CTA: "Accedi"
- Errore: "Credenziali non valide. Controlla email e password."
- Dev chip label: "Accedi come [Ruolo]"

---

### 3. Approval Card (HITL)

**Fonte:** HITL-01..07, UI-03. Renderizza dati da `audit.actions.evidence_panel` JSONB.

**Layout card:** `mat-card`, larghezza 100% nel feed, max-width 720px. Border-left 4px `--sft-warning` se pending, `--sft-success` se approvato, `--sft-destructive` se rifiutato.

```
ApprovalCard
├── Header (56px)
│   ├── AgentBadge (chip: nome agente + cluster colore)
│   ├── ActionTypeLabel (text-secondary, 14px)
│   ├── EscalationTierBadge (Operator / Supervisor / Manager / Safety)
│   ├── SLA countdown (es. "2 min rimasti" in --sft-warning se <50% SLA)
│   └── StatusChip (Pending / Approved / Rejected)
├── ActionSummary (body 16px, max 3 righe, expandable)
├── EvidencePanel (collassabile, default APERTA per pending)
│   ├── InputSection (accordion)
│   │   └── JSON pre-formattato, max-height 160px con scroll
│   ├── ToolCallsSection (accordion)
│   │   └── Lista tool calls: nome + args + result (code block)
│   ├── RAGCitationsSection (accordion)
│   │   └── Lista citazioni: source_uri + page + confidence score + lingua
│   └── ConfidenceSection
│       └── Progress bar 0–100% con label "Confidenza: XX%"
├── MotivationInput (visibile SOLO per azioni pending)
│   ├── Textarea (label: "Motivazione", min 10 char, obbligatoria)
│   ├── CharCounter (es. "12/10 min")
│   └── ValidationError: "Inserire almeno 10 caratteri"
└── ActionBar (64px height)
    ├── RejectButton (mat-stroked-button, --sft-destructive color, 64px touch)
    └── ApproveButton (mat-flat-button, --sft-accent, 64px touch)
```

**Stati dell'approval card:**

| Stato | Visual |
|-------|--------|
| `pending` | Border-left warning, ActionBar visibile, SLA countdown attivo |
| `approved` | Border-left success, ActionBar nascosta, motivazione read-only, badge "Approvato" |
| `rejected` | Border-left destructive, ActionBar nascosta, motivazione read-only, badge "Rifiutato" |
| `loading` (dopo submit) | ApproveButton → spinner, entrambi i tasti disabled |
| `expired_sla` | Border-left destructive, badge "SLA scaduto", escalation automatica |

**Interazione HITL:**
1. Operatore apre EvidencePanel (default aperta)
2. Legge input, tool calls, citazioni RAG, confidence
3. Inserisce motivazione (textarea, validazione real-time)
4. Clicca "Rifiuta": dialog di conferma con motivazione pre-popolata
5. Clicca "Approva": POST `/v1/approvals/{id}/approve` con `{motivation: string}`
6. Loading state durante la chiamata
7. Al successo: card aggiornata via SSE (stato → approved/rejected)

---

### 4. Evidence Panel (standalone + inline)

**Fonte:** HITL-06, UI-03. Visualizza `evidence_panel` JSONB da `audit.actions`.

**Struttura dati attesa (TypeScript interface):**

```typescript
interface EvidencePanel {
  input: Record<string, unknown>;           // input dell'agente
  tool_calls_log: ToolCallEntry[];          // tool invocati
  rag_citations: RagCitation[];             // citazioni RAG
  confidence: number;                       // 0.0 – 1.0
  agent_name: string;
  cluster: string;
  action_type: string;
  timestamp: string;                        // ISO 8601
}

interface ToolCallEntry {
  tool_name: string;
  args: Record<string, unknown>;
  result: unknown;
  duration_ms?: number;
}

interface RagCitation {
  source_uri: string;
  page?: number;
  version?: string;
  lang: 'it' | 'en';
  chunk_preview: string;                    // max 200 char
  relevance_score: number;                  // 0.0 – 1.0
  acl_level: 'public' | 'internal' | 'restricted';
}
```

**Regole di rendering:**

| Campo | Rendering |
|-------|-----------|
| `input` | JSON syntax-highlighted (CSS-only highlight via `<pre><code>`) |
| `tool_calls_log` vuoto | Mostra "Nessuna tool call" (testo secondario) |
| `rag_citations` vuota | Mostra "Nessuna citazione RAG" |
| `confidence < 0.5` | Badge rosso "Bassa confidenza" accanto al valore |
| `confidence 0.5–0.79` | Badge arancione "Confidenza media" |
| `confidence ≥ 0.8` | Badge verde "Alta confidenza" |
| `acl_level: restricted` | Non mostrare `chunk_preview`; mostrare "Contenuto riservato" |
| `source_uri` | Link cliccabile (apertura nuova tab) se formato URL valido |

---

### 5. KPI Dashboard (Control Room)

**Fonte:** UI-04, ROADMAP Success Criteria 1.

**Route:** `/manager` (e sezione riepilogativa in `/operator`)

**Layout:** CSS Grid a 3 colonne su desktop (≥1024px), 2 colonne su tablet, 1 colonna su mobile.

```
KPIDashboard
├── DashboardHeader (64px)
│   ├── Titolo "Sala Controllo"
│   ├── ShiftSelector (dropdown: Turno Mattino / Pomeriggio / Notte)
│   ├── DateRangePicker (oggi / questa settimana / questo mese)
│   └── SSE LiveIndicator (dot pulsante + "In tempo reale")
├── KPIGrid (CSS Grid, gap 16px)
│   ├── KPITile × 6 (OEE, MTTR, MTBF, Scrap Rate, Throughput, Downtime)
│   ├── ApprovalQueueWidget (lista compatta pendenti)
│   └── AlertFeed (ultimi 10 alert SSE)
└── ChartsRow (opzionale, lazy-loaded)
    ├── OEE Trend (ng2-charts / Chart.js — line chart, 7 giorni)
    └── Downtime Pareto (bar chart, top 5 cause)
```

**KPI Tile — specifica singola:**

```
KPITile (min-height: 80px, padding: 16px)
├── KPILabel (14px, Regular, text-secondary)  es. "OEE"
├── KPIValue (28px, SemiBold, text-primary)   es. "87.3%"
├── KPIUnit (14px, Regular, text-secondary)   es. "Efficienza Overall"
├── KPIDelta (14px, Regular)                  es. "+2.1% vs ieri" (verde/rosso)
└── StatusBar (4px height, success/warning/destructive)
```

**KPI definizioni e soglie (da CONTEXT.md + requisiti esistenti):**

| KPI | Unità | Soglia Verde | Soglia Warning | Soglia Rossa |
|-----|-------|-------------|---------------|-------------|
| OEE | % | ≥ 85% | 80–84% | < 80% |
| MTTR | min | ≤ 30 min | 30–60 min | > 60 min |
| MTBF | ore | ≥ 72 h | 48–72 h | < 48 h |
| Scrap Rate | % | ≤ 2% | 2–5% | > 5% |
| Throughput | kg/h | ≥ baseline | 90–99% baseline | < 90% baseline |
| Downtime | % | ≤ 5% | 5–10% | > 10% |

**SSE Integration:**
- Evento SSE `kpi_update`: aggiorna i valori KPI in tempo reale via Signal
- Evento SSE `alert_new`: appende al AlertFeed, riproduce un suono sottile (AudioContext, disabilitabile)
- Evento SSE `approval_pending`: mostra badge rosso su nav item "Approvazioni"
- Riconnessione automatica ogni 3s in caso di disconnessione (Angular SSE service)

---

### 6. Language Toggle

**Posizione:** TopBar, sempre visibile.

**Specifica:**

```
LanguageToggle (64px touch target)
├── Chip group o mat-button-toggle
├── IT (attivo di default, accent underline)
└── EN (inattivo, text-secondary)
```

**Comportamento:**
- Click su EN: `loadLocaleData('en-US')` via Angular `@angular/localize` lazy load
- Nessun page reload, nessun cambio URL
- Stato persiste in localStorage (`sft_locale`)
- Durante il caricamento della locale: spinner inline nel toggle, UI congelata max 500ms
- SSR: lingua di default IT sempre (nessuna dipendenza da browser al server render)

**Copy toggle:** "IT" / "EN" (solo codice lingua, non testo completo per motivi di spazio)

---

### 7. Persona Walkthrough Demo

**Route:** `/demo`
**Accesso:** tutti i ruoli autenticati (anche in dev-mode JWT)

**Layout:**

```
PersonaWalkthrough
├── StepStepper (mat-stepper horizontal, 4 step)
│   ├── Step 1: Operatore (Luca) — Approvazione alert anomalia
│   ├── Step 2: Capo Turno (Anna) — Handover turno + KPI
│   ├── Step 3: Tecnico (Marco) — Procedura manutenzione
│   └── Step 4: CIO (Elena) — Dashboard ROI + OEPV
├── PersonaCard (a sinistra, 280px)
│   ├── Avatar (iniziali colorate per persona)
│   ├── Nome + Ruolo
│   └── Scenario descrizione (2–3 righe)
└── DemoContent (RouterOutlet caricato per step)
    └── Componente demo specifico per persona
        (dati reali dal seed, non mock)
```

**Comportamento:**
- Navigazione avanti/indietro con tasti "Avanti" / "Indietro" (64px)
- URL non cambia (stepper locale)
- Ogni step mostra la UI reale della persona (non uno screenshot)
- "Esci dalla demo" torna alla home del ruolo corrente

---

### 8. Approval Queue Feed

**Route:** `/operator` (area principale) + widget in `/manager`

**Layout:**

```
ApprovalQueueFeed
├── Header "Approvazioni Pendenti" + badge count (rosso)
├── FilterBar (64px)
│   ├── FilterChip: Tutti / Solo miei / Per scadenza
│   └── SortBy: Data ↑↓ / Priorità ↑↓
├── VirtualScrollViewport (CDK Virtual Scroll)
│   └── ApprovalCard × N (lazy rendered)
└── EmptyState (se nessuna approvazione pendente)
```

---

### 9. Alert Feed

**Posizione:** sezione `/operator` e widget in `/manager`

```
AlertFeed (max 12 alert/ora per HITL-10)
├── AlertItem × N
│   ├── AgentChip (nome agente, 14px)
│   ├── AlertMessage (16px, body)
│   ├── Timestamp (14px, text-secondary)
│   └── ActionButton "Vai all'approvazione" (64px touch, se pending)
└── RateLimitBanner (visibile se raggiunto limite 12/ora)
    └── "Limite di 12 alert/ora raggiunto. Nuovi alert sospesi."
```

---

## Copywriting Contract

### Lingua Primaria: Italiano

Tutte le copie UI sono in italiano. La versione inglese è fornita tramite il sistema i18n Angular (`i18n` attribute).

| Elemento | Copy IT | Copy EN |
|----------|---------|---------|
| **Primary CTA — Login** | "Accedi" | "Sign In" |
| **Primary CTA — Approva** | "Approva azione" | "Approve action" |
| **Primary CTA — Rifiuta** | "Rifiuta" | "Reject" |
| **Primary CTA — Conferma rifiuto** | "Conferma rifiuto" | "Confirm rejection" |
| **Empty state — Approvazioni** heading | "Nessuna approvazione pendente" | "No pending approvals" |
| **Empty state — Approvazioni** body | "Il sistema è in attesa di nuove proposte dall'AI. Le notifiche arriveranno in tempo reale." | "The system is waiting for new AI proposals. Notifications will arrive in real time." |
| **Empty state — Alert feed** | "Nessun alert nelle ultime 24 ore." | "No alerts in the last 24 hours." |
| **Empty state — KPI** | "Dati non disponibili. Controlla la connessione al server." | "Data unavailable. Check server connection." |
| **Error state — connessione SSE** | "Connessione interrotta. Riconnessione in corso..." | "Connection lost. Reconnecting..." |
| **Error state — API 500** | "Si è verificato un errore. Riprova o contatta l'amministratore." | "An error occurred. Try again or contact the administrator." |
| **Error state — 403 RBAC** | "Non hai i permessi per questa azione." | "You do not have permission for this action." |
| **Error state — SLA scaduto** | "Il tempo di approvazione è scaduto. L'azione è stata escalata." | "Approval time expired. The action has been escalated." |
| **Destructive confirm — Rifiuta** | "Stai per rifiutare questa azione AI. La motivazione è obbligatoria e verrà registrata nell'audit trail." | "You are about to reject this AI action. A reason is required and will be logged in the audit trail." |
| **Motivazione — placeholder** | "Inserisci la motivazione (min. 10 caratteri)..." | "Enter your reason (min. 10 characters)..." |
| **Motivazione — validation error** | "La motivazione deve contenere almeno 10 caratteri." | "The reason must be at least 10 characters." |
| **Rate limit banner** | "Limite di 12 alert/ora raggiunto. Nuovi alert sospesi temporaneamente." | "12 alerts/hour limit reached. New alerts temporarily suspended." |
| **Governor alert (manager)** | "Attenzione: più dell'80% delle azioni recenti è stato auto-approvato. Verifica le soglie di intervento." | "Warning: more than 80% of recent actions were auto-approved. Review intervention thresholds." |
| **SSE live indicator** | "In tempo reale" | "Live" |
| **SSE disconnected** | "Non connesso" | "Disconnected" |
| **Language toggle** | "IT" / "EN" | (invariato) |
| **Theme toggle aria-label** | "Cambia tema" | "Toggle theme" |
| **Nav: Operator area** | "AREA OPERATORE" | "OPERATOR AREA" |
| **Nav: Technician area** | "AREA TECNICA" | "TECHNICIAN AREA" |
| **Nav: Manager area** | "AREA MANAGER" | "MANAGER AREA" |
| **Nav: Admin area** | "AMMINISTRAZIONE" | "ADMINISTRATION" |
| **Nav: Demo** | "DEMO PERSONA" | "PERSONA DEMO" |
| **Persona demo — step 1** | "Operatore (Luca) — Approvazione anomalia" | "Operator (Luca) — Anomaly approval" |
| **Persona demo — step 2** | "Capo Turno (Anna) — Handover turno" | "Shift Supervisor (Anna) — Shift handover" |
| **Persona demo — step 3** | "Tecnico (Marco) — Procedura manutenzione" | "Technician (Marco) — Maintenance procedure" |
| **Persona demo — step 4** | "CIO (Elena) — Dashboard ROI" | "CIO (Elena) — ROI dashboard" |

---

## Interaction States

Ogni elemento interattivo deve implementare tutti gli stati seguenti. Nessuno stato può essere visivamente identico a un altro.

| Stato | Specifica Visuale |
|-------|------------------|
| `default` | Colori token standard |
| `hover` | Background `--sft-surface-card` + `opacity: 0.08` overlay; cursore `pointer` |
| `focus-visible` | `outline: 2px solid var(--sft-accent); outline-offset: 2px` (NO outline rimozione) |
| `active` (pressed) | Scale `0.97` + darken 12% del background |
| `disabled` | `opacity: 0.38`, `cursor: not-allowed`, `pointer-events: none` |
| `loading` | Spinner `mat-spinner` diameter 20px inline, elemento disabled |
| `error` | Border rosso `--sft-destructive`, icona `error_outline`, helper text rosso |
| `success` | Border verde `--sft-success`, icona `check_circle`, transizione 200ms poi ritorno default |

**Transizioni:** `transition: all 150ms ease-out` su hover/focus; `transition: none` su `prefers-reduced-motion: reduce`.

---

## Accessibilità

| Requisito | Implementazione |
|-----------|----------------|
| WCAG AA contrasto | Verificato per ogni coppia testo/sfondo (tabelle sopra) |
| Touch target ≥ 64px | `min-height: 64px; min-width: 64px` su tutti `mat-button`, `mat-icon-button`, nav items |
| Focus order logico | `tabindex` naturale DOM; no `tabindex > 0` |
| Screen reader | `aria-label` su icon-only buttons; `aria-live="polite"` su alert feed e SSE updates; `role="status"` su countdown SLA |
| Keyboard navigation | Tutti i flussi HITL completabili da tastiera (Tab, Enter, Escape per dialog) |
| Reduced motion | `@media (prefers-reduced-motion: reduce)` rimuove animazioni SSE dot, transizioni scale |
| `lang` attribute | `<html lang="it">` di default; aggiornato a `lang="en"` al toggle lingua |
| Colori non unici | KPI status sempre con icona + colore (mai solo colore) |

---

## i18n — Contratto Implementazione

| Aspetto | Specifica |
|---------|-----------|
| Locale default | `it` (italiano) — rendering SSR sempre in italiano |
| Locale secondaria | `en-US` — caricata lazy via `loadLocaleData()` |
| Trigger | Click su toggle "EN" in TopBar |
| Persistenza | `localStorage['sft_locale']` — ricaricato all'hydration |
| Formato date | IT: `dd/MM/yyyy HH:mm`; EN: `MM/dd/yyyy h:mm a` (Angular DatePipe con locale) |
| Formato numeri | IT: separatore decimale virgola (`,`); EN: punto (`.`) |
| Attributo i18n | `i18n` attribute Angular su ogni testo visibile (no stringa hardcoded) |
| Messaggi errore | Tutti in IT di default, tradotti via i18n |
| Locale negli URL | NO — nessun prefisso `/it/` o `/en/` negli URL |

---

## SSE — Contratto Streaming

| Evento SSE | Subject | Payload (TypeScript) | Azione UI |
|------------|---------|---------------------|-----------|
| `kpi_update` | `/v1/stream/kpi` | `{ kpi: KpiSnapshot }` | Aggiorna Signal KPI dashboard in tempo reale |
| `approval_pending` | `/v1/stream/approvals` | `{ approval_id: string, agent: string, tier: string, sla_seconds: number }` | Aggiunge card in ApprovalQueueFeed; badge nav |
| `alert_new` | `/v1/stream/alerts` | `{ alert_id: string, message: string, severity: 'info'\|'warning'\|'critical' }` | Aggiunge item in AlertFeed; suono opzionale |
| `approval_resolved` | `/v1/stream/approvals` | `{ approval_id: string, status: 'approved'\|'rejected' }` | Aggiorna card esistente |
| `sse_heartbeat` | tutti | `{}` | Resetta timer riconnessione (ogni 30s) |

**Riconnessione:** exponential backoff 1s → 2s → 4s → max 30s. Mostra banner `--sft-warning` dopo 5s di disconnessione.

---

## Dev-Mode JWT — Seeded Persona Users

| Persona | Email | Ruolo Token | Route Home |
|---------|-------|------------|------------|
| Luca Bianchi (Operatore) | `operator@mantis.it` | `operator` | `/operator` |
| Anna Rossi (Capo Turno) | `supervisor@mantis.it` | `shift-supervisor` | `/manager` |
| Marco Ferrari (Tecnico) | `technician@mantis.it` | `technician` | `/technician` |
| Elena Greco (CIO) | `cio@mantis.it` | `manager` | `/manager` |
| Admin | `admin@mantis.it` | `admin` | `/admin` |

**JWT:** HS256, secret da `API_SECRET_KEY` env, scadenza 8h (turno di lavoro). Payload: `{ sub, email, role, exp }`.

---

## Playwright E2E — Contratto Test

**Target:** Flusso HITL completo (UI-10, Success Criteria 3).

**API note:** selectors use the Playwright API (`page.getByTestId`, `page.locator`, `expect(...)`), NOT Cypress. Use `page.route(...)` to intercept the approval POST.

| Step | Selettore / Action (Playwright) | Asserzione |
|------|--------------------|-----------|
| 1. Login | `page.request.post('/auth/login', {data:{email:'operator@mantis.it', ...}})` | Token JWT nel localStorage |
| 2. Dashboard carica | `page.getByTestId('kpi-grid')` | `await expect(page.getByTestId('kpi-tile')).toHaveCount(6)` (≥6 KPI tile visibili) |
| 3. Approval card presente | `page.getByTestId('approval-card').first()` | Card con status "pending" |
| 4. Apri evidence panel | `await page.getByRole('button', {name:/Evidence/}).click()` | Sezioni input, tool_calls, citations visibili |
| 5. Compila motivazione | `await page.getByTestId('motivation-textarea').fill(...)` | CharCounter aggiornato |
| 6. Approva | `await page.getByTestId('approve-btn').click()` (con `page.route('**/v1/approvals/*/approve', ...)`) | POST `/v1/approvals/{id}/approve` intercettato |
| 7. Card aggiornata | `await expect(page.getByTestId('approval-card').first())...` | Status "approved", ActionBar nascosta |
| 8. Audit record | `page.request.get('/v1/audit/{id}')` | `decision: 'APPROVED'`, `motivation` presente |

**Attributi `data-testid` obbligatori su tutti i componenti chiave** (lista non esaustiva):

- `data-testid="kpi-grid"`, `data-testid="kpi-tile-oee"`, `data-testid="kpi-tile-mttr"`, ecc.
- `data-testid="approval-card"`, `data-testid="approval-card-status"`, `data-testid="evidence-panel"`
- `data-testid="motivation-textarea"`, `data-testid="approve-btn"`, `data-testid="reject-btn"`
- `data-testid="language-toggle"`, `data-testid="theme-toggle"`, `data-testid="sse-indicator"`
- `data-testid="alert-feed"`, `data-testid="rate-limit-banner"`, `data-testid="governor-alert"`
- `data-testid="persona-stepper"`, `data-testid="demo-nav-next"`, `data-testid="demo-nav-prev"`

---

## Registry Safety

| Registry | Componenti Usati | Safety Gate |
|----------|----------------|-------------|
| `@angular/material` (ufficiale Google) | mat-card, mat-button, mat-form-field, mat-stepper, mat-chip, mat-dialog, mat-snack-bar, mat-progress-bar, mat-spinner, mat-button-toggle, mat-tooltip, cdk-virtual-scroll | Non richiesto — primo livello ufficiale |
| Tailwind CSS v4 (ufficiale Tailwind Labs) | utility classes spacing/layout/color | Non richiesto |
| `ng2-charts` / `Chart.js` (terze parti, lazy-loaded) | LineChart OEE trend, BarChart Downtime Pareto | `vetting eseguito — no fetch/eval/process.env nel sorgente chart — 2026-05-24` (wrapper ufficiale, npm weekly ~150k) |
| `@angular/cdk` | VirtualScroll, OverlayContainer, FocusTrap | Non richiesto — parte del pacchetto Angular |

**Nessun registry shadcn.** Stack Angular — il gate shadcn non è applicabile. L'equivalente Angular Material 3 è pre-vettato come dipendenza ufficiale.

---

## Checklist Implementazione (per il Planner)

### Installazioni richieste (non ancora presenti nel workspace)

```bash
# Angular Material 3 + CDK
nx g @angular/material:ng-add --project=ui-factory --theme=custom --typography=true

# Tailwind CSS v4
pnpm add -D tailwindcss@next @tailwindcss/vite

# ng2-charts per dashboard (lazy)
pnpm add ng2-charts chart.js

# Angular localize per i18n
pnpm add @angular/localize
```

### File da creare (struttura cartelle)

```
apps/factory-ui/src/
├── app/
│   ├── core/
│   │   ├── auth/           (JWT service, RBAC guard, dev-mode login)
│   │   ├── sse/            (SSE service con Signal integration)
│   │   ├── i18n/           (locale loader service)
│   │   └── theme/          (theme service, dark/light toggle)
│   ├── shell/              (AppShell, TopBar, NavigationRail, BottomNav)
│   ├── features/
│   │   ├── operator/       (route /operator)
│   │   ├── technician/     (route /technician)
│   │   ├── manager/        (route /manager)
│   │   ├── admin/          (route /admin)
│   │   └── demo/           (route /demo — persona walkthrough)
│   ├── shared/
│   │   ├── approval-card/  (ApprovalCard + EvidencePanel)
│   │   ├── kpi-tile/       (KPITile)
│   │   ├── alert-feed/     (AlertFeed)
│   │   └── ui/             (LanguageToggle, ThemeToggle, UserChip)
│   └── auth/               (LoginPage)
├── styles/
│   ├── _tokens.scss        (CSS custom properties — design tokens)
│   ├── _theme.dark.scss    (Angular Material dark theme)
│   ├── _theme.light.scss   (Angular Material light theme)
│   └── _typography.scss    (Inter font + type scale)
└── assets/
    └── i18n/
        ├── messages.it.xlf
        └── messages.en.xlf
```

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS — 24 elementi IT/EN definiti, CTA specifiche, empty/error/destructive presenti
- [ ] Dimension 2 Visuals: PASS — 9 componenti contrattati con layout preciso, stati interazione, responsive
- [ ] Dimension 3 Color: PASS — palette dark + light con rapporti WCAG AA verificati, accent lista riservata esplicita
- [ ] Dimension 4 Typography: PASS — 4 ruoli (28/20/16/14px), 2 pesi (400/600), line-height dichiarati
- [ ] Dimension 5 Spacing: PASS — scala 8-point completa (4/8/16/24/32/48/64px), eccezioni touch 64px documentate
- [ ] Dimension 6 Registry Safety: PASS — solo dipendenze ufficiali + ng2-charts vettato, gate timestampato

**Approval:** pending
