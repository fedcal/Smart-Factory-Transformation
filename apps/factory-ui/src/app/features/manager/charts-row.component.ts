import {
  Component,
  computed,
  input,
  inject,
  PLATFORM_ID,
  OnInit,
  signal,
} from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { BaseChartDirective } from 'ng2-charts';
import {
  Chart,
  LineController,
  BarController,
  LineElement,
  BarElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  ChartData,
  ChartOptions,
} from 'chart.js';
import { KpiSnapshot } from '../../core/sse/sse.service';

// ---------------------------------------------------------------------------
// Chart.js selective registration (tree-shake T-10-08-02)
// Only the controllers, elements and scales needed for line + bar charts.
// ---------------------------------------------------------------------------
Chart.register(
  LineController,
  BarController,
  LineElement,
  BarElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
);

// ---------------------------------------------------------------------------
// Types for chart data
// ---------------------------------------------------------------------------

export interface OeeTrendPoint {
  day: string;
  oee: number;
}

export interface DowntimePareto {
  cause: string;
  minutes: number;
}

// ---------------------------------------------------------------------------
// Default placeholder data (7-day trend + top-5 Pareto)
// Real data comes from GET /v1/kpi endpoint (10-02); SSE updates live values.
// ---------------------------------------------------------------------------

const TREND_DAYS = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'];

function makePlaceholderTrendData(): OeeTrendPoint[] {
  return TREND_DAYS.map((day) => ({ day, oee: 0 }));
}

const DOWNTIME_CAUSES = ['Guasto Meccanico', 'Mancanza Materiale', 'Setup', 'Manutenzione', 'Altro'];

function makePlaceholderParetoData(): DowntimePareto[] {
  return DOWNTIME_CAUSES.map((cause) => ({ cause, minutes: 0 }));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * ChartsRowComponent — lazy-loaded OEE trend + Downtime Pareto charts.
 *
 * Requirements: UI-04, 10-UI-SPEC Component 5 ChartsRow.
 *
 * - OEE Trend: line chart (7 giorni) via ng2-charts@8 BaseChartDirective
 * - Downtime Pareto: bar chart (top-5 cause) via ng2-charts@8 BaseChartDirective
 * - SSR guard: chart canvas rendered only in browser (isPlatformBrowser check)
 *   to prevent document.createElement('canvas') crash on server (T-10-08-02)
 * - Chart.js selective registration: only needed controllers/elements registered
 *   (LineController, BarController, LineElement, BarElement, etc.) — tree-shakes
 *   all unused Chart.js code
 * - data-testid="charts-row" on root for Playwright E2E
 * - WCAG AA: legend enabled; axes labeled; colors use SFT token values
 */
@Component({
  selector: 'sft-charts-row',
  standalone: true,
  imports: [CommonModule, BaseChartDirective],
  template: `
    <div class="sft-charts-row" data-testid="charts-row">

      <h2 class="sft-charts-row__heading">
        Analisi Storica
      </h2>

      @if (isBrowser) {
        <div class="sft-charts-row__grid">

          <!-- OEE Trend — line chart (7 giorni) -->
          <div class="sft-charts-row__card">
            <h3 class="sft-charts-row__card-title">
              <span class="material-symbols-outlined" aria-hidden="true">show_chart</span>
              Trend OEE (7 giorni)
            </h3>
            <div class="sft-charts-row__chart-wrapper">
              <canvas
                baseChart
                [type]="'line'"
                [data]="oeeChartData()"
                [options]="oeeChartOptions"
                aria-label="Grafico trend OEE degli ultimi 7 giorni">
              </canvas>
            </div>
          </div>

          <!-- Downtime Pareto — bar chart (top 5 cause) -->
          <div class="sft-charts-row__card">
            <h3 class="sft-charts-row__card-title">
              <span class="material-symbols-outlined" aria-hidden="true">bar_chart</span>
              Pareto Fermi (top 5 cause)
            </h3>
            <div class="sft-charts-row__chart-wrapper">
              <canvas
                baseChart
                [type]="'bar'"
                [data]="paretoChartData()"
                [options]="paretoChartOptions"
                aria-label="Grafico Pareto delle cause di fermo macchina">
              </canvas>
            </div>
          </div>

        </div>
      } @else {
        <!-- SSR placeholder — avoids document API crash on server -->
        <div class="sft-charts-row__ssr-placeholder" aria-hidden="true">
          <span class="material-symbols-outlined">bar_chart</span>
          <span>Grafici disponibili nel browser</span>
        </div>
      }

    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sft-charts-row {
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
    }

    .sft-charts-row__heading {
      font-size: 20px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      margin: 0;
    }

    .sft-charts-row__grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: var(--sft-space-4, 16px);
    }

    @media (max-width: 1023px) {
      .sft-charts-row__grid {
        grid-template-columns: 1fr;
      }
    }

    .sft-charts-row__card {
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      padding: var(--sft-space-4, 16px);
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
    }

    .sft-charts-row__card-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 16px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      margin: 0;
    }

    .sft-charts-row__card-title .material-symbols-outlined {
      font-size: 20px;
      color: var(--sft-accent, #3B82F6);
    }

    .sft-charts-row__chart-wrapper {
      position: relative;
      min-height: 200px;
    }

    .sft-charts-row__chart-wrapper canvas {
      max-height: 240px;
    }

    .sft-charts-row__ssr-placeholder {
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

    @media (prefers-reduced-motion: reduce) {
      .sft-charts-row__card {
        transition: none;
      }
    }
  `],
})
export class ChartsRowComponent implements OnInit {
  private readonly platformId = inject(PLATFORM_ID);

  /** SSR guard: charts rendered only in browser */
  isBrowser = false;

  /** OEE trend data — 7-day time series from GET /v1/kpi or SSE */
  readonly trendData = input<OeeTrendPoint[]>(makePlaceholderTrendData());

  /** Downtime Pareto data — top 5 causes */
  readonly paretoData = input<DowntimePareto[]>(makePlaceholderParetoData());

  /** Current KPI snapshot — used to overlay the most recent OEE value */
  readonly kpiSnapshot = input<KpiSnapshot | null>(null);

  ngOnInit(): void {
    // SSR guard: set flag only in browser (T-10-08-02)
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  // ---------------------------------------------------------------------------
  // OEE line chart
  // ---------------------------------------------------------------------------

  readonly oeeChartData = computed<ChartData<'line', number[], string>>(() => {
    const trend = this.trendData();
    return {
      labels: trend.map((p) => p.day),
      datasets: [
        {
          label: 'OEE (%)',
          data: trend.map((p) => p.oee),
          borderColor: '#3B82F6',
          backgroundColor: 'rgba(59,130,246,0.15)',
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
      ],
    };
  });

  readonly oeeChartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { color: '#9BA3B2', font: { size: 12 } } },
      tooltip: { enabled: true },
    },
    scales: {
      x: {
        ticks: { color: '#9BA3B2', font: { size: 12 } },
        grid: { color: '#363B47' },
      },
      y: {
        min: 0,
        max: 100,
        ticks: {
          color: '#9BA3B2',
          font: { size: 12 },
          callback: (value) => `${value}%`,
        },
        grid: { color: '#363B47' },
        title: {
          display: true,
          text: 'OEE %',
          color: '#9BA3B2',
          font: { size: 12 },
        },
      },
    },
  };

  // ---------------------------------------------------------------------------
  // Downtime Pareto bar chart
  // ---------------------------------------------------------------------------

  readonly paretoChartData = computed<ChartData<'bar', number[], string>>(() => {
    const pareto = this.paretoData();
    return {
      labels: pareto.map((p) => p.cause),
      datasets: [
        {
          label: 'Minuti di fermo',
          data: pareto.map((p) => p.minutes),
          backgroundColor: [
            '#EF4444',
            '#F59E0B',
            '#3B82F6',
            '#22C55E',
            '#9BA3B2',
          ],
          borderRadius: 4,
        },
      ],
    };
  });

  readonly paretoChartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: { display: false },
      tooltip: { enabled: true },
    },
    scales: {
      x: {
        ticks: { color: '#9BA3B2', font: { size: 12 } },
        grid: { color: '#363B47' },
        title: {
          display: true,
          text: 'Minuti',
          color: '#9BA3B2',
          font: { size: 12 },
        },
      },
      y: {
        ticks: { color: '#9BA3B2', font: { size: 11 } },
        grid: { color: '#363B47' },
      },
    },
  };
}
