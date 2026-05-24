import { Component, computed, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { AlertNewEvent } from '../../core/sse/sse.service';
import { TranslocoModule } from '@jsverse/transloco';

/** Maximum number of alerts displayable per HITL-10 (12/hour) */
const RATE_LIMIT = 12;

/**
 * AlertFeedComponent — live SSE alert feed with HITL-10 rate-limit banner.
 *
 * Requirements: UI-06, HITL-10, 10-UI-SPEC Component 9.
 *
 * - data-testid="alert-feed" on root for Playwright E2E
 * - aria-live="polite" on the alert list region (screen reader announcements)
 * - Rate-limit banner (data-testid="rate-limit-banner") when rateLimitReached
 * - Alert items: AgentChip + message + timestamp + optional "Vai all'approvazione" button
 * - Touch target >= 64px for the action button (UI-02 factory floor)
 * - SSR-safe: no window/document access
 * - T-10-07-01 (DoS): capped feed mirrors HITL-10 12/hr limit
 * - T-10-07-02 (XSS): Angular text interpolation only — no [innerHTML]
 */
@Component({
  selector: 'sft-alert-feed',
  standalone: true,
  imports: [CommonModule, MatChipsModule, MatButtonModule, TranslocoModule],
  template: `
    <div class="sft-alert-feed" data-testid="alert-feed" role="region" aria-label="Feed alert">

      <!-- Rate-limit banner — HITL-10 -->
      @if (rateLimitReached()) {
        <div
          class="sft-alert-feed__rate-limit-banner"
          data-testid="rate-limit-banner"
          role="alert"
          aria-live="assertive">
          <span class="sft-alert-feed__banner-icon material-symbols-outlined" aria-hidden="true">
            block
          </span>
          <span>
            Limite di {{ rateLimit }} alert/ora raggiunto. Nuovi alert sospesi temporaneamente.
          </span>
        </div>
      }

      <!-- Alert list — aria-live polite for screen reader announcements -->
      <div
        class="sft-alert-feed__list"
        aria-live="polite"
        aria-relevant="additions"
        aria-label="Lista alert">

        @if (visibleAlerts().length === 0) {
          <!-- Empty state -->
          <div class="sft-alert-feed__empty">
            <span class="sft-type-body" style="color: var(--sft-text-secondary)">
              {{ 'empty_state.alert_feed' | transloco }}
            </span>
          </div>
        } @else {
          @for (alert of visibleAlerts(); track alert.alert_id) {
            <div
              class="sft-alert-feed__item"
              [class]="'sft-alert-feed__item--' + alert.severity"
              role="listitem">

              <!-- Agent chip + severity icon -->
              <div class="sft-alert-feed__item-header">
                <span
                  class="sft-alert-feed__severity-icon material-symbols-outlined"
                  [attr.aria-label]="severityLabel(alert.severity)">
                  {{ severityIcon(alert.severity) }}
                </span>

                <!-- AgentChip: severity label -->
                <mat-chip class="sft-chip sft-chip--severity" [class]="'sft-chip--' + alert.severity">
                  {{ severityLabel(alert.severity) }}
                </mat-chip>
              </div>

              <!-- Alert message (text interpolation — no innerHTML, T-10-07-02) -->
              <p class="sft-alert-feed__message sft-type-body">
                {{ alert.message }}
              </p>

              <!-- "Vai all'approvazione" button — 64px touch target -->
              @if (alert.severity === 'critical' || alert.severity === 'warning') {
                <button
                  mat-stroked-button
                  type="button"
                  class="sft-alert-feed__action-btn"
                  [attr.aria-label]="'Vai alla approvazione per: ' + alert.message">
                  <span class="material-symbols-outlined" aria-hidden="true">open_in_new</span>
                  {{ 'alert.action_button' | transloco }}
                </button>
              }
            </div>
          }
        }
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sft-alert-feed {
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-2, 8px);
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      padding: var(--sft-space-4, 16px);
      box-sizing: border-box;
    }

    /* Rate-limit banner (HITL-10) */
    .sft-alert-feed__rate-limit-banner {
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

    .sft-alert-feed__banner-icon {
      font-size: 20px;
      flex-shrink: 0;
    }

    /* Alert list */
    .sft-alert-feed__list {
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-2, 8px);
    }

    .sft-alert-feed__empty {
      padding: var(--sft-space-4, 16px) 0;
      text-align: center;
    }

    /* Individual alert item */
    .sft-alert-feed__item {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: var(--sft-space-2, 8px) var(--sft-space-4, 16px);
      border-radius: 6px;
      border-left: 3px solid var(--sft-text-secondary, #9BA3B2);
      background-color: var(--sft-surface, #121418);
    }

    .sft-alert-feed__item--info {
      border-left-color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-alert-feed__item--warning {
      border-left-color: var(--sft-warning, #F59E0B);
    }

    .sft-alert-feed__item--critical {
      border-left-color: var(--sft-destructive, #EF4444);
    }

    .sft-alert-feed__item-header {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .sft-alert-feed__severity-icon {
      font-size: 18px;
      color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-chip {
      font-size: var(--sft-type-label, 14px);
      height: 28px;
    }

    .sft-chip--info {
      background-color: color-mix(in srgb, var(--sft-text-secondary, #9BA3B2) 20%, transparent) !important;
      color: var(--sft-text-secondary, #9BA3B2) !important;
    }

    .sft-chip--warning {
      background-color: color-mix(in srgb, var(--sft-warning, #F59E0B) 20%, transparent) !important;
      color: var(--sft-warning, #F59E0B) !important;
    }

    .sft-chip--critical {
      background-color: color-mix(in srgb, var(--sft-destructive, #EF4444) 20%, transparent) !important;
      color: var(--sft-destructive, #EF4444) !important;
    }

    .sft-alert-feed__message {
      color: var(--sft-text-primary, #F0F2F5);
      font-size: 16px;
      line-height: 1.5;
      margin: 0;
    }

    /* Action button — 64px touch target (UI-02) */
    .sft-alert-feed__action-btn {
      align-self: flex-start;
      min-height: 64px;
      min-width: 64px;
      font-size: 14px;
      display: inline-flex;
      align-items: center;
      gap: 6px;

      &:focus-visible {
        outline: 2px solid var(--sft-accent, #3B82F6);
        outline-offset: 2px;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-alert-feed__item,
      .sft-alert-feed__action-btn {
        transition: none;
      }
    }
  `],
})
export class AlertFeedComponent {
  /** Alert events from SseService.alerts signal */
  readonly alerts = input<AlertNewEvent[]>([]);

  /**
   * Whether the 12/hr HITL-10 rate limit has been reached.
   * Driven by the parent (SseService rate_limit event or count >= 12).
   */
  readonly rateLimitReached = input<boolean>(false);

  /** Constant exposed to template */
  readonly rateLimit = RATE_LIMIT;

  /**
   * Visible alerts — capped at RATE_LIMIT to prevent runaway rendering.
   * T-10-07-01 (DoS mitigation): renders only the most recent 12 alerts.
   */
  readonly visibleAlerts = computed<AlertNewEvent[]>(() => {
    const all = this.alerts();
    // Show newest-first up to the rate limit
    return all.slice(-RATE_LIMIT).reverse();
  });

  // ---------------------------------------------------------------------------
  // Pure helpers (no DOM access — SSR-safe)
  // ---------------------------------------------------------------------------

  severityIcon(severity: 'info' | 'warning' | 'critical'): string {
    switch (severity) {
      case 'info':     return 'info';
      case 'warning':  return 'warning';
      case 'critical': return 'error';
    }
  }

  severityLabel(severity: 'info' | 'warning' | 'critical'): string {
    switch (severity) {
      case 'info':     return 'Info';
      case 'warning':  return 'Avviso';
      case 'critical': return 'Critico';
    }
  }
}
