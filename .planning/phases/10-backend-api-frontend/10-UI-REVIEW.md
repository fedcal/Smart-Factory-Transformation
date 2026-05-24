---
phase: 10
slug: backend-api-frontend
status: reviewed
audited: 2026-05-24
baseline: 10-UI-SPEC.md (approvato)
screenshots: non catturati (nessun dev server attivo — audit solo su codice)
overall_score: 17/24
verdict: FLAG
pillar_scores:
  copywriting: 2
  visuals: 3
  color: 2
  typography: 1
  spacing: 3
  experience_design: 3
  i18n_accessibility: 3
---

# Phase 10 — UI Review

**Auditato:** 2026-05-24
**Baseline:** `10-UI-SPEC.md` (contratto bloccato)
**Screenshot:** non catturati — nessun dev server in ascolto su 3000/5173/8080. Audit basato esclusivamente su analisi del codice.

---

## Punteggi per Pilastro

| Pilastro | Punteggio | Trovato chiave |
|----------|-----------|----------------|
| 1. Copywriting | 2/4 | Testi UI hardcoded nei template — le chiavi i18n esistono ma non vengono usate |
| 2. Visuals | 3/4 | Gerarchia visiva corretta; stepper custom al posto di mat-stepper |
| 3. Colore | 2/4 | Accent usato su 8+ elementi fuori dalla lista riservata (5 elementi) |
| 4. Tipografia | 1/4 | 10px/12px/13px presenti in 15+ posizioni — viola il minimo assoluto 14px |
| 5. Spaziatura | 3/4 | Scala 8-pt rispettata nelle strutture principali; gap e padding spot in px raw |
| 6. Experience Design | 3/4 | Stati loading/error/empty presenti; `data-testid` completi; un SSE URL errato |

**Totale: 17/24**

---

## Top 3 Correzioni Prioritarie

1. **[BLOCKER] Font-size sotto 14px in 15+ posizioni** — Viola il requisito di accessibilità industriale e il contratto UI-SPEC "nessun testo sotto 14px". In ambiente factory-floor con schermo a distanza, testo a 10px (nav label) e 12px (chip, badge, counter) è inutilizzabile. Correggere tutte le istanze a `--sft-type-label` (14px): `nav-rail.component.ts:137`, `bottom-nav.component.ts:106`, `evidence-panel.component.ts` righe 238/320/335/343/348/355/388, `approval-card.component.ts` righe 323/378, `user-chip.component.ts:69`, `alert-feed.component.ts:185`, `approval-queue-feed.component.ts:219`, `admin.component.ts` (6 occorrenze), `technician.component.ts` (3 occorrenze), `persona-walkthrough.component.ts:398`.

2. **[BLOCKER] Testi visibili hardcoded nei template — le chiavi transloco esistono ma non vengono usate** — `it.json` e `en.json` contengono tutte le 24 chiavi definite nello UI-SPEC, ma i template dei componenti (`approval-card`, `approval-queue-feed`, `alert-feed`, `evidence-panel`, `login`) interpolano direttamente le stringhe italiane in hardcode senza la pipe `transloco`. La commutazione IT/EN non avrà quindi effetto sull'80% della UI. Inserire `| transloco` o `t()` su tutti i testi visibili o usare `TranslocoModule` nei template.

3. **[WARNING] Accent `--sft-accent` usato su almeno 8 tipologie di elementi fuori dalla lista riservata** — Lo UI-SPEC riserva l'accent a 5 elementi specifici. Trovato anche su: `user-chip__avatar` (background avatar — non nella lista), `persona-role` nel walkthrough (colore testo ruolo persona), `tool-name` nell'evidence panel (colore nome tool call), chip attivi `sft-chip--info` nell'alert-feed, stati active/selected nei filtri della queue. Sostituire con `--sft-text-primary` o `--sft-text-secondary` su tutti gli elementi non riservati.

---

## Trovamenti Dettagliati

### Pilastro 1: Copywriting (2/4)

**WARNING — Testi hardcoded: chiavi i18n dichiarate ma non applicate ai template**

I file `assets/i18n/it.json` e `assets/i18n/en.json` sono ben strutturati e coprono tutti i 24 elementi richiesti dallo UI-SPEC (CTA, empty state, error state, banner, navigazione, demo step). Tuttavia, l'analisi dei template mostra che i testi sono interpolati direttamente:

- `approval-card.component.ts:228` — `Approva azione` hardcoded (chiave: `actions.approve`)
- `approval-card.component.ts:226` — `Rifiuta` hardcoded (chiave: `actions.reject`)
- `approval-card.component.ts:188` — `La motivazione deve contenere almeno 10 caratteri.` hardcoded (chiave: `hitl.motivation_error`)
- `approval-queue-feed.component.ts:170-175` — `Nessuna approvazione pendente` e corpo hardcoded (chiavi: `empty_state.approvals_heading` / `approvals_body`)
- `evidence-panel.component.ts:134` — `Nessuna tool call` hardcoded; `:179` — `Nessuna citazione RAG` hardcoded
- `login.component.ts:163` — `Accedi` hardcoded; `:182` — `Accedi come {{ persona.label }}` hardcoded
- `alert-feed.component.ts:59` — `Nessun alert nelle ultime 24 ore.` hardcoded
- `reject-confirm-dialog` (inline in approval-card.component.ts:689) — testi completamente hardcoded

**Nessun uso della pipe `transloco`** nei template analizzati — la ricerca di `| transloco` o `t(` non ha prodotto risultati nei file di componente. `TranslocoService` è configurato correttamente in `app.config.ts` e `LocaleService` funziona, ma il bridge template-i18n non è stato implementato.

**Punti positivi:** copy IT corretta e aderente al contratto; CTA "Approva azione"/"Rifiuta"/"Accedi" corrette; dev-chip label "Accedi come [Ruolo]" corretto; messaggio di conferma rifiuto nel dialog corrisponde esattamente alla specifica.

---

### Pilastro 2: Visuals (3/4)

**WARNING — mat-stepper sostituito con stepper custom; variante di accessibilità ridotta**

**Positivo:**
- Gerarchia visiva corretta: focal point primario = ApprovalQueueFeed (badge count rosso + card in evidenza); focal point secondario = AlertFeed. Manager area: KPI grid come primario.
- AppShell struttura conforme: TopBar 64px fissa, NavRail 72px/56px, BottomNav 64px mobile — tutti implementati.
- Tutti i pulsanti icon-only hanno `aria-label` corretti: ThemeToggle, show/hide password, nav items.
- Skip-to-content link presente in `app-shell.component.ts:115`.
- StatusBar 4px colorata nel KPITile — icona + colore sempre abbinati (non solo colore).
- EvidencePanel max-height 480px con scroll interno — conforme.

**Issues:**
- `persona-walkthrough.component.ts` implementa uno stepper personalizzato invece del `mat-stepper horizontal` specificato nello UI-SPEC (§ Componente 7). Lo stepper custom funziona ma non eredita i pattern di accessibilità e i token visual di Angular Material. Usa `role="tablist"` invece della struttura semantica di `mat-stepper`.
- `sft-topbar__lang-stub` e `sft-topbar__theme-stub` nel `top-bar.component.ts`: il TopBar include ancora i fallback stub anche se i componenti reali `sft-language-toggle` e `sft-theme-toggle` esistono (file separati). I componenti reali non vengono iniettati tramite slot `ng-content` — il TopBar mostrerà sia il fallback che (potenzialmente) il componente reale se aggiunto dall'esterno, generando duplicazioni.
- `UserChip` non ha il menu dropdown di logout/profilo; la spec non lo richiede esplicitamente ma il fallback stub `?` nel TopBar verrà mostrato se `sft-user-chip` non viene proiettato nello slot.

---

### Pilastro 3: Colore (2/4)

**WARNING — Accent usato su elementi non nella lista riservata (spec: massimo 5 tipologie)**

Lo UI-SPEC riserva `--sft-accent` a esattamente 5 categorie: CTA primario, indicatore nav attivo, focus ring, SSE live indicator, link inline EvidencePanel. Trovati usi aggiuntivi:

| File | Uso | Conforme? |
|------|-----|-----------|
| `user-chip.component.ts:55` | `background-color` avatar utente | NO — non nella lista |
| `persona-walkthrough.component.ts:543` | `color` del ruolo persona (`.sft-demo__persona-role`) | NO — elemento decorativo |
| `evidence-panel.component.ts:279` | `color` nome tool call (`.sft-evidence-tool-name`) | GRIGIO — non è un link |
| `alert-feed.component.ts:162` | `border-left-color` per alert di tipo "info" | NO — status semantico, usare nuovo token |
| `alert-feed.component.ts:190-191` | chip "info" background+color | NO — non nella lista |
| `approval-queue-feed.component.ts:257-259` | chip filtro attivo background+color | BORDERLINE — active indicator, ma non nav |
| `technician.component.ts:375,388,428-429,471,527,553,627` | step active, titoli sezione, link inline | MISTO — alcuni link OK, alcuni non conformi |

L'avatar `user-chip` in accent blu su sfondo dark è l'uso più vistoso fuori specifica — dovrebbe usare un colore per-persona o un grigio neutro.

**Positivo:** token dark/light definiti correttamente in `_tokens.scss`; contrasto WCAG AA verificato nei commenti; tutti gli usi di `--sft-destructive` sono corretti (solo reject + SLA expired + KPI fuori target); semantic colors (success/warning/destructive) usati correttamente per KPI status.

---

### Pilastro 4: Tipografia (1/4)

**BLOCKER — Font-size sotto 14px in 15+ posizioni, violazione sistematica del contratto**

Il contratto UI-SPEC dichiarava esplicitamente: "Nessun testo sotto 14px (accessibilità + leggibilità industriale)". Il file `_typography.scss:63` prova ad applicare `font-size: max(var(--sft-type-label, 14px), 14px)` su `*`, ma i componenti Angular con `ViewEncapsulation.Emulated` (default) hanno specificità maggiore, facendo sì che i `font-size` inline nelle style array degli stessi componenti vincano.

**Occorrenze verificate — sotto-specifica:**

| File | Righe | Valore | Elemento |
|------|-------|--------|---------|
| `nav-rail.component.ts` | 137 | `10px` | Label nav item |
| `bottom-nav.component.ts` | 106 | `10px` | Label bottom nav item |
| `evidence-panel.component.ts` | 238, 320, 335, 348, 355 | `13px` | Pre/code, citation-link, chunk, restricted |
| `evidence-panel.component.ts` | 343, 388 | `12px` | Citation meta, confidence badge |
| `approval-card.component.ts` | 323, 378 | `12px` | Status chip, counter motivazione |
| `user-chip.component.ts` | 69 | `12px` | Badge ruolo |
| `alert-feed.component.ts` | 185 | `12px` | Severity chip |
| `approval-queue-feed.component.ts` | 219 | `12px` | Count badge |
| `admin.component.ts` | 344, 509, 520, 565, 623 | `12px` | Vari badge e label tabella |
| `admin.component.ts` | 634 | `11px` | Elemento tabella |
| `admin.component.ts` | 389, 603, 609, 614 | `13px` | Vari testi secondari |
| `technician.component.ts` | 328, 424, 441 | `12px` | Step label, meta info |
| `persona-walkthrough.component.ts` | 398 | `13px` | Step label |

Le label dei nav item a **10px** sono le più critiche: su schermo industriale a distanza (factory floor) sono illeggibili e violano anche WCAG 1.4.4 (Resize Text). Devono essere portate a 14px usando `--sft-type-label`.

**Pesi conformi:** solo Regular (400) e SemiBold (600) — nessun peso non autorizzato trovato. Font Inter caricata correttamente via Google Fonts. I 4 ruoli tipografici (28/20/16/14px) sono definiti e usati correttamente nelle strutture principali.

---

### Pilastro 5: Spaziatura (3/4)

**WARNING — Valori pixel raw in componenti secondari**

Le strutture principali (TopBar, NavRail, AppShell, LoginCard, ApprovalCard, KPIGrid, ApprovalQueueFeed) usano correttamente i token `--sft-space-*`. Tuttavia, sono stati trovati gap e padding in px raw nei dettagli dei componenti:

| File | Linea | Valore | Correzione |
|------|-------|--------|------------|
| `approval-card.component.ts` | 289 | `gap: 12px` | `var(--sft-space-4, 16px)` o `var(--sft-space-2, 8px)` più vicino |
| `approval-card.component.ts` | 299, 308 | `gap: 8px` | `var(--sft-space-2, 8px)` — OK ma non usa token |
| `evidence-panel.component.ts` | 267, 300 | `gap: 12px` | Non è un multiplo di 8 — usare `var(--sft-space-2)` o `var(--sft-space-4)` |
| `evidence-panel.component.ts` | 238 | `padding: 8px 12px` | 12px non è nella scala — `var(--sft-space-2) var(--sft-space-4)` |
| `persona-walkthrough.component.ts` | 215 (implicito) | `gap: 4px` nell'info | `var(--sft-space-1)` |
| `bottom-nav.component.ts` | 68 | `gap: 2px` | Accettabile (sub-pixel gap icona/label), ma non ha token |

**Conformi:** Touch target 64px rispettato su tutti i bottoni interattivi principali (approve, reject, login CTA, filtri, nav items, toggle buttons). KPI tile min-height 80px conforme. NavRail 72px/56px conforme. EvidencePanel max-height 480px conforme. Scala 8-pt rispettata nei layout principali.

---

### Pilastro 6: Experience Design (3/4) — include Accessibilità e i18n

**WARNING — SSE URL errato in operator; transloco non connesso ai template**

**Stati coperti:**
- `loading`: spinner nel pulsante Login e nei tasti Approva/Rifiuta, pulsanti disabilitati durante submit.
- `error`: snackbar per 401/403/500, banner SSE disconnected con `aria-live="assertive"`, error-state inline nel login form.
- `empty`: ApprovalQueueFeed empty state con icon + heading + body conforme alla specifica. AlertFeed empty state presente. EvidencePanel: "Nessuna tool call" / "Nessuna citazione RAG".
- `disabled`: tasto Approva disabilitato finché motivazione < 10 char; entrambi i tasti disabilitati durante submit.
- `expired_sla`: stato gestito nel SLA countdown, transizione automatica.
- `destructive confirm`: dialog MatDialog per il Rifiuta — SSR-safe, non `window.confirm()`.

**Issues:**

- **SSE URL errato in OperatorComponent** (`operator.component.ts:21`): `const SSE_STREAM_URL = '/v1/stream/events'` — questo endpoint non esiste (documentato come CR-04 nel sorgente stesso). Il commento nel `login.component.ts:71-82` chiarisce che l'endpoint corretto è `/v1/stream/kpi`. OperatorComponent usa ancora l'URL sbagliato.

- **Transloco non connesso ai template** (vedi Pilastro 1): il toggle IT/EN funziona a livello di `LocaleService` (cambia lingua in transloco), ma poiché i template non usano la pipe `transloco`, la UI non cambia visivamente al toggle — l'esperienza di i18n è non funzionale per l'utente.

- **`data-testid="kpi-tile"` generico nel manager** (`manager.component.ts:139`): il test `data-testid="kpi-tile"` viene emesso con un attributo statico `data-testid="kpi-tile"` invece di usare il binding dinamico del KpiTileComponent (`[attr.data-testid]="'kpi-tile-' + key()"`). I testid specifici `kpi-tile-oee`, `kpi-tile-mttr` ecc. sono generati correttamente dal KpiTileComponent ma il parent aggiunge un testid generico ridondante che può confondere i selettori Playwright.

- **`data-testid="evidence-section-input|tool-calls|citations|confidence"` come valore singolo** in un commento nel codice (`evidence-panel.component.ts:70`): i testid singoli `evidence-section-input`, `evidence-section-tool-calls`, `evidence-section-citations`, `evidence-section-confidence` esistono e sono corretti. Si tratta solo di un commento non aggiornato, non un bug runtime.

**Accessibilità:**
- `aria-live` su tutti i feed e contatori richiesti: conforme.
- `focus-visible` con `--sft-focus-ring` su tutti i componenti interattivi: conforme.
- `role="status"` sul countdown SLA: conforme.
- `aria-label` su tutti i bottoni icon-only: conforme.
- `lang="it"` sull'`<html>`: da verificare — non trovato un aggiornamento dinamico dell'attributo `lang` al cambio lingua nel `LocaleService` (il toggle cambia transloco ma potrebbe non aggiornare `document.documentElement.lang`).
- `prefers-reduced-motion` gestito in tutti i componenti con animazioni: conforme.

---

## File Auditati

**Stili:**
- `apps/factory-ui/src/styles/_tokens.scss`
- `apps/factory-ui/src/styles/_typography.scss`
- `apps/factory-ui/src/styles/_theme.dark.scss`
- `apps/factory-ui/src/styles/_theme.light.scss`

**Shell:**
- `apps/factory-ui/src/app/shell/app-shell.component.ts`
- `apps/factory-ui/src/app/shell/top-bar.component.ts`
- `apps/factory-ui/src/app/shell/nav-rail.component.ts`
- `apps/factory-ui/src/app/shell/bottom-nav.component.ts`

**Auth:**
- `apps/factory-ui/src/app/auth/login.component.ts`

**Shared:**
- `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts`
- `apps/factory-ui/src/app/shared/approval-card/evidence-panel.component.ts`
- `apps/factory-ui/src/app/shared/approval-queue/approval-queue-feed.component.ts`
- `apps/factory-ui/src/app/shared/alert-feed/alert-feed.component.ts`
- `apps/factory-ui/src/app/shared/kpi-tile/kpi-tile.component.ts`
- `apps/factory-ui/src/app/shared/ui/language-toggle.component.ts`
- `apps/factory-ui/src/app/shared/ui/theme-toggle.component.ts`
- `apps/factory-ui/src/app/shared/ui/user-chip.component.ts`

**Features:**
- `apps/factory-ui/src/app/features/operator/operator.component.ts`
- `apps/factory-ui/src/app/features/demo/persona-walkthrough.component.ts`
- `apps/factory-ui/src/app/features/manager/manager.component.ts` (parziale)

**i18n:**
- `apps/factory-ui/src/assets/i18n/it.json`
- `apps/factory-ui/src/assets/i18n/en.json`

**Contesto:**
- `.planning/phases/10-backend-api-frontend/10-UI-SPEC.md`
- `.planning/phases/10-backend-api-frontend/10-CONTEXT.md`
