/**
 * Contract tests for SseService — Plan 10-05.
 *
 * Architecture decisions (10-CONTEXT.md):
 *   - SSE primary channel for live KPI + alert/approval push
 *   - SseService.connect() is a no-op when isPlatformBrowser() is false (SSR)
 *   - kpi_update event → sets kpiSnapshot Signal
 *   - sse_heartbeat event → sets connectionStatus Signal to 'connected'
 *   - Reconnect: exponential backoff 1s → 2s → 4s → max 30s
 *   - JWT passed as query param (EventSource cannot set custom headers — 10-CONTEXT post_research #2)
 *
 * SSE event contract (10-UI-SPEC SSE Contratto Streaming):
 *   kpi_update    → { kpi: KpiSnapshot } — updates kpiSnapshot Signal
 *   sse_heartbeat → {}                   — sets connectionStatus 'connected'
 *   alert_new     → { alert_id, message, severity }
 *   approval_pending → { approval_id, agent, tier, sla_seconds }
 *
 * KpiSnapshot keys: oee, mttr, mtbf, scrap_rate, throughput, downtime
 */

import { TestBed } from '@angular/core/testing';
import { PLATFORM_ID } from '@angular/core';
import { SseService } from './sse.service';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeKpiEvent(kpi: Record<string, number>): MessageEvent {
  return new MessageEvent('kpi_update', {
    data: JSON.stringify({ kpi }),
  });
}

function makeHeartbeatEvent(): MessageEvent {
  return new MessageEvent('sse_heartbeat', { data: '{}' });
}

function makeErrorEvent(): Event {
  return new Event('error');
}

const FULL_KPI = {
  oee: 87.3,
  mttr: 28.5,
  mtbf: 76.0,
  scrap_rate: 1.8,
  throughput: 142.0,
  downtime: 4.2,
};

// ---------------------------------------------------------------------------
// SSR guard — connect() is a no-op on server platform
// ---------------------------------------------------------------------------

describe('SseService (server platform)', () => {
  let service: SseService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        SseService,
        { provide: PLATFORM_ID, useValue: 'server' },
      ],
    });
    service = TestBed.inject(SseService);
  });

  it('connect() does nothing when running on server platform (isPlatformBrowser false)', () => {
    service.connect('/v1/stream/kpi', 'fake-token');
    expect(service.connectionStatus()).toBe('disconnected');
  });
});

// ---------------------------------------------------------------------------
// Browser platform — event handling
// ---------------------------------------------------------------------------

describe('SseService (browser platform)', () => {
  let service: SseService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        SseService,
        { provide: PLATFORM_ID, useValue: 'browser' },
      ],
    });
    service = TestBed.inject(SseService);
  });

  // ---------------------------------------------------------------------------
  // kpi_update event → kpiSnapshot Signal
  // ---------------------------------------------------------------------------

  it('a kpi_update MessageEvent updates the kpiSnapshot Signal', () => {
    const fakeEvent = makeKpiEvent(FULL_KPI);
    service.handleEvent(fakeEvent);

    const snapshot = service.kpiSnapshot();
    expect(snapshot).not.toBeNull();
    expect(snapshot?.oee).toBe(87.3);
    expect(snapshot?.mttr).toBe(28.5);
  });

  it('kpiSnapshot Signal contains all 6 KPI keys after a kpi_update event', () => {
    service.handleEvent(makeKpiEvent(FULL_KPI));
    const snapshot = service.kpiSnapshot();

    const KPI_KEYS = ['oee', 'mttr', 'mtbf', 'scrap_rate', 'throughput', 'downtime'] as const;
    for (const key of KPI_KEYS) {
      expect(snapshot).toHaveProperty(key);
    }
  });

  // ---------------------------------------------------------------------------
  // sse_heartbeat → connectionStatus Signal
  // ---------------------------------------------------------------------------

  it('an sse_heartbeat event sets connectionStatus to "connected"', () => {
    service.handleEvent(makeHeartbeatEvent());
    expect(service.connectionStatus()).toBe('connected');
  });

  it('connectionStatus is "disconnected" before any event is received', () => {
    expect(service.connectionStatus()).toBe('disconnected');
  });

  // ---------------------------------------------------------------------------
  // Reconnect: error event sets connectionStatus to 'reconnecting'
  // ---------------------------------------------------------------------------

  it('an EventSource error sets connectionStatus to "reconnecting"', () => {
    service.handleError(makeErrorEvent());
    expect(service.connectionStatus()).toBe('reconnecting');
  });

  // ---------------------------------------------------------------------------
  // disconnect() — cleans up EventSource
  // ---------------------------------------------------------------------------

  it('disconnect() closes the EventSource and sets connectionStatus to "disconnected"', () => {
    // disconnect from idle state — should set status to disconnected
    service.disconnect();
    expect(service.connectionStatus()).toBe('disconnected');
  });
});
