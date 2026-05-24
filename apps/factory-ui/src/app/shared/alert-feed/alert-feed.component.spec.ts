/**
 * Contract tests for AlertFeedComponent.
 *
 * TDD RED/GREEN — plan 10-07 (Wave 6 frontend dashboard primitives).
 * Implements 10-UI-SPEC Component 9 + HITL-10 rate-limit contract.
 *
 * Requirements: UI-06, HITL-10.
 *
 * Acceptance criteria:
 *   - data-testid="alert-feed" on the root element
 *   - aria-live="polite" on the alert list region
 *   - Rate-limit banner (data-testid="rate-limit-banner") shown when
 *     rateLimitReached() is true (12+ alerts in sliding window)
 *   - Alert items render agent chip + message + timestamp
 *   - "Vai all'approvazione" button (64px touch) present when alert has pending action
 *   - T-10-07-02: text interpolation only — no [innerHTML]
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { By } from '@angular/platform-browser';
import { AlertFeedComponent } from './alert-feed.component';
import { AlertNewEvent } from '../../core/sse/sse.service';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeAlert(
  id: string,
  message = 'Alert di test',
  severity: 'info' | 'warning' | 'critical' = 'warning',
): AlertNewEvent {
  return { alert_id: id, message, severity };
}

function createFixture(
  alerts: AlertNewEvent[],
  rateLimitReached = false,
): ComponentFixture<AlertFeedComponent> {
  TestBed.configureTestingModule({
    imports: [NoopAnimationsModule, AlertFeedComponent],
  });
  const fixture = TestBed.createComponent(AlertFeedComponent);
  fixture.componentRef.setInput('alerts', alerts);
  fixture.componentRef.setInput('rateLimitReached', rateLimitReached);
  fixture.detectChanges();
  return fixture;
}

// ---------------------------------------------------------------------------
// data-testid
// ---------------------------------------------------------------------------

describe('AlertFeedComponent — data-testid', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('has data-testid="alert-feed" on root element', () => {
    const f = createFixture([]);
    const el = f.debugElement.query(By.css('[data-testid="alert-feed"]'));
    expect(el).toBeTruthy();
  });

  it('does NOT show rate-limit-banner when limit not reached', () => {
    const f = createFixture([makeAlert('1')], false);
    const banner = f.debugElement.query(By.css('[data-testid="rate-limit-banner"]'));
    expect(banner).toBeFalsy();
  });

  it('shows rate-limit-banner when rateLimitReached=true', () => {
    const f = createFixture([], true);
    const banner = f.debugElement.query(By.css('[data-testid="rate-limit-banner"]'));
    expect(banner).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// Rate-limit banner — HITL-10
// ---------------------------------------------------------------------------

describe('AlertFeedComponent — rate-limit banner (HITL-10)', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('banner contains HITL-10 copy about 12/hour limit', () => {
    const f = createFixture([], true);
    const banner = f.debugElement.query(By.css('[data-testid="rate-limit-banner"]'));
    expect(banner).toBeTruthy();
    const text = (banner.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('12');
  });

  it('banner is hidden when rateLimitReached=false', () => {
    const alerts = Array.from({ length: 11 }, (_, i) => makeAlert(String(i)));
    const f = createFixture(alerts, false);
    const banner = f.debugElement.query(By.css('[data-testid="rate-limit-banner"]'));
    expect(banner).toBeFalsy();
  });

  it('shows banner when 13 alerts are injected with rateLimitReached=true', () => {
    const alerts = Array.from({ length: 13 }, (_, i) => makeAlert(String(i)));
    const f = createFixture(alerts, true);
    const banner = f.debugElement.query(By.css('[data-testid="rate-limit-banner"]'));
    expect(banner).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// Alert items rendering
// ---------------------------------------------------------------------------

describe('AlertFeedComponent — alert items', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('renders all alert messages', () => {
    const alerts = [
      makeAlert('1', 'Anomalia rilevata'),
      makeAlert('2', 'Temperatura elevata'),
    ];
    const f = createFixture(alerts);
    const text = f.nativeElement.textContent as string;
    expect(text).toContain('Anomalia rilevata');
    expect(text).toContain('Temperatura elevata');
  });

  it('renders empty state copy when alerts is empty', () => {
    const f = createFixture([]);
    const text = f.nativeElement.textContent as string;
    // Empty state: some indication that there are no alerts
    expect(text.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// Accessibility
// ---------------------------------------------------------------------------

describe('AlertFeedComponent — accessibility', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('alert list region has aria-live="polite"', () => {
    const f = createFixture([makeAlert('1')]);
    const liveRegion = f.debugElement.query(By.css('[aria-live="polite"]'));
    expect(liveRegion).toBeTruthy();
  });
});
