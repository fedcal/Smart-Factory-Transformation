import { Component, computed, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { ScrollingModule } from '@angular/cdk/scrolling';
import {
  ApprovalCardComponent,
  ApprovalCardData,
} from '../approval-card/approval-card.component';
import { ApprovalPendingEvent } from '../../core/sse/sse.service';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type QueueFilter = 'all' | 'mine' | 'expiring';
export type QueueSort = 'date-asc' | 'date-desc' | 'priority-asc' | 'priority-desc';

/** Height in px for each ApprovalCard row in the virtual scroll viewport */
const CARD_ITEM_HEIGHT_PX = 200;

/** Height of the CDK virtual scroll viewport */
const VIEWPORT_HEIGHT_PX = 600;

/**
 * Maps a raw ApprovalPendingEvent (from SseService) to the full ApprovalCardData
 * needed by ApprovalCardComponent. Missing fields are set to sensible defaults
 * since the SSE event carries only the minimal approval metadata.
 */
function pendingEventToCardData(event: ApprovalPendingEvent): ApprovalCardData {
  return {
    id: event.approval_id,
    status: 'pending',
    agent_name: event.agent,
    cluster: 'unknown',
    action_type: 'PENDING',
    escalation_tier: event.tier,
    action_summary: `Azione in attesa da ${event.agent} (${event.tier})`,
    sla_seconds: event.sla_seconds,
    sla_started_at: new Date().toISOString(),
    motivation: undefined,
    evidence_panel: null,
  };
}

/**
 * ApprovalQueueFeedComponent — virtual-scroll pending approvals queue.
 *
 * Requirements: HITL-04, UI-06, 10-UI-SPEC Component 8.
 *
 * - Header "Approvazioni Pendenti" + count badge
 * - FilterBar: Tutti / Solo miei / Per scadenza (64px touch targets)
 * - SortBy: Data ↑↓ / Priorità ↑↓
 * - CDK VirtualScroll viewport rendering ApprovalCard per item (T-10-07-03)
 * - EmptyState when no pending approvals
 * - SSR-safe: cdk-virtual-scroll-viewport is platform-browser-guarded by Angular
 */
@Component({
  selector: 'sft-approval-queue-feed',
  standalone: true,
  imports: [
    CommonModule,
    MatChipsModule,
    MatButtonModule,
    ScrollingModule,
    ApprovalCardComponent,
  ],
  template: `
    <div class="sft-queue" data-testid="approval-queue-feed" role="region" aria-label="Approvazioni pendenti">

      <!-- Header -->
      <div class="sft-queue__header">
        <h2 class="sft-queue__title sft-type-heading">
          Approvazioni Pendenti
          @if (pendingCount() > 0) {
            <span
              class="sft-queue__count-badge"
              [attr.aria-label]="pendingCount() + ' approvazioni in attesa'"
              aria-live="polite">
              {{ pendingCount() }}
            </span>
          }
        </h2>
      </div>

      <!-- FilterBar — 64px height (UI-02) -->
      <div class="sft-queue__filter-bar" role="toolbar" aria-label="Filtri e ordinamento">
        <!-- Filter chips -->
        <div class="sft-queue__filters" role="group" aria-label="Filtra per">
          <button
            mat-stroked-button
            type="button"
            class="sft-queue__filter-btn"
            [class.sft-queue__filter-btn--active]="activeFilter() === 'all'"
            (click)="setFilter('all')"
            [attr.aria-pressed]="activeFilter() === 'all'">
            Tutti
          </button>
          <button
            mat-stroked-button
            type="button"
            class="sft-queue__filter-btn"
            [class.sft-queue__filter-btn--active]="activeFilter() === 'mine'"
            (click)="setFilter('mine')"
            [attr.aria-pressed]="activeFilter() === 'mine'">
            Solo miei
          </button>
          <button
            mat-stroked-button
            type="button"
            class="sft-queue__filter-btn"
            [class.sft-queue__filter-btn--active]="activeFilter() === 'expiring'"
            (click)="setFilter('expiring')"
            [attr.aria-pressed]="activeFilter() === 'expiring'">
            Per scadenza
          </button>
        </div>

        <!-- Sort selector -->
        <div class="sft-queue__sort" role="group" aria-label="Ordina per">
          <button
            mat-stroked-button
            type="button"
            class="sft-queue__sort-btn"
            [class.sft-queue__sort-btn--active]="activeSort() === 'date-asc'"
            (click)="setSort('date-asc')"
            aria-label="Ordina per data crescente">
            Data ↑
          </button>
          <button
            mat-stroked-button
            type="button"
            class="sft-queue__sort-btn"
            [class.sft-queue__sort-btn--active]="activeSort() === 'date-desc'"
            (click)="setSort('date-desc')"
            aria-label="Ordina per data decrescente">
            Data ↓
          </button>
          <button
            mat-stroked-button
            type="button"
            class="sft-queue__sort-btn"
            [class.sft-queue__sort-btn--active]="activeSort() === 'priority-desc'"
            (click)="setSort('priority-desc')"
            aria-label="Ordina per priorità decrescente">
            Priorità ↑
          </button>
        </div>
      </div>

      <!-- CDK Virtual Scroll viewport (T-10-07-03: bounds rendered cards) -->
      @if (filteredCards().length > 0) {
        <cdk-virtual-scroll-viewport
          [itemSize]="itemHeightPx"
          class="sft-queue__viewport"
          [style.height.px]="viewportHeightPx">

          <sft-approval-card
            *cdkVirtualFor="let card of filteredCards(); trackBy: trackById"
            [card]="card"
            class="sft-queue__card-wrapper">
          </sft-approval-card>
        </cdk-virtual-scroll-viewport>
      } @else {
        <!-- Empty state -->
        <div class="sft-queue__empty" role="status" data-testid="approval-queue-empty">
          <span
            class="sft-queue__empty-icon material-symbols-outlined"
            aria-hidden="true">
            inbox
          </span>
          <h3 class="sft-type-heading">Nessuna approvazione pendente</h3>
          <p class="sft-type-body">
            Il sistema è in attesa di nuove proposte dall'AI. Le notifiche arriveranno in tempo reale.
          </p>
        </div>
      }
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sft-queue {
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      padding: var(--sft-space-4, 16px);
      box-sizing: border-box;
    }

    /* Header */
    .sft-queue__header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .sft-queue__title {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--sft-text-primary, #F0F2F5);
      font-size: 20px;
      font-weight: 600;
      margin: 0;
    }

    .sft-queue__count-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background-color: var(--sft-destructive, #EF4444);
      color: #fff;
      font-size: 12px;
      font-weight: 600;
      border-radius: 12px;
      padding: 2px 8px;
      min-width: 24px;
    }

    /* FilterBar — 64px min-height */
    .sft-queue__filter-bar {
      display: flex;
      align-items: center;
      gap: var(--sft-space-4, 16px);
      min-height: 64px;
      flex-wrap: wrap;
    }

    .sft-queue__filters,
    .sft-queue__sort {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .sft-queue__filter-btn,
    .sft-queue__sort-btn {
      min-height: 64px;
      min-width: 64px;
      font-size: 14px;

      &:focus-visible {
        outline: 2px solid var(--sft-accent, #3B82F6);
        outline-offset: 2px;
      }
    }

    .sft-queue__filter-btn--active,
    .sft-queue__sort-btn--active {
      background-color: color-mix(in srgb, var(--sft-accent, #3B82F6) 20%, transparent) !important;
      border-color: var(--sft-accent, #3B82F6) !important;
      color: var(--sft-accent, #3B82F6) !important;
    }

    /* CDK virtual scroll viewport */
    .sft-queue__viewport {
      width: 100%;
      overflow-y: auto;
      border-radius: 6px;
    }

    .sft-queue__card-wrapper {
      display: block;
      padding-bottom: var(--sft-space-2, 8px);
    }

    /* Empty state */
    .sft-queue__empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-8, 32px) var(--sft-space-4, 16px);
      text-align: center;
    }

    .sft-queue__empty-icon {
      font-size: 48px;
      color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-queue__empty h3 {
      color: var(--sft-text-primary, #F0F2F5);
      margin: 0;
    }

    .sft-queue__empty p {
      color: var(--sft-text-secondary, #9BA3B2);
      margin: 0;
      max-width: 360px;
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-queue__filter-btn,
      .sft-queue__sort-btn {
        transition: none;
      }
    }
  `],
})
export class ApprovalQueueFeedComponent {
  /** Pending approval events from SseService.approvals signal */
  readonly approvals = input<ApprovalPendingEvent[]>([]);

  /** CDK virtual scroll item height */
  readonly itemHeightPx = CARD_ITEM_HEIGHT_PX;

  /** CDK virtual scroll viewport height */
  readonly viewportHeightPx = VIEWPORT_HEIGHT_PX;

  // Filter/sort state signals
  private readonly _activeFilter = signal<QueueFilter>('all');
  private readonly _activeSort = signal<QueueSort>('date-desc');

  readonly activeFilter = computed(() => this._activeFilter());
  readonly activeSort = computed(() => this._activeSort());

  readonly pendingCount = computed(() => this.approvals().length);

  /**
   * Filtered + sorted cards derived from approvals input.
   * Filter 'mine' and 'expiring' require additional data not in the minimal
   * SSE event — for now 'mine' filters by nothing (all shown), 'expiring'
   * sorts by sla_seconds ascending.
   */
  readonly filteredCards = computed<ApprovalCardData[]>(() => {
    const raw = this.approvals().map(pendingEventToCardData);
    const filter = this._activeFilter();
    const sort = this._activeSort();

    // Apply filter
    let filtered = raw;
    if (filter === 'expiring') {
      // Sort by SLA seconds ascending (most urgent first) — used as filter+sort
      filtered = [...raw].sort((a, b) => a.sla_seconds - b.sla_seconds);
      return filtered;
    }
    // 'all' and 'mine' show all (mine requires auth context not available here)

    // Apply sort (immutable — spread before sort)
    const sorted = [...filtered];
    switch (sort) {
      case 'date-asc':
        sorted.sort(
          (a, b) =>
            new Date(a.sla_started_at).getTime() -
            new Date(b.sla_started_at).getTime(),
        );
        break;
      case 'date-desc':
        sorted.sort(
          (a, b) =>
            new Date(b.sla_started_at).getTime() -
            new Date(a.sla_started_at).getTime(),
        );
        break;
      case 'priority-desc':
        sorted.sort((a, b) => a.sla_seconds - b.sla_seconds);
        break;
      case 'priority-asc':
        sorted.sort((a, b) => b.sla_seconds - a.sla_seconds);
        break;
    }
    return sorted;
  });

  // ---------------------------------------------------------------------------
  // User interactions
  // ---------------------------------------------------------------------------

  setFilter(filter: QueueFilter): void {
    this._activeFilter.set(filter);
  }

  setSort(sort: QueueSort): void {
    this._activeSort.set(sort);
  }

  trackById(_index: number, card: ApprovalCardData): string {
    return card.id;
  }
}
