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
import { AlertFeedComponent } from '../../shared/alert-feed/alert-feed.component';
import { ApprovalQueueFeedComponent } from '../../shared/approval-queue/approval-queue-feed.component';
import { ChartsRowComponent, OeeTrendPoint, DowntimePareto } from './charts-row.component';

/** All 6 KPI keys displayed in the control-room grid */
const KPI_GRID_KEYS: KpiKey[] = ['oee', 'mttr', 'mtbf', 'scrap_rate', 'throughput', 'downtime'];

/** SSE stream endpoint for KPI updates (UI-SPEC SSE Contract) */
const SSE_STREAM_URL = '/v1/stream/kpi';

/** Shift options for the ShiftSelector */
const SHIFT_OPTIONS = [
  { value: 'morning', label: 'Turno Mattino' },
  { value: 'afternoon', label: 'Turno Pomeriggio' },
  { value: 'night', label: 'Turno Notte' },
];

/** Date range options */
const DATE_RANGE_OPTIONS = [
  { value: 'today', label: 'Oggi' },
  { value: 'week', label: 'Questa settimana' },
  { value: 'month', label: 'Questo mese' },
];

/**
 * ManagerComponent — Sala Controllo (Control Room).
 *
 * Requirements: UI-04, UI-06, HITL-01, HITL-04, 10-UI-SPEC Component 5.
 *
 * Layout:
 *   DashboardHeader (title + ShiftSelector + DateRangePicker + SSE LiveIndicator)
 *   KPIGrid (data-testid="kpi-grid") — 6 KpiTiles (OEE/MTTR/MTBF/Scrap/Throughput/Downtime)
 *   Widget row (ApprovalQueueWidget + AlertFeed)
 *   @defer ChartsRow (lazy-loaded OEE trend + Downtime Pareto, browser-only)
 *
 * SSR guard: connect() called only in browser via isPlatformBrowser().
 * KPI seeded by GET /v1/kpi on SSR then updated live via SSE kpi_update events.
 * RBAC: roles shift-supervisor + manager (T-10-08-01 Elevation of Privilege).
 * data-testid="kpi-grid" required by Playwright E2E (10-UI-SPEC Playwright contract).
 * T-10-08-03: values from typed KpiSnapshot; text interpolation auto-escapes (no [innerHTML]).
 */
@Component({
  selector: 'sft-manager',
  standalone: true,
  imports: [
    CommonModule,
    KpiTileComponent,
    AlertFeedComponent,
    ApprovalQueueFeedComponent,
    ChartsRowComponent,
  ],
  template: `
    <div class="sft-manager" data-testid="manager-area">

      <!-- Dashboard Header -->
      <header class="sft-manager__header">
        <div class="sft-manager__header-left">
          <h1 class="sft-manager__title">Sala Controllo</h1>
        </div>

        <div class="sft-manager__header-controls">

          <!-- ShiftSelector -->
          <label class="sft-manager__control-label" for="shift-select">Turno</label>
          <select
            id="shift-select"
            class="sft-manager__select"
            [value]="activeShift()"
            (change)="setShift($event)"
            aria-label="Seleziona turno">
            @for (opt of shiftOptions; track opt.value) {
              <option [value]="opt.value">{{ opt.label }}</option>
            }
          </select>

          <!-- DateRangePicker -->
          <label class="sft-manager__control-label" for="date-range-select">Periodo</label>
          <select
            id="date-range-select"
            class="sft-manager__select"
            [value]="activeDateRange()"
            (change)="setDateRange($event)"
            aria-label="Seleziona periodo">
            @for (opt of dateRangeOptions; track opt.value) {
              <option [value]="opt.value">{{ opt.label }}</option>
            }
          </select>

          <!-- SSE LiveIndicator (data-testid="sse-indicator") -->
          <div
            class="sft-manager__live-indicator"
            data-testid="sse-indicator"
            [class.sft-manager__live-indicator--connected]="isConnected()"
            role="status"
            [attr.aria-label]="isConnected() ? 'In tempo reale' : 'Non connesso'">
            <span class="sft-manager__live-dot" aria-hidden="true"></span>
            <span class="sft-manager__live-label">
              {{ isConnected() ? 'In tempo reale' : 'Non connesso' }}
            </span>
          </div>

        </div>
      </header>

      <!-- SSE Disconnection warning banner (shown after 5s) -->
      @if (sseService.disconnectedTooLong()) {
        <div
          class="sft-manager__sse-banner"
          role="alert"
          aria-live="assertive">
          <span class="material-symbols-outlined sft-manager__sse-banner-icon" aria-hidden="true">
            wifi_off
          </span>
          <span>Connessione interrotta. Riconnessione in corso...</span>
        </div>
      }

      <!-- KPI Grid (data-testid="kpi-grid" — required by Playwright E2E) -->
      <section
        class="sft-manager__kpi-grid"
        data-testid="kpi-grid"
        aria-label="Griglia KPI">
        @for (kpiKey of kpiGridKeys; track kpiKey) {
          <sft-kpi-tile
            [key]="kpiKey"
            [value]="kpiValue(kpiKey)"
            data-testid="kpi-tile">
          </sft-kpi-tile>
        }
      </section>

      <!-- Widgets row: ApprovalQueueWidget + AlertFeed -->
      <div class="sft-manager__widgets">

        <!-- Approval Queue Widget (compact) -->
        <section class="sft-manager__widget" aria-label="Coda approvazioni">
          <sft-approval-queue-feed
            [approvals]="sseService.approvals()">
          </sft-approval-queue-feed>
        </section>

        <!-- Alert Feed -->
        <section class="sft-manager__widget" aria-label="Feed alert">
          <sft-alert-feed
            [alerts]="sseService.alerts()"
            [rateLimitReached]="rateLimitReached()">
          </sft-alert-feed>
        </section>

      </div>

      <!-- ChartsRow — lazy via @defer; browser-only (T-10-08-02) -->
      @defer (on viewport) {
        <sft-charts-row
          [kpiSnapshot]="sseService.kpiSnapshot()">
        </sft-charts-row>
      } @loading {
        <div class="sft-manager__charts-loading" aria-busy="true" role="status">
          <span class="material-symbols-outlined sft-manager__charts-spinner" aria-hidden="true">
            hourglass_empty
          </span>
          <span>Caricamento grafici...</span>
        </div>
      } @placeholder {
        <div class="sft-manager__charts-placeholder" aria-hidden="true">
          <span class="material-symbols-outlined">bar_chart</span>
          <span>Grafici storici</span>
        </div>
      }

    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sft-manager {
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-4, 16px);
      box-sizing: border-box;
      min-height: 100%;
    }

    /* Dashboard Header */
    .sft-manager__header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: var(--sft-space-4, 16px);
      min-height: 64px;
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      padding: var(--sft-space-4, 16px);
    }

    .sft-manager__header-left {
      display: flex;
      align-items: center;
      gap: var(--sft-space-4, 16px);
    }

    .sft-manager__title {
      font-size: 28px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      line-height: 1.2;
      margin: 0;
    }

    .sft-manager__header-controls {
      display: flex;
      align-items: center;
      gap: var(--sft-space-4, 16px);
      flex-wrap: wrap;
    }

    .sft-manager__control-label {
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-manager__select {
      min-height: 64px;
      min-width: 160px;
      padding: 0 var(--sft-space-4, 16px);
      background-color: var(--sft-surface, #121418);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 6px;
      color: var(--sft-text-primary, #F0F2F5);
      font-size: 14px;
      cursor: pointer;

      &:focus-visible {
        outline: 2px solid var(--sft-accent, #3B82F6);
        outline-offset: 2px;
      }
    }

    /* SSE LiveIndicator */
    .sft-manager__live-indicator {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 0 var(--sft-space-4, 16px);
      min-height: 64px;
      color: var(--sft-text-secondary, #9BA3B2);
      font-size: 14px;
    }

    .sft-manager__live-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--sft-text-secondary, #9BA3B2);
      flex-shrink: 0;
    }

    .sft-manager__live-indicator--connected .sft-manager__live-dot {
      background-color: var(--sft-success, #22C55E);
      animation: sft-pulse 2s infinite;
    }

    .sft-manager__live-indicator--connected .sft-manager__live-label {
      color: var(--sft-success, #22C55E);
    }

    @keyframes sft-pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-manager__live-dot {
        animation: none;
      }
    }

    /* SSE disconnection banner */
    .sft-manager__sse-banner {
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

    .sft-manager__sse-banner-icon {
      font-size: 20px;
      flex-shrink: 0;
    }

    /* KPI Grid — 3 col desktop, 2 col tablet, 1 col mobile */
    .sft-manager__kpi-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: var(--sft-space-4, 16px);
    }

    @media (max-width: 1023px) {
      .sft-manager__kpi-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    @media (max-width: 767px) {
      .sft-manager__kpi-grid {
        grid-template-columns: 1fr;
      }
    }

    /* Widgets row */
    .sft-manager__widgets {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: var(--sft-space-4, 16px);
      align-items: start;
    }

    @media (max-width: 1023px) {
      .sft-manager__widgets {
        grid-template-columns: 1fr;
      }
    }

    .sft-manager__widget {
      min-width: 0;
    }

    /* Charts lazy loading states */
    .sft-manager__charts-loading,
    .sft-manager__charts-placeholder {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: var(--sft-space-8, 32px);
      color: var(--sft-text-secondary, #9BA3B2);
      justify-content: center;
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
    }

    .sft-manager__charts-spinner {
      font-size: 24px;
    }
  `],
})
export class ManagerComponent implements OnInit {
  readonly sseService = inject(SseService);
  private readonly jwtService = inject(JwtService);
  private readonly platformId = inject(PLATFORM_ID);

  /** All 6 KPI keys for the control-room grid */
  readonly kpiGridKeys = KPI_GRID_KEYS;

  /** Shift and date range filter state */
  readonly shiftOptions = SHIFT_OPTIONS;
  readonly dateRangeOptions = DATE_RANGE_OPTIONS;

  private readonly _activeShift = signal<string>('morning');
  private readonly _activeDateRange = signal<string>('today');

  readonly activeShift = computed(() => this._activeShift());
  readonly activeDateRange = computed(() => this._activeDateRange());

  /**
   * Whether the 12/hr HITL-10 rate limit has been reached.
   * Derived from the alerts signal count.
   */
  readonly rateLimitReached = computed<boolean>(
    () => this.sseService.alerts().length >= 12,
  );

  /** True when SSE is connected */
  readonly isConnected = computed<boolean>(
    () => this.sseService.connectionStatus() === 'connected',
  );

  ngOnInit(): void {
    // SSR guard: only connect EventSource in the browser (T-10-08-01)
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    const token = this.jwtService.getToken();
    if (token) {
      this.sseService.connect(SSE_STREAM_URL, token);
    }
  }

  /**
   * Returns the current numeric value for a given KPI key from the snapshot.
   * Returns null when snapshot is not yet available (grey state).
   * T-10-08-03: typed KpiSnapshot prevents tampering.
   */
  kpiValue(key: KpiKey): number | null {
    const snap = this.sseService.kpiSnapshot();
    if (!snap) return null;
    return snap[key] ?? null;
  }

  setShift(event: Event): void {
    const target = event.target as HTMLSelectElement;
    this._activeShift.set(target.value);
  }

  setDateRange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    this._activeDateRange.set(target.value);
  }
}
