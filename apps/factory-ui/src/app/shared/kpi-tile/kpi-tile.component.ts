import { Component, computed, input } from '@angular/core';
import { CommonModule } from '@angular/common';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type KpiKey = 'oee' | 'mttr' | 'mtbf' | 'scrap_rate' | 'throughput' | 'downtime';
export type KpiStatus = 'green' | 'warning' | 'destructive' | 'grey';

/**
 * KPI threshold definition.
 *
 * Direction controls whether higher is better (oee, mtbf, throughput)
 * or lower is better (mttr, scrap_rate, downtime).
 *
 * 10-UI-SPEC §5 threshold table.
 */
interface KpiThreshold {
  greenBound: number;
  redBound: number;
  direction: 'higher' | 'lower';
  label: string;
  unit: string;
  valueUnit: string;
}

/** Icon name per status (Material Symbols Outlined) */
const STATUS_ICON: Record<KpiStatus, string> = {
  green: 'check_circle',
  warning: 'warning',
  destructive: 'error',
  grey: 'help',
};

/** CSS class suffix per status */
const STATUS_CLASS: Record<KpiStatus, string> = {
  green: 'green',
  warning: 'warning',
  destructive: 'destructive',
  grey: 'grey',
};

/**
 * Static threshold table per KPI key.
 *
 * Throughput: greenBound=1.0, redBound=0.9 are ratios (value/baseline).
 *
 * 10-UI-SPEC §5:
 *   OEE:        >= 85 green, 80–84 warning, < 80  destructive
 *   MTTR:       <= 30 green, 30–60 warning, > 60  destructive
 *   MTBF:       >= 72 green, 48–72 warning, < 48  destructive
 *   Scrap Rate: <= 2  green, 2–5  warning, > 5   destructive
 *   Throughput: >= baseline green, 90–99% warning, < 90% destructive
 *   Downtime:   <= 5  green, 5–10 warning, > 10  destructive
 */
const KPI_META: Record<KpiKey, KpiThreshold> = {
  oee: {
    greenBound: 85,
    redBound: 80,
    direction: 'higher',
    label: 'OEE',
    unit: '%',
    valueUnit: '%',
  },
  mttr: {
    greenBound: 30,
    redBound: 60,
    direction: 'lower',
    label: 'MTTR',
    unit: 'min',
    valueUnit: 'min',
  },
  mtbf: {
    greenBound: 72,
    redBound: 48,
    direction: 'higher',
    label: 'MTBF',
    unit: 'h',
    valueUnit: 'h',
  },
  scrap_rate: {
    greenBound: 2,
    redBound: 5,
    direction: 'lower',
    label: 'Scarto',
    unit: '%',
    valueUnit: '%',
  },
  throughput: {
    greenBound: 1.0,
    redBound: 0.9,
    direction: 'higher',
    label: 'Produttività',
    unit: 'kg/h',
    valueUnit: 'kg/h',
  },
  downtime: {
    greenBound: 5,
    redBound: 10,
    direction: 'lower',
    label: 'Fermo',
    unit: '%',
    valueUnit: '%',
  },
};

// ---------------------------------------------------------------------------
// Pure threshold function (exported for unit testing)
// ---------------------------------------------------------------------------

/**
 * Computes KPI status from a raw numeric value and the KPI key.
 *
 * For 'throughput', `baseline` must be provided; the ratio value/baseline is
 * compared against greenBound (1.0) and redBound (0.9).
 *
 * Returns 'grey' when value is null/undefined.
 */
export function computeKpiStatus(
  key: KpiKey,
  value: number | null,
  baseline?: number,
): KpiStatus {
  if (value === null || value === undefined) return 'grey';

  const meta = KPI_META[key];
  let effectiveValue = value;

  if (key === 'throughput') {
    const base = baseline ?? value;
    effectiveValue = base === 0 ? 0 : value / base;
  }

  if (meta.direction === 'higher') {
    if (effectiveValue >= meta.greenBound) return 'green';
    if (effectiveValue >= meta.redBound) return 'warning';
    return 'destructive';
  } else {
    if (effectiveValue <= meta.greenBound) return 'green';
    if (effectiveValue <= meta.redBound) return 'warning';
    return 'destructive';
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * KpiTileComponent — single KPI tile with threshold-colored status bar.
 *
 * Requirements: UI-04, UI-06, 10-UI-SPEC Component 5.
 *   - min-height 80px (factory floor readability at a distance)
 *   - StatusBar 4px at top edge, colored by status
 *   - Icon + color for status (never color alone — WCAG accessibility)
 *   - data-testid="kpi-tile-<key>" for Playwright E2E
 *   - SSR-safe: no window/document access
 *   - T-10-07-02: text interpolation only — no [innerHTML]
 *
 * Uses Angular 17+ input() signal API so that computed() reacts immediately
 * to @Input changes without a manual ngOnChanges bridge.
 */
@Component({
  selector: 'sft-kpi-tile',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="sft-kpi-tile"
      [attr.data-testid]="'kpi-tile-' + key()"
      [attr.aria-label]="meta().label + ': ' + displayValue() + ' ' + meta().unit">

      <!-- Status bar — 4px at the top edge -->
      <div
        class="sft-kpi-tile__status-bar"
        [class]="'sft-kpi-tile__status-bar--' + statusClass()"
        aria-hidden="true">
      </div>

      <!-- Body -->
      <div class="sft-kpi-tile__body">

        <!-- Label row: icon + label -->
        <div class="sft-kpi-tile__label-row">
          <!-- Status icon (icon + color, never color alone — WCAG) -->
          <span
            class="sft-kpi-tile__icon material-symbols-outlined"
            [class]="'sft-kpi-tile__icon--' + statusClass()"
            [attr.aria-label]="statusAriaLabel()">
            {{ statusIcon() }}
          </span>
          <span class="sft-kpi-tile__label">{{ meta().label }}</span>
        </div>

        <!-- Value row -->
        <div class="sft-kpi-tile__value-row">
          <span class="sft-kpi-tile__value">{{ displayValue() }}</span>
          @if (value() !== null) {
            <span class="sft-kpi-tile__value-unit">{{ meta().valueUnit }}</span>
          }
        </div>

        <!-- Unit / description -->
        <div class="sft-kpi-tile__unit">{{ meta().unit }}</div>

        <!-- Delta (optional) -->
        @if (delta() !== null && delta() !== undefined) {
          <div
            class="sft-kpi-tile__delta"
            [class.sft-kpi-tile__delta--positive]="(delta() ?? 0) > 0"
            [class.sft-kpi-tile__delta--negative]="(delta() ?? 0) < 0">
            {{ (delta() ?? 0) > 0 ? '+' : '' }}{{ delta() }}%
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sft-kpi-tile {
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      min-height: 80px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-sizing: border-box;
    }

    .sft-kpi-tile:focus-within {
      outline: 2px solid var(--sft-accent, #3B82F6);
      outline-offset: 2px;
    }

    /* 4px status bar at the top edge */
    .sft-kpi-tile__status-bar {
      height: 4px;
      width: 100%;
      flex-shrink: 0;
      background-color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-kpi-tile__status-bar--green {
      background-color: var(--sft-success, #22C55E);
    }

    .sft-kpi-tile__status-bar--warning {
      background-color: var(--sft-warning, #F59E0B);
    }

    .sft-kpi-tile__status-bar--destructive {
      background-color: var(--sft-destructive, #EF4444);
    }

    .sft-kpi-tile__status-bar--grey {
      background-color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-kpi-tile__body {
      padding: var(--sft-space-4, 16px);
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-2, 8px);
      flex: 1;
    }

    .sft-kpi-tile__label-row {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .sft-kpi-tile__icon {
      font-size: 18px;
      line-height: 1;
      color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-kpi-tile__icon--green { color: var(--sft-success, #22C55E); }
    .sft-kpi-tile__icon--warning { color: var(--sft-warning, #F59E0B); }
    .sft-kpi-tile__icon--destructive { color: var(--sft-destructive, #EF4444); }
    .sft-kpi-tile__icon--grey { color: var(--sft-text-secondary, #9BA3B2); }

    .sft-kpi-tile__label {
      font-size: 14px;
      font-weight: 400;
      color: var(--sft-text-secondary, #9BA3B2);
      line-height: 1.4;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .sft-kpi-tile__value-row {
      display: flex;
      align-items: baseline;
      gap: 4px;
    }

    .sft-kpi-tile__value {
      font-size: 28px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      line-height: 1.2;
    }

    .sft-kpi-tile__value-unit {
      font-size: 14px;
      font-weight: 400;
      color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-kpi-tile__unit {
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
      line-height: 1.4;
    }

    .sft-kpi-tile__delta {
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-kpi-tile__delta--positive { color: var(--sft-success, #22C55E); }
    .sft-kpi-tile__delta--negative { color: var(--sft-destructive, #EF4444); }

    @media (prefers-reduced-motion: reduce) {
      .sft-kpi-tile { transition: none; }
    }
  `],
})
export class KpiTileComponent {
  /** KPI key — determines threshold logic, label, units */
  readonly key = input.required<KpiKey>();

  /** Raw KPI numeric value; null means "no data" → grey */
  readonly value = input<number | null>(null);

  /** Optional baseline for throughput ratio computation */
  readonly baseline = input<number | undefined>(undefined);

  /** Optional delta (percentage vs previous period) */
  readonly delta = input<number | null | undefined>(null);

  // ---------------------------------------------------------------------------
  // Computed signals
  // ---------------------------------------------------------------------------

  readonly meta = computed<KpiThreshold>(() => KPI_META[this.key()]);

  /** KPI status from thresholds */
  readonly status = computed<KpiStatus>(() =>
    computeKpiStatus(this.key(), this.value(), this.baseline()),
  );

  readonly statusClass = computed<string>(() => STATUS_CLASS[this.status()]);

  readonly statusIcon = computed<string>(() => STATUS_ICON[this.status()]);

  readonly statusAriaLabel = computed<string>(() => {
    switch (this.status()) {
      case 'green':       return 'In target';
      case 'warning':     return 'Attenzione — in zona warning';
      case 'destructive': return 'Critico — fuori target';
      case 'grey':        return 'Nessun dato';
    }
  });

  readonly displayValue = computed<string>(() => {
    const v = this.value();
    if (v === null || v === undefined) return '—';
    return Number.isInteger(v) ? String(v) : v.toFixed(1);
  });
}
