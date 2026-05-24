/**
 * Contract tests for ManagerComponent (Sala Controllo).
 *
 * Plan 10-08 — manager control room (6-KPI grid + widgets + lazy charts).
 *
 * Requirements: UI-04, UI-06, HITL-01, HITL-04, 10-UI-SPEC Component 5.
 *
 * Acceptance criteria:
 *   - data-testid="manager-area" on root
 *   - data-testid="kpi-grid" present (Playwright E2E contract)
 *   - 6 KPI tiles rendered (oee, mttr, mtbf, scrap_rate, throughput, downtime)
 *   - data-testid="sse-indicator" present in header
 *   - SSR-safe: no browser API in constructor
 *   - sseService.connect called on init in browser platform
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { By } from '@angular/platform-browser';
import { signal } from '@angular/core';
import { PLATFORM_ID } from '@angular/core';
import { ManagerComponent } from './manager.component';
import {
  SseService,
  KpiSnapshot,
  ApprovalPendingEvent,
  AlertNewEvent,
} from '../../core/sse/sse.service';
import { JwtService } from '../../core/auth/jwt.service';

// ---------------------------------------------------------------------------
// Fake services
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
    getToken: jest.fn().mockReturnValue('fake-manager-token'),
  };
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('ManagerComponent', () => {
  let fixture: ComponentFixture<ManagerComponent>;
  let component: ManagerComponent;
  let fakeSse: ReturnType<typeof makeFakeSseService>;
  let fakeJwt: ReturnType<typeof makeFakeJwtService>;

  beforeEach(async () => {
    fakeSse = makeFakeSseService();
    fakeJwt = makeFakeJwtService();

    await TestBed.configureTestingModule({
      imports: [ManagerComponent, NoopAnimationsModule],
      providers: [
        { provide: PLATFORM_ID, useValue: 'browser' },
        { provide: SseService, useValue: fakeSse },
        { provide: JwtService, useValue: fakeJwt },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ManagerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('renders data-testid="manager-area" on the root element', () => {
    const el = fixture.debugElement.query(By.css('[data-testid="manager-area"]'));
    expect(el).toBeTruthy();
  });

  it('renders data-testid="kpi-grid" (Playwright E2E contract)', () => {
    const el = fixture.debugElement.query(By.css('[data-testid="kpi-grid"]'));
    expect(el).toBeTruthy();
  });

  it('renders 6 KPI tiles', () => {
    const tiles = fixture.debugElement.queryAll(By.css('sft-kpi-tile'));
    expect(tiles.length).toBe(6);
  });

  it('renders data-testid="sse-indicator" in the header', () => {
    const el = fixture.debugElement.query(By.css('[data-testid="sse-indicator"]'));
    expect(el).toBeTruthy();
  });

  it('renders the approval queue feed widget', () => {
    const el = fixture.debugElement.query(By.css('sft-approval-queue-feed'));
    expect(el).toBeTruthy();
  });

  it('renders the alert feed widget', () => {
    const el = fixture.debugElement.query(By.css('sft-alert-feed'));
    expect(el).toBeTruthy();
  });

  it('does NOT show the SSE disconnection banner when connected', () => {
    fakeSse.disconnectedTooLong.set(false);
    fixture.detectChanges();
    const banner = fixture.debugElement.query(By.css('.sft-manager__sse-banner'));
    expect(banner).toBeFalsy();
  });

  it('shows the SSE disconnection banner when disconnectedTooLong is true', () => {
    fakeSse.disconnectedTooLong.set(true);
    fixture.detectChanges();
    const banner = fixture.debugElement.query(By.css('.sft-manager__sse-banner'));
    expect(banner).toBeTruthy();
  });

  it('calls sseService.connect on init in browser platform', () => {
    expect(fakeSse.connect).toHaveBeenCalledWith('/v1/stream/events', 'fake-manager-token');
  });

  it('kpiValue returns null when kpiSnapshot is null', () => {
    fakeSse.kpiSnapshot.set(null);
    expect(component.kpiValue('oee')).toBeNull();
  });

  it('kpiValue returns values from snapshot for all 6 KPIs', () => {
    const snap: KpiSnapshot = {
      oee: 87.5,
      mttr: 25,
      mtbf: 80,
      scrap_rate: 1.5,
      throughput: 120,
      downtime: 3,
    };
    fakeSse.kpiSnapshot.set(snap);
    fixture.detectChanges();

    expect(component.kpiValue('oee')).toBe(87.5);
    expect(component.kpiValue('mttr')).toBe(25);
    expect(component.kpiValue('mtbf')).toBe(80);
    expect(component.kpiValue('scrap_rate')).toBe(1.5);
    expect(component.kpiValue('throughput')).toBe(120);
    expect(component.kpiValue('downtime')).toBe(3);
  });

  it('isConnected returns false when connectionStatus is disconnected', () => {
    fakeSse.connectionStatus.set('disconnected');
    expect(component.isConnected()).toBeFalsy();
  });

  it('isConnected returns true when connectionStatus is connected', () => {
    fakeSse.connectionStatus.set('connected');
    expect(component.isConnected()).toBeTruthy();
  });
});
