import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconButtonModule } from '@angular/material/button';
import { ThemeService } from '../../core/theme/theme.service';

/**
 * ThemeToggle — dark/light toggle icon button.
 *
 * Requirements: UI-05, 10-UI-SPEC Component 1.
 *   - 64px touch target (min-height + min-width)
 *   - data-testid="theme-toggle"
 *   - aria-label for screen readers
 *   - SSR-safe via ThemeService
 */
@Component({
  selector: 'sft-theme-toggle',
  standalone: true,
  imports: [CommonModule, MatIconButtonModule],
  template: `
    <button
      mat-icon-button
      type="button"
      data-testid="theme-toggle"
      [attr.aria-label]="isDark() ? 'Cambia tema a chiaro' : 'Cambia tema a scuro'"
      (click)="themeService.toggle()"
      class="sft-theme-toggle-btn">
      <span class="material-symbols-outlined" aria-hidden="true">
        {{ isDark() ? 'light_mode' : 'dark_mode' }}
      </span>
    </button>
  `,
  styles: [`
    :host {
      display: inline-flex;
      align-items: center;
    }

    .sft-theme-toggle-btn {
      min-height: 64px;
      min-width: 64px;
      display: inline-flex;
      align-items: center;
      justify-content: center;

      &:focus-visible {
        outline: 2px solid var(--sft-accent);
        outline-offset: 2px;
      }
    }

    .material-symbols-outlined {
      font-size: 24px;
      color: var(--sft-text-primary);
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-theme-toggle-btn {
        transition: none;
      }
    }
  `],
})
export class ThemeToggleComponent {
  readonly themeService = inject(ThemeService);

  readonly isDark = computed<boolean>(() => this.themeService.isDark());
}
