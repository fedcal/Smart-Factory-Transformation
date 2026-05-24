import {
  inject,
  Injectable,
  PLATFORM_ID,
  signal,
  computed,
  OnDestroy,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

// ---------------------------------------------------------------------------
// Types — SSE event payloads (10-UI-SPEC SSE Contratto Streaming)
// ---------------------------------------------------------------------------

export interface KpiSnapshot {
  oee: number;
  mttr: number;
  mtbf: number;
  scrap_rate: number;
  throughput: number;
  downtime: number;
}

export interface ApprovalPendingEvent {
  approval_id: string;
  agent: string;
  tier: string;
  sla_seconds: number;
}

export interface ApprovalResolvedEvent {
  approval_id: string;
  status: 'approved' | 'rejected';
}

export interface AlertNewEvent {
  alert_id: string;
  message: string;
  severity: 'info' | 'warning' | 'critical';
}

export type ConnectionStatus = 'connected' | 'disconnected' | 'reconnecting';

/** Reconnect backoff config (10-UI-SPEC: 1s → 2s → 4s → max 30s) */
const BACKOFF_INITIAL_MS = 1_000;
const BACKOFF_MAX_MS = 30_000;

/** Banner threshold — show warning after 5s of disconnection */
const DISCONNECT_BANNER_THRESHOLD_MS = 5_000;

/**
 * SseService — Signal-based Server-Sent Events client.
 *
 * SSR guard: connect() is a no-op when !isPlatformBrowser() (T-10-05-01).
 * Token auth: JWT passed as query param — EventSource cannot set headers
 *   (10-CONTEXT post_research_resolution #2).
 * Reconnection: exponential backoff 1s → 2s → 4s → max 30s.
 * Signals: kpiSnapshot, approvals, alerts, connectionStatus, disconnectedTooLong.
 */
@Injectable({ providedIn: 'root' })
export class SseService implements OnDestroy {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  // ---------------------------------------------------------------------------
  // Public signals
  // ---------------------------------------------------------------------------

  readonly kpiSnapshot = signal<KpiSnapshot | null>(null);
  readonly approvals = signal<ApprovalPendingEvent[]>([]);
  readonly alerts = signal<AlertNewEvent[]>([]);
  readonly connectionStatus = signal<ConnectionStatus>('disconnected');

  /** Time (ms epoch) when last disconnect started; null when connected */
  private readonly _disconnectedAt = signal<number | null>(null);

  /**
   * True after 5s of continuous disconnection — drives the warning banner
   * (10-UI-SPEC: "Mostra banner --sft-warning dopo 5s di disconnessione").
   */
  readonly disconnectedTooLong = computed<boolean>(() => {
    const ts = this._disconnectedAt();
    if (ts === null) return false;
    return Date.now() - ts > DISCONNECT_BANNER_THRESHOLD_MS;
  });

  // ---------------------------------------------------------------------------
  // Private state
  // ---------------------------------------------------------------------------

  private _eventSource: EventSource | null = null;
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _currentBackoffMs = BACKOFF_INITIAL_MS;
  private _currentUrl = '';
  private _currentToken = '';

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Opens the SSE connection to the given URL, appending `?token=<jwt>`.
   *
   * No-op when !isPlatformBrowser (SSR guard — T-10-05-01).
   * Multiple calls disconnect the previous connection first.
   */
  connect(url: string, token: string): void {
    if (!this.isBrowser) {
      // SSR: no-op — EventSource must not be created on the server
      return;
    }

    this._currentUrl = url;
    this._currentToken = token;
    this._openConnection(url, token);
  }

  /**
   * Closes the current EventSource and cancels any pending reconnect timer.
   * Sets connectionStatus to 'disconnected'.
   */
  disconnect(): void {
    this._cancelReconnect();
    this._closeEventSource();
    this.connectionStatus.set('disconnected');
    this._disconnectedAt.set(Date.now());
  }

  /**
   * Handles a MessageEvent from the EventSource.
   * Exposed for direct testing without a live EventSource.
   */
  handleEvent(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data as string) as Record<string, unknown>;
      switch (event.type) {
        case 'kpi_update':
          this.kpiSnapshot.set(data['kpi'] as KpiSnapshot);
          break;

        case 'sse_heartbeat':
          this.connectionStatus.set('connected');
          this._disconnectedAt.set(null);
          this._currentBackoffMs = BACKOFF_INITIAL_MS;
          break;

        case 'approval_pending':
          this.approvals.update((prev) => [
            ...prev,
            data as unknown as ApprovalPendingEvent,
          ]);
          break;

        case 'approval_resolved': {
          const resolved = data as unknown as ApprovalResolvedEvent;
          this.approvals.update((prev) =>
            prev.filter((a) => a.approval_id !== resolved.approval_id),
          );
          break;
        }

        case 'alert_new':
          this.alerts.update((prev) => [
            ...prev,
            data as unknown as AlertNewEvent,
          ]);
          break;

        default:
          break;
      }
    } catch {
      // Malformed JSON — ignore, do not crash
    }
  }

  /**
   * Handles an EventSource error event.
   * Sets status to 'reconnecting' and schedules exponential backoff reconnect.
   * Exposed for direct testing.
   */
  handleError(_event: Event): void {
    this.connectionStatus.set('reconnecting');
    this._disconnectedAt.set(Date.now());
    this._closeEventSource();
    this._scheduleReconnect();
  }

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  ngOnDestroy(): void {
    this.disconnect();
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  private _openConnection(url: string, token: string): void {
    this._closeEventSource();

    const fullUrl = `${url}?token=${encodeURIComponent(token)}`;
    const es = new EventSource(fullUrl);
    this._eventSource = es;

    // Named event handlers (10-UI-SPEC event types)
    const eventTypes: string[] = [
      'kpi_update',
      'sse_heartbeat',
      'approval_pending',
      'approval_resolved',
      'alert_new',
    ];

    for (const type of eventTypes) {
      es.addEventListener(type, (ev: Event) => {
        this.handleEvent(ev as MessageEvent);
      });
    }

    es.onerror = (ev: Event) => {
      this.handleError(ev);
    };

    // Treat initial open as connected
    es.onopen = () => {
      this.connectionStatus.set('connected');
      this._disconnectedAt.set(null);
      this._currentBackoffMs = BACKOFF_INITIAL_MS;
    };
  }

  private _closeEventSource(): void {
    if (this._eventSource) {
      this._eventSource.close();
      this._eventSource = null;
    }
  }

  private _scheduleReconnect(): void {
    this._cancelReconnect();
    const delay = this._currentBackoffMs;
    this._reconnectTimer = setTimeout(() => {
      if (this.isBrowser && this._currentUrl) {
        this._openConnection(this._currentUrl, this._currentToken);
      }
    }, delay);

    // Double backoff up to max
    this._currentBackoffMs = Math.min(
      this._currentBackoffMs * 2,
      BACKOFF_MAX_MS,
    );
  }

  private _cancelReconnect(): void {
    if (this._reconnectTimer !== null) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
  }
}
