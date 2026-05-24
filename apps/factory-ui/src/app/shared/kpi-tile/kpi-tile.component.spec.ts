/**
 * Contract tests for KpiTileComponent.
 *
 * TDD RED/GREEN — plan 10-07 (Wave 6 frontend dashboard primitives).
 * Implements 10-UI-SPEC Component 5 + 10-00b scaffold acceptance contract.
 *
 * Requirements: UI-04, UI-06.
 *
 * Threshold table (10-UI-SPEC §5):
 *   OEE:        >= 85 green, 80–84 warning, < 80  destructive
 *   MTTR:       <= 30 green, 30–60 warning, > 60  destructive
 *   MTBF:       >= 72 green, 48–72 warning, < 48  destructive
 *   Scrap Rate: <= 2  green, 2–5  warning, > 5   destructive
 *   Throughput: >= baseline green, 90–99% warning, < 90% destructive
 *   Downtime:   <= 5  green, 5–10 warning, > 10  destructive
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { By } from '@angular/platform-browser';
import { KpiTileComponent, KpiKey, KpiStatus } from './kpi-tile.component';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createFixture(
  key: KpiKey,
  value: number | null,
  baseline?: number,
): ComponentFixture<KpiTileComponent> {
  TestBed.configureTestingModule({
    imports: [NoopAnimationsModule, KpiTileComponent],
  });
  const fixture = TestBed.createComponent(KpiTileComponent);
  fixture.componentRef.setInput('key', key);
  fixture.componentRef.setInput('value', value);
  if (baseline !== undefined) {
    fixture.componentRef.setInput('baseline', baseline);
  }
  fixture.detectChanges();
  return fixture;
}

// ---------------------------------------------------------------------------
// Threshold → status mapping
// ---------------------------------------------------------------------------

describe('KpiTileComponent — threshold → status', () => {
  afterEach(() => TestBed.resetTestingModule());

  // OEE
  it('OEE >= 85 → green', () => {
    const f = createFixture('oee', 87);
    expect(f.componentInstance.status()).toBe<KpiStatus>('green');
  });

  it('OEE 82 → warning', () => {
    const f = createFixture('oee', 82);
    expect(f.componentInstance.status()).toBe<KpiStatus>('warning');
  });

  it('OEE < 80 → destructive', () => {
    const f = createFixture('oee', 75);
    expect(f.componentInstance.status()).toBe<KpiStatus>('destructive');
  });

  // MTTR
  it('MTTR <= 30 → green', () => {
    const f = createFixture('mttr', 25);
    expect(f.componentInstance.status()).toBe<KpiStatus>('green');
  });

  it('MTTR 45 (30–60) → warning', () => {
    const f = createFixture('mttr', 45);
    expect(f.componentInstance.status()).toBe<KpiStatus>('warning');
  });

  it('MTTR > 60 → destructive', () => {
    const f = createFixture('mttr', 90);
    expect(f.componentInstance.status()).toBe<KpiStatus>('destructive');
  });

  // MTBF
  it('MTBF >= 72 → green', () => {
    const f = createFixture('mtbf', 80);
    expect(f.componentInstance.status()).toBe<KpiStatus>('green');
  });

  it('MTBF 60 (48–72) → warning', () => {
    const f = createFixture('mtbf', 60);
    expect(f.componentInstance.status()).toBe<KpiStatus>('warning');
  });

  it('MTBF < 48 → destructive', () => {
    const f = createFixture('mtbf', 30);
    expect(f.componentInstance.status()).toBe<KpiStatus>('destructive');
  });

  // Scrap Rate
  it('scrap_rate <= 2 → green', () => {
    const f = createFixture('scrap_rate', 1.5);
    expect(f.componentInstance.status()).toBe<KpiStatus>('green');
  });

  it('scrap_rate 3.5 (2–5) → warning', () => {
    const f = createFixture('scrap_rate', 3.5);
    expect(f.componentInstance.status()).toBe<KpiStatus>('warning');
  });

  it('scrap_rate > 5 → destructive', () => {
    const f = createFixture('scrap_rate', 7);
    expect(f.componentInstance.status()).toBe<KpiStatus>('destructive');
  });

  // Throughput (with baseline)
  it('throughput >= baseline → green', () => {
    const f = createFixture('throughput', 110, 100);
    expect(f.componentInstance.status()).toBe<KpiStatus>('green');
  });

  it('throughput 94% of baseline → warning', () => {
    const f = createFixture('throughput', 94, 100);
    expect(f.componentInstance.status()).toBe<KpiStatus>('warning');
  });

  it('throughput < 90% of baseline → destructive', () => {
    const f = createFixture('throughput', 85, 100);
    expect(f.componentInstance.status()).toBe<KpiStatus>('destructive');
  });

  // Downtime
  it('downtime <= 5 → green', () => {
    const f = createFixture('downtime', 3);
    expect(f.componentInstance.status()).toBe<KpiStatus>('green');
  });

  it('downtime 7 (5–10) → warning', () => {
    const f = createFixture('downtime', 7);
    expect(f.componentInstance.status()).toBe<KpiStatus>('warning');
  });

  it('downtime > 10 → destructive', () => {
    const f = createFixture('downtime', 15);
    expect(f.componentInstance.status()).toBe<KpiStatus>('destructive');
  });

  // Null value → grey (no data)
  it('null value → grey (no data)', () => {
    const f = createFixture('oee', null);
    expect(f.componentInstance.status()).toBe<KpiStatus>('grey');
  });
});

// ---------------------------------------------------------------------------
// data-testid
// ---------------------------------------------------------------------------

describe('KpiTileComponent — data-testid', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('has data-testid="kpi-tile-oee"', () => {
    const f = createFixture('oee', 87);
    const el = f.debugElement.query(By.css('[data-testid="kpi-tile-oee"]'));
    expect(el).toBeTruthy();
  });

  it('has data-testid="kpi-tile-mttr"', () => {
    const f = createFixture('mttr', 25);
    const el = f.debugElement.query(By.css('[data-testid="kpi-tile-mttr"]'));
    expect(el).toBeTruthy();
  });

  it('has data-testid="kpi-tile-mtbf"', () => {
    const f = createFixture('mtbf', 72);
    const el = f.debugElement.query(By.css('[data-testid="kpi-tile-mtbf"]'));
    expect(el).toBeTruthy();
  });

  it('has data-testid="kpi-tile-scrap_rate"', () => {
    const f = createFixture('scrap_rate', 2);
    const el = f.debugElement.query(By.css('[data-testid="kpi-tile-scrap_rate"]'));
    expect(el).toBeTruthy();
  });

  it('has data-testid="kpi-tile-throughput"', () => {
    const f = createFixture('throughput', 100, 100);
    const el = f.debugElement.query(By.css('[data-testid="kpi-tile-throughput"]'));
    expect(el).toBeTruthy();
  });

  it('has data-testid="kpi-tile-downtime"', () => {
    const f = createFixture('downtime', 5);
    const el = f.debugElement.query(By.css('[data-testid="kpi-tile-downtime"]'));
    expect(el).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// Icon + color (accessibility — never color alone)
// ---------------------------------------------------------------------------

describe('KpiTileComponent — icon conveying status', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('green status → check_circle icon present', () => {
    const f = createFixture('oee', 87);
    const text = f.nativeElement.textContent as string;
    expect(text).toContain('check_circle');
  });

  it('warning status → warning icon present', () => {
    const f = createFixture('oee', 82);
    const text = f.nativeElement.textContent as string;
    expect(text).toContain('warning');
  });

  it('destructive status → error icon present', () => {
    const f = createFixture('oee', 70);
    const text = f.nativeElement.textContent as string;
    expect(text).toContain('error');
  });
});

// ---------------------------------------------------------------------------
// StatusBar color class
// ---------------------------------------------------------------------------

describe('KpiTileComponent — status bar', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('renders status bar element', () => {
    const f = createFixture('oee', 87);
    const bar = f.debugElement.query(By.css('.sft-kpi-tile__status-bar'));
    expect(bar).toBeTruthy();
  });

  it('status bar has green class for green status', () => {
    const f = createFixture('oee', 87);
    const bar = f.debugElement.query(By.css('.sft-kpi-tile__status-bar'));
    expect(bar.nativeElement.classList).toContain('sft-kpi-tile__status-bar--green');
  });

  it('status bar has warning class for warning status', () => {
    const f = createFixture('oee', 82);
    const bar = f.debugElement.query(By.css('.sft-kpi-tile__status-bar'));
    expect(bar.nativeElement.classList).toContain('sft-kpi-tile__status-bar--warning');
  });

  it('status bar has destructive class for destructive status', () => {
    const f = createFixture('oee', 70);
    const bar = f.debugElement.query(By.css('.sft-kpi-tile__status-bar'));
    expect(bar.nativeElement.classList).toContain('sft-kpi-tile__status-bar--destructive');
  });
});

// ---------------------------------------------------------------------------
// Layout / accessibility
// ---------------------------------------------------------------------------

describe('KpiTileComponent — layout + accessibility', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('renders label', () => {
    const f = createFixture('oee', 87);
    const text = f.nativeElement.textContent as string;
    expect(text).toContain('OEE');
  });

  it('renders value', () => {
    const f = createFixture('oee', 87.3);
    const text = f.nativeElement.textContent as string;
    expect(text).toContain('87.3');
  });

  it('null value shows no-data copy', () => {
    const f = createFixture('oee', null);
    const text = f.nativeElement.textContent as string;
    expect(text).toContain('—');
  });
});
