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
import { ApprovalQueueFeedComponent } from '../../shared/approval-queue/approval-queue-feed.component';
import { AlertFeedComponent } from '../../shared/alert-feed/alert-feed.component';
import { KpiTileComponent, KpiKey } from '../../shared/kpi-tile/kpi-tile.component';

/** KPI keys shown in the compact summary row on the operator area */
const OPERATOR_KPI_KEYS: KpiKey[] = ['oee', 'scrap_rate', 'downtime'];

/** SSE stream endpoint for KPI updates (UI-SPEC SSE Contract) */
const SSE_STREAM_URL = '/v1/stream/kpi';

/**
 * OperatorComponent — Area Operatore.
 *
 * Requirements: HITL-01, HITL-04, UI-01, UI-06, 10-UI-SPEC Component 1.
 *
 * Layout: 2-column (desktop ≥1024px): ApprovalQueueFeed (primary focal) + right
 * column (AlertFeed secondary + compact KPI summary row).
 *
 * SSR guard: connect() called only in browser via isPlatformBrowser().
 * Token: reads from JwtService — never from browser API in constructor (T-10-08-01).
 * data-testid="operator-area" — Playwright landing point for /operator.
 */
@Component({
  selector: 'sft-operator',
  standalone: true,
  imports: [
    CommonModule,
    ApprovalQueueFeedComponent,
    AlertFeedComponent,
    KpiTileComponent,
  ],
  template: `
    <div class="sft-operator" data-testid="operator-area">

      <!-- Disconnection warning banner (10-UI-SPEC: shown after 5s) -->
      @if (sseService.disconnectedTooLong()) {
        <div
          class="sft-operator__sse-banner"
          role="alert"
          aria-live="assertive">
          <span class="material-symbols-outlined sft-operator__sse-banner-icon" aria-hidden="true">
            wifi_off
          </span>
          <span>Connessione interrotta. Riconnessione in corso...</span>
        </div>
      }

      <!-- Compact KPI Summary Row -->
      <section class="sft-operator__kpi-row" aria-label="Riepilogo KPI">
        @for (kpiKey of kpiKeys; track kpiKey) {
          <sft-kpi-tile
            [key]="kpiKey"
            [value]="kpiValue(kpiKey)">
          </sft-kpi-tile>
        }
      </section>

      <!-- Main 2-column layout -->
      <div class="sft-operator__content">

        <!-- Primary focal: Approval Queue Feed (col-1) -->
        <main class="sft-operator__primary" aria-label="Coda approvazioni">
          <sft-approval-queue-feed
            [approvals]="sseService.approvals()">
          </sft-approval-queue-feed>
        </main>

        <!-- Secondary: Alert Feed (col-2) -->
        <aside class="sft-operator__secondary" aria-label="Feed alert">
          <sft-alert-feed
            [alerts]="sseService.alerts()"
            [rateLimitReached]="rateLimitReached()">
          </sft-alert-feed>
        </aside>

      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sft-operator {
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-4, 16px);
      box-sizing: border-box;
      min-height: 100%;
    }

    /* SSE disconnection banner */
    .sft-operator__sse-banner {
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

    .sft-operator__sse-banner-icon {
      font-size: 20px;
      flex-shrink: 0;
    }

    /* Compact KPI summary row — 3 tiles */
    .sft-operator__kpi-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: var(--sft-space-4, 16px);
    }

    @media (max-width: 767px) {
      .sft-operator__kpi-row {
        grid-template-columns: 1fr;
      }
    }

    /* 2-column main layout (desktop ≥1024px) */
    .sft-operator__content {
      display: grid;
      grid-template-columns: 1fr 400px;
      gap: var(--sft-space-8, 32px);
      align-items: start;
    }

    /* Tablet: single column */
    @media (max-width: 1023px) {
      .sft-operator__content {
        grid-template-columns: 1fr;
      }
    }

    .sft-operator__primary {
      /* ApprovalQueueFeed takes all available space */
      min-width: 0;
    }

    .sft-operator__secondary {
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-operator__sse-banner {
        transition: none;
      }
    }
  `],
})
export class OperatorComponent implements OnInit {
  readonly sseService = inject(SseService);
  private readonly jwtService = inject(JwtService);
  private readonly platformId = inject(PLATFORM_ID);

  /** KPI keys displayed in the compact summary row */
  readonly kpiKeys = OPERATOR_KPI_KEYS;

  /**
   * Whether the 12/hr HITL-10 rate limit has been reached.
   * Derived from the alerts signal count.
   */
  readonly rateLimitReached = computed<boolean>(
    () => this.sseService.alerts().length >= 12,
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
   */
  kpiValue(key: KpiKey): number | null {
    const snap = this.sseService.kpiSnapshot();
    if (!snap) return null;
    return snap[key] ?? null;
  }
}
