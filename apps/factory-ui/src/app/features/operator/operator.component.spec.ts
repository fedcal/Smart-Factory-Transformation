/**
 * Contract tests for OperatorComponent.
 *
 * Plan 10-08 — operator area (approval-queue focal + alert feed + KPI summary).
 *
 * Requirements: HITL-01, HITL-04, UI-01, UI-06, 10-UI-SPEC Component 1.
 *
 * Acceptance criteria:
 *   - data-testid="operator-area" on root
 *   - sft-approval-queue-feed rendered (primary focal)
 *   - sft-alert-feed rendered (secondary)
 *   - 3 KPI tiles rendered (oee, scrap_rate, downtime)
 *   - SSR-safe: no browser API in constructor
 *   - Disconnection banner shown when sseService.disconnectedTooLong() is true
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { By } from '@angular/platform-browser';
import { signal } from '@angular/core';
import { PLATFORM_ID } from '@angular/core';
import { TranslocoTestingModule } from '@jsverse/transloco';
import { OperatorComponent } from './operator.component';
import {
  SseService,
  KpiSnapshot,
  ApprovalPendingEvent,
  AlertNewEvent,
} from '../../core/sse/sse.service';
import { JwtService } from '../../core/auth/jwt.service';

const translocoTesting = TranslocoTestingModule.forRoot({
  langs: {
    it: {
      error_state: { sse_connection: 'Connessione interrotta. Riconnessione in corso...' },
      empty_state: {
        approvals_heading: 'Nessuna approvazione pendente',
        approvals_body: "Il sistema è in attesa di nuove proposte dall'AI.",
        alert_feed: 'Nessun alert nelle ultime 24 ore.',
      },
      banners: { rate_limit: 'Limite di 12 alert/ora raggiunto.' },
      alert: { action_button: "Vai all'approvazione" },
      queue: { filter_all: 'Tutti', filter_mine: 'Solo miei', filter_expiring: 'Per scadenza', sort_date_asc: 'Data ↑', sort_date_desc: 'Data ↓', sort_priority_desc: 'Priorità ↑', cancel: 'Annulla' },
      approval: { queue_heading: 'Approvazioni Pendenti' },
      kpi: { oee: 'OEE', mttr: 'MTTR', scrap_rate: 'Scarto', downtime: 'Fermo' },
    },
  },
  translocoConfig: { defaultLang: 'it', availableLangs: ['it'] },
  preloadLangs: true,
});

// ---------------------------------------------------------------------------
// Fake SseService
// ---------------------------------------------------------------------------

function makeFakeSseService() {
  return {
    kpiSnapshot: signal<KpiSnapshot | null>(null),
    approvals: signal<ApprovalPendingEvent[]>([]),
    alerts: signal<AlertNewEvent[]>([]),
    disconnectedTooLong: signal<boolean>(false),
    connectionStatus: signal<'connected' | 'disconnected' | 'reconnecting'>('disconnected'),
    connect: jest.fn(),
    disconnect: jest.fn(),
  };
}

function makeFakeJwtService() {
  return {
    getToken: jest.fn().mockReturnValue('fake-token'),
  };
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('OperatorComponent', () => {
  let fixture: ComponentFixture<OperatorComponent>;
  let component: OperatorComponent;
  let fakeSse: ReturnType<typeof makeFakeSseService>;
  let fakeJwt: ReturnType<typeof makeFakeJwtService>;

  beforeEach(async () => {
    fakeSse = makeFakeSseService();
    fakeJwt = makeFakeJwtService();

    await TestBed.configureTestingModule({
      imports: [OperatorComponent, NoopAnimationsModule, translocoTesting],
      providers: [
        { provide: PLATFORM_ID, useValue: 'browser' },
        { provide: SseService, useValue: fakeSse },
        { provide: JwtService, useValue: fakeJwt },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(OperatorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('renders data-testid="operator-area" on the root element', () => {
    const el = fixture.debugElement.query(By.css('[data-testid="operator-area"]'));
    expect(el).toBeTruthy();
  });

  it('renders the approval queue feed (primary focal)', () => {
    const el = fixture.debugElement.query(By.css('sft-approval-queue-feed'));
    expect(el).toBeTruthy();
  });

  it('renders the alert feed (secondary)', () => {
    const el = fixture.debugElement.query(By.css('sft-alert-feed'));
    expect(el).toBeTruthy();
  });

  it('renders 3 compact KPI tiles (oee, scrap_rate, downtime)', () => {
    const tiles = fixture.debugElement.queryAll(By.css('sft-kpi-tile'));
    expect(tiles.length).toBe(3);
  });

  it('does NOT show the disconnection banner when connected', () => {
    fakeSse.disconnectedTooLong.set(false);
    fixture.detectChanges();
    const banner = fixture.debugElement.query(By.css('.sft-operator__sse-banner'));
    expect(banner).toBeFalsy();
  });

  it('shows the disconnection banner when disconnectedTooLong is true', () => {
    fakeSse.disconnectedTooLong.set(true);
    fixture.detectChanges();
    const banner = fixture.debugElement.query(By.css('.sft-operator__sse-banner'));
    expect(banner).toBeTruthy();
  });

  it('calls sseService.connect on init in browser platform', () => {
    expect(fakeSse.connect).toHaveBeenCalledWith('/v1/stream/kpi', 'fake-token');
  });

  it('kpiValue returns null when kpiSnapshot is null', () => {
    fakeSse.kpiSnapshot.set(null);
    expect(component.kpiValue('oee')).toBeNull();
  });

  it('kpiValue returns numeric value from snapshot', () => {
    fakeSse.kpiSnapshot.set({
      oee: 87.5,
      mttr: 25,
      mtbf: 80,
      scrap_rate: 1.5,
      throughput: 120,
      downtime: 3,
    });
    fixture.detectChanges();
    expect(component.kpiValue('oee')).toBe(87.5);
    expect(component.kpiValue('scrap_rate')).toBe(1.5);
    expect(component.kpiValue('downtime')).toBe(3);
  });
});
