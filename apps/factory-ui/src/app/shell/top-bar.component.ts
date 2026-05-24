import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

/**
 * TopBar — 64px fixed header bar.
 *
 * Hosts:
 *   - Logo + persona area title
 *   - Slots for LanguageToggle (10-05) / ThemeToggle (10-06) / SSE indicator / UserChip (10-06)
 *
 * SSR-safe: no browser-only APIs in constructor or class body.
 * Touch targets: icon-only buttons have min-height/min-width 64px via global CSS layer.
 */
@Component({
  selector: 'sft-top-bar',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatTooltipModule],
  template: `
    <header class="sft-topbar" role="banner">
      <!-- Logo + area title -->
      <div class="sft-topbar__brand">
        <span class="sft-topbar__logo" aria-label="Smart Factory">SF</span>
        @if (areaTitle()) {
          <span class="sft-topbar__area-title sft-type-heading" aria-live="polite">
            {{ areaTitle() }}
          </span>
        }
      </div>

      <!-- Right-side action slots -->
      <div class="sft-topbar__actions">
        <!-- SSE live indicator (stub — wired in 10-05 SSE service) -->
        <div
          class="sft-topbar__sse-indicator"
          data-testid="sse-indicator"
          role="status"
          [attr.aria-label]="sseConnected() ? 'In tempo reale' : 'Non connesso'"
          [class.sft-topbar__sse-indicator--live]="sseConnected()">
          <span class="sft-sse-dot" aria-hidden="true"></span>
          <span class="sft-topbar__sse-label sft-type-label">
            {{ sseConnected() ? 'In tempo reale' : 'Non connesso' }}
          </span>
        </div>

        <!-- LanguageToggle placeholder (sft-language-toggle authored in 10-05) -->
        <div data-testid="language-toggle" class="sft-topbar__lang-slot">
          <ng-content select="[slot=language-toggle]"></ng-content>
          <!-- Fallback stub until 10-05 provides real component -->
          <button
            mat-button
            class="sft-topbar__lang-stub"
            aria-label="Seleziona lingua"
            title="Language toggle — disponibile in 10-05">
            IT
          </button>
        </div>

        <!-- ThemeToggle placeholder (sft-theme-toggle authored in 10-06) -->
        <div data-testid="theme-toggle" class="sft-topbar__theme-slot">
          <ng-content select="[slot=theme-toggle]"></ng-content>
          <!-- Fallback stub until 10-06 provides real component -->
          <button
            mat-icon-button
            class="sft-topbar__theme-stub"
            aria-label="Cambia tema"
            [attr.title]="'Cambia tema — disponibile in 10-06'"
            (click)="themeToggleClicked.emit()">
            <mat-icon>dark_mode</mat-icon>
          </button>
        </div>

        <!-- UserChip placeholder (sft-user-chip authored in 10-06) -->
        <ng-content select="[slot=user-chip]"></ng-content>
        <!-- Fallback stub -->
        <div class="sft-topbar__user-stub" aria-label="Utente non autenticato">
          <span class="sft-topbar__avatar" aria-hidden="true">?</span>
        </div>
      </div>
    </header>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sft-topbar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: var(--sft-topbar-height, 64px);
      background-color: var(--sft-surface-card);
      border-bottom: 1px solid var(--sft-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 var(--sft-space-4);
      z-index: 100;
      gap: var(--sft-space-2);
    }

    .sft-topbar__brand {
      display: flex;
      align-items: center;
      gap: var(--sft-space-2);
    }

    .sft-topbar__logo {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background-color: var(--sft-accent);
      color: #ffffff;
      font-weight: 600;
      font-size: 14px;
      font-family: var(--sft-font-family);
      flex-shrink: 0;
    }

    .sft-topbar__area-title {
      color: var(--sft-text-primary);
      font-size: 20px;
      font-weight: 600;
    }

    .sft-topbar__actions {
      display: flex;
      align-items: center;
      gap: var(--sft-space-1);
    }

    .sft-topbar__sse-indicator {
      display: flex;
      align-items: center;
      gap: var(--sft-space-1);
      padding: var(--sft-space-1) var(--sft-space-2);
      border-radius: 4px;
    }

    .sft-sse-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--sft-text-secondary);
      flex-shrink: 0;
    }

    .sft-topbar__sse-indicator--live .sft-sse-dot {
      background-color: var(--sft-success);
      animation: sft-pulse 2s infinite;
    }

    @keyframes sft-pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-topbar__sse-indicator--live .sft-sse-dot {
        animation: none;
      }
    }

    .sft-topbar__sse-label {
      color: var(--sft-text-secondary);
      font-size: 14px;

      @media (max-width: 767px) {
        display: none;
      }
    }

    .sft-topbar__lang-slot,
    .sft-topbar__theme-slot {
      display: contents;
    }

    .sft-topbar__lang-stub {
      color: var(--sft-text-secondary);
      font-size: 14px;
      font-weight: 600;
      min-height: var(--sft-touch-target, 64px);
    }

    .sft-topbar__avatar {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background-color: var(--sft-surface-card);
      border: 1px solid var(--sft-border);
      color: var(--sft-text-secondary);
      font-size: 14px;
      font-weight: 600;
    }
  `],
})
export class TopBarComponent {
  /** Area title displayed next to the logo */
  readonly areaTitle = input<string>('');

  /** Whether SSE stream is connected */
  readonly sseConnected = input<boolean>(false);

  /** Emitted when theme-toggle stub is clicked (wired in 10-06) */
  readonly themeToggleClicked = output<void>();
}
