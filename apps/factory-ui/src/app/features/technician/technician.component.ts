import {
  Component,
  OnInit,
  inject,
  PLATFORM_ID,
  computed,
  signal,
} from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { SseService } from '../../core/sse/sse.service';
import { JwtService } from '../../core/auth/jwt.service';
import { KpiTileComponent, KpiKey } from '../../shared/kpi-tile/kpi-tile.component';
import { ApprovalQueueFeedComponent } from '../../shared/approval-queue/approval-queue-feed.component';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** KPI keys relevant to the technician (maintenance-focused) */
const TECHNICIAN_KPI_KEYS: KpiKey[] = ['mttr', 'mtbf', 'downtime'];

/** Default SSE stream endpoint */
const SSE_STREAM_URL = '/v1/stream/events';

/**
 * Procedure step — step-by-step maintenance procedure UI.
 * Displayed as a numbered list with status tracking.
 */
interface ProcedureStep {
  readonly id: number;
  readonly title: string;
  readonly description: string;
  readonly status: 'pending' | 'in-progress' | 'done';
  readonly safetyWarning?: string;
}

/**
 * Active maintenance task surfaced from the seeded data.
 * Based on the technician scenario from UI-SPEC Component 7 (Tecnico Marco).
 */
interface MaintenanceTask {
  readonly id: string;
  readonly machineId: string;
  readonly machineName: string;
  readonly issueType: string;
  readonly rcaSummary: string;
  readonly openedAt: string;
  readonly slaTierLabel: string;
  readonly slaSeconds: number;
}

/** Seeded maintenance task (Tecnico Marco — Piano 10-09 demo scenario) */
const SEEDED_MAINTENANCE_TASK: MaintenanceTask = {
  id: 'MNT-001',
  machineId: 'TLR-04',
  machineName: 'Telaio Rapier 04',
  issueType: 'Vibrazione anomala mandrino',
  rcaSummary:
    'Rilevata vibrazione fuori soglia su mandrino principale. ' +
    'Probabile usura cuscinetto DIN 625-6204. ' +
    'Analisi spettrale indica frequenza 48 Hz (soglia: 35 Hz).',
  openedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  slaTierLabel: 'Tecnico',
  slaSeconds: 3600,
};

/** Step-by-step procedure for the seeded maintenance task */
const SEEDED_PROCEDURE_STEPS: ProcedureStep[] = [
  {
    id: 1,
    title: 'Isolamento macchina',
    description:
      'Posizionare il segnale "FUORI SERVIZIO" e aprire il sezionatore principale. ' +
      'Attendere lo smaltimento dell\'energia accumulata (min. 5 minuti).',
    status: 'done',
    safetyWarning: 'Verificare assenza tensione con multimetro prima di procedere.',
  },
  {
    id: 2,
    title: 'Rimozione pannello laterale',
    description:
      'Rimuovere le 8 viti M6 del pannello laterale sinistro (chiave Torx T30). ' +
      'Conservare le viti in contenitore magnetico.',
    status: 'in-progress',
  },
  {
    id: 3,
    title: 'Ispezione visiva cuscinetto',
    description:
      'Ispezionare il cuscinetto DIN 625-6204 per segni di usura, ' +
      'grasso carbonizzato o pitting sulla pista di rotolamento.',
    status: 'pending',
  },
  {
    id: 4,
    title: 'Sostituzione cuscinetto',
    description:
      'Smontare il cuscinetto con estrattore idraulico. ' +
      'Montare il cuscinetto nuovo (PN: 6204-2RS1-SKF) con pressa manuale. ' +
      'Applicare grasso Mobilgrease XHP 222 (15 g).',
    status: 'pending',
    safetyWarning: 'Non usare fiamma libera per scaldare il cuscinetto.',
  },
  {
    id: 5,
    title: 'Verifica e riavvio',
    description:
      'Rimontare il pannello. Avviare la macchina a vuoto per 10 minuti. ' +
      'Verificare che la vibrazione sia rientrata sotto soglia (< 35 Hz).',
    status: 'pending',
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * TechnicianComponent — Area Tecnica.
 *
 * Requirements: HITL-04, UI-01, 10-UI-SPEC Component 7 (Tecnico Marco).
 *
 * Layout:
 *   - Compact KPI row (MTTR / MTBF / Downtime)
 *   - Active Maintenance Task card (RCA summary)
 *   - Step-by-step procedure accordion (numbered steps with status)
 *   - HITL-04 pending approvals queue filtered to technician tier
 *
 * SSR guard: connect() called only in browser via isPlatformBrowser().
 * Threat model: T-10-09-01 (data read-only from audit endpoints — no mutations here).
 * Note: HITL-03 (Safety Interlock) and HITL-08 (rollback) are Phase 4 backend deferrals.
 *
 * data-testid="technician-area" — Playwright landing point for /technician.
 */
@Component({
  selector: 'sft-technician',
  standalone: true,
  imports: [
    CommonModule,
    KpiTileComponent,
    ApprovalQueueFeedComponent,
  ],
  template: `
    <div class="sft-tech" data-testid="technician-area">

      <!-- SSE disconnection warning banner -->
      @if (sseService.disconnectedTooLong()) {
        <div
          class="sft-tech__sse-banner"
          role="alert"
          aria-live="assertive">
          <span class="material-symbols-outlined sft-tech__sse-banner-icon" aria-hidden="true">
            wifi_off
          </span>
          <span>Connessione interrotta. Riconnessione in corso...</span>
        </div>
      }

      <!-- Page heading -->
      <header class="sft-tech__header">
        <h1 class="sft-tech__title">Area Tecnica</h1>
        <span class="sft-tech__nav-label">AREA TECNICA</span>
      </header>

      <!-- Compact KPI Row: MTTR / MTBF / Downtime -->
      <section class="sft-tech__kpi-row" aria-label="KPI Manutenzione">
        @for (kpiKey of kpiKeys; track kpiKey) {
          <sft-kpi-tile
            [key]="kpiKey"
            [value]="kpiValue(kpiKey)">
          </sft-kpi-tile>
        }
      </section>

      <!-- Active Maintenance Task + RCA -->
      <section class="sft-tech__task-card" aria-label="Intervento attivo">
        <div class="sft-tech__task-header">
          <div class="sft-tech__task-machine">
            <span class="material-symbols-outlined sft-tech__task-icon" aria-hidden="true">
              build
            </span>
            <span class="sft-tech__task-machine-name">{{ task.machineName }}</span>
            <span class="sft-tech__task-machine-id">{{ task.machineId }}</span>
          </div>
          <div class="sft-tech__task-meta">
            <!-- SLA countdown (HITL-04 visibility) — role="timer" for screen readers -->
            <div
              class="sft-tech__sla-badge"
              [class.sft-tech__sla-badge--warning]="slaWarning()"
              role="timer"
              [attr.aria-label]="'Tempo rimanente SLA: ' + slaDisplay()">
              <span class="material-symbols-outlined sft-tech__sla-icon" aria-hidden="true">
                schedule
              </span>
              <span>{{ slaDisplay() }}</span>
            </div>
            <span class="sft-tech__task-tier-badge">{{ task.slaTierLabel }}</span>
          </div>
        </div>

        <div class="sft-tech__task-issue">
          <span class="sft-tech__task-issue-label">Tipo di intervento</span>
          <span class="sft-tech__task-issue-value">{{ task.issueType }}</span>
        </div>

        <!-- RCA summary (Rule 2: always show available diagnostic info) -->
        <div class="sft-tech__rca">
          <h2 class="sft-tech__rca-title">
            <span class="material-symbols-outlined sft-tech__rca-icon" aria-hidden="true">
              manage_search
            </span>
            Analisi Cause Radice (RCA)
          </h2>
          <p class="sft-tech__rca-body">{{ task.rcaSummary }}</p>
        </div>
      </section>

      <!-- Step-by-step procedure -->
      <section class="sft-tech__procedure" aria-label="Procedura manutenzione">
        <h2 class="sft-tech__procedure-title">Procedura Step-by-Step</h2>

        <ol class="sft-tech__steps" role="list">
          @for (step of procedureSteps; track step.id) {
            <li
              class="sft-tech__step"
              [class.sft-tech__step--done]="step.status === 'done'"
              [class.sft-tech__step--in-progress]="step.status === 'in-progress'"
              [class.sft-tech__step--pending]="step.status === 'pending'"
              [attr.aria-current]="step.status === 'in-progress' ? 'step' : null">

              <div class="sft-tech__step-indicator" aria-hidden="true">
                @if (step.status === 'done') {
                  <span class="material-symbols-outlined sft-tech__step-icon sft-tech__step-icon--done">
                    check_circle
                  </span>
                } @else if (step.status === 'in-progress') {
                  <span class="material-symbols-outlined sft-tech__step-icon sft-tech__step-icon--active">
                    radio_button_checked
                  </span>
                } @else {
                  <span class="sft-tech__step-number">{{ step.id }}</span>
                }
              </div>

              <div class="sft-tech__step-content">
                <h3 class="sft-tech__step-title">{{ step.title }}</h3>
                <p class="sft-tech__step-desc">{{ step.description }}</p>

                @if (step.safetyWarning) {
                  <div class="sft-tech__step-warning" role="note">
                    <span class="material-symbols-outlined sft-tech__step-warning-icon" aria-hidden="true">
                      warning
                    </span>
                    <span>{{ step.safetyWarning }}</span>
                  </div>
                }
              </div>
            </li>
          }
        </ol>
      </section>

      <!-- HITL-04: Pending approvals for technician tier -->
      <section class="sft-tech__approvals" aria-label="Approvazioni tecnico">
        <h2 class="sft-tech__approvals-title">
          <span class="material-symbols-outlined sft-tech__approvals-icon" aria-hidden="true">
            approval
          </span>
          Approvazioni in Attesa
        </h2>
        <sft-approval-queue-feed
          [approvals]="technicianApprovals()">
        </sft-approval-queue-feed>
      </section>

    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sft-tech {
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-4, 16px);
      box-sizing: border-box;
      min-height: 100%;
    }

    /* SSE banner */
    .sft-tech__sse-banner {
      display: flex;
      align-items: center;
      gap: 8px;
      background-color: color-mix(in srgb, var(--sft-warning, #F59E0B) 15%, transparent);
      border: 1px solid var(--sft-warning, #F59E0B);
      border-radius: 6px;
      padding: var(--sft-space-2, 8px) var(--sft-space-4, 16px);
      color: var(--sft-warning, #F59E0B);
      font-size: 14px;
    }

    .sft-tech__sse-banner-icon {
      font-size: 20px;
      flex-shrink: 0;
    }

    /* Page header */
    .sft-tech__header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: var(--sft-space-2, 8px);
    }

    .sft-tech__title {
      font-size: 28px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      line-height: 1.2;
      margin: 0;
    }

    .sft-tech__nav-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--sft-text-secondary, #9BA3B2);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    /* KPI row — 3 tiles */
    .sft-tech__kpi-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: var(--sft-space-4, 16px);
    }

    @media (max-width: 767px) {
      .sft-tech__kpi-row {
        grid-template-columns: 1fr;
      }
    }

    /* Active task card */
    .sft-tech__task-card {
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      padding: var(--sft-space-6, 24px);
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
    }

    .sft-tech__task-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: var(--sft-space-4, 16px);
    }

    .sft-tech__task-machine {
      display: flex;
      align-items: center;
      gap: var(--sft-space-2, 8px);
    }

    .sft-tech__task-icon {
      font-size: 24px;
      color: var(--sft-accent, #3B82F6);
    }

    .sft-tech__task-machine-name {
      font-size: 20px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
    }

    .sft-tech__task-machine-id {
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
      padding: 2px 8px;
      background-color: color-mix(in srgb, var(--sft-accent, #3B82F6) 15%, transparent);
      border-radius: 4px;
    }

    .sft-tech__task-meta {
      display: flex;
      align-items: center;
      gap: var(--sft-space-2, 8px);
      flex-wrap: wrap;
    }

    /* SLA badge — HITL-04 visibility */
    .sft-tech__sla-badge {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 4px 12px;
      min-height: 32px;
      border-radius: 16px;
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
      border: 1px solid var(--sft-border, #363B47);
      background-color: transparent;
    }

    .sft-tech__sla-badge--warning {
      color: var(--sft-warning, #F59E0B);
      border-color: var(--sft-warning, #F59E0B);
      background-color: color-mix(in srgb, var(--sft-warning, #F59E0B) 10%, transparent);
    }

    .sft-tech__sla-icon {
      font-size: 16px;
    }

    .sft-tech__task-tier-badge {
      font-size: 12px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 12px;
      background-color: color-mix(in srgb, var(--sft-accent, #3B82F6) 20%, transparent);
      color: var(--sft-accent, #3B82F6);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .sft-tech__task-issue {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .sft-tech__task-issue-label {
      font-size: 12px;
      color: var(--sft-text-secondary, #9BA3B2);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .sft-tech__task-issue-value {
      font-size: 16px;
      color: var(--sft-text-primary, #F0F2F5);
      font-weight: 600;
    }

    /* RCA summary */
    .sft-tech__rca {
      border-top: 1px solid var(--sft-border, #363B47);
      padding-top: var(--sft-space-4, 16px);
    }

    .sft-tech__rca-title {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 16px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      margin: 0 0 8px;
    }

    .sft-tech__rca-icon {
      font-size: 20px;
      color: var(--sft-accent, #3B82F6);
    }

    .sft-tech__rca-body {
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
      line-height: 1.6;
      margin: 0;
    }

    /* Step-by-step procedure */
    .sft-tech__procedure {
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      padding: var(--sft-space-6, 24px);
    }

    .sft-tech__procedure-title {
      font-size: 20px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      margin: 0 0 var(--sft-space-4, 16px);
    }

    .sft-tech__steps {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-2, 8px);
    }

    .sft-tech__step {
      display: flex;
      align-items: flex-start;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-4, 16px);
      border-radius: 6px;
      border: 1px solid var(--sft-border, #363B47);
      transition: background-color 150ms ease-out;
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-tech__step {
        transition: none;
      }
    }

    .sft-tech__step--done {
      opacity: 0.65;
      background-color: color-mix(in srgb, var(--sft-success, #22C55E) 5%, transparent);
    }

    .sft-tech__step--in-progress {
      border-color: var(--sft-accent, #3B82F6);
      background-color: color-mix(in srgb, var(--sft-accent, #3B82F6) 8%, transparent);
    }

    .sft-tech__step--pending {
      background-color: transparent;
    }

    .sft-tech__step-indicator {
      flex-shrink: 0;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .sft-tech__step-icon {
      font-size: 24px;
    }

    .sft-tech__step-icon--done {
      color: var(--sft-success, #22C55E);
    }

    .sft-tech__step-icon--active {
      color: var(--sft-accent, #3B82F6);
    }

    .sft-tech__step-number {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background-color: var(--sft-surface, #121418);
      border: 1px solid var(--sft-border, #363B47);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: 600;
      color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-tech__step-content {
      flex: 1;
      min-width: 0;
    }

    .sft-tech__step-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      margin: 0 0 4px;
    }

    .sft-tech__step-desc {
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
      line-height: 1.5;
      margin: 0;
    }

    .sft-tech__step-warning {
      display: flex;
      align-items: flex-start;
      gap: 6px;
      margin-top: var(--sft-space-2, 8px);
      padding: var(--sft-space-2, 8px) var(--sft-space-4, 16px);
      background-color: color-mix(in srgb, var(--sft-warning, #F59E0B) 12%, transparent);
      border: 1px solid var(--sft-warning, #F59E0B);
      border-radius: 4px;
      font-size: 13px;
      color: var(--sft-warning, #F59E0B);
    }

    .sft-tech__step-warning-icon {
      font-size: 16px;
      flex-shrink: 0;
      margin-top: 1px;
    }

    /* Approvals section */
    .sft-tech__approvals {
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
    }

    .sft-tech__approvals-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 20px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      margin: 0;
    }

    .sft-tech__approvals-icon {
      font-size: 24px;
      color: var(--sft-accent, #3B82F6);
    }
  `],
})
export class TechnicianComponent implements OnInit {
  readonly sseService = inject(SseService);
  private readonly jwtService = inject(JwtService);
  private readonly platformId = inject(PLATFORM_ID);

  /** KPI keys for the maintenance-focused summary row */
  readonly kpiKeys = TECHNICIAN_KPI_KEYS;

  /** Seeded maintenance task */
  readonly task = SEEDED_MAINTENANCE_TASK;

  /** Seeded procedure steps */
  readonly procedureSteps = SEEDED_PROCEDURE_STEPS;

  /**
   * Elapsed seconds since the maintenance task was opened.
   * Used to compute the SLA countdown display (HITL-04 visibility).
   */
  private readonly _elapsedSeconds = signal<number>(
    Math.floor((Date.now() - new Date(SEEDED_MAINTENANCE_TASK.openedAt).getTime()) / 1000),
  );

  /**
   * Remaining SLA seconds (clamps to 0).
   * HITL-04: tier-based SLA countdown displayed prominently.
   */
  readonly slaRemainingSeconds = computed<number>(() =>
    Math.max(0, SEEDED_MAINTENANCE_TASK.slaSeconds - this._elapsedSeconds()),
  );

  /**
   * Human-readable SLA countdown (hh:mm:ss or "Scaduto").
   * role="timer" on the host element for screen reader announcement.
   */
  readonly slaDisplay = computed<string>(() => {
    const remaining = this.slaRemainingSeconds();
    if (remaining === 0) return 'Scaduto';
    const h = Math.floor(remaining / 3600);
    const m = Math.floor((remaining % 3600) / 60);
    const s = remaining % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  });

  /**
   * True when SLA remaining < 50% → warning color (10-UI-SPEC).
   */
  readonly slaWarning = computed<boolean>(
    () => this.slaRemainingSeconds() < SEEDED_MAINTENANCE_TASK.slaSeconds * 0.5,
  );

  /**
   * Approvals filtered to technician tier (HITL-04 per-tier visibility).
   * Filters the shared SseService approvals signal.
   */
  readonly technicianApprovals = computed(() =>
    this.sseService.approvals().filter(
      (a) => a.tier === 'technician' || a.tier === 'Tecnico',
    ),
  );

  ngOnInit(): void {
    // SSR guard: only connect EventSource in the browser
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }
    const token = this.jwtService.getToken();
    if (token) {
      this.sseService.connect(SSE_STREAM_URL, token);
    }
  }

  /**
   * Returns the current KPI value from the SSE snapshot or null.
   */
  kpiValue(key: KpiKey): number | null {
    const snap = this.sseService.kpiSnapshot();
    if (!snap) return null;
    return snap[key] ?? null;
  }
}
