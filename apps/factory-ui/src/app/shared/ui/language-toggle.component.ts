import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { LocaleService, SupportedLocale } from '../../core/i18n/locale.service';

/**
 * LanguageToggle — IT/EN runtime switch via LocaleService (transloco, no reload).
 *
 * Requirements: UI-07, 10-UI-SPEC Component 6.
 *   - 64px touch target (min-height)
 *   - data-testid="language-toggle"
 *   - Persists in localStorage via LocaleService
 *   - SSR-safe: no direct localStorage access
 */
@Component({
  selector: 'sft-language-toggle',
  standalone: true,
  imports: [CommonModule, MatButtonToggleModule],
  template: `
    <mat-button-toggle-group
      [value]="currentLocale()"
      (change)="onLocaleChange($event.value)"
      aria-label="Seleziona lingua"
      data-testid="language-toggle"
      class="sft-lang-toggle">
      <mat-button-toggle value="it" class="sft-lang-btn">IT</mat-button-toggle>
      <mat-button-toggle value="en" class="sft-lang-btn">EN</mat-button-toggle>
    </mat-button-toggle-group>
  `,
  styles: [`
    :host {
      display: inline-flex;
      align-items: center;
    }

    .sft-lang-toggle {
      height: 64px;
      border: 1px solid var(--sft-border);
      border-radius: 8px;
      overflow: hidden;
    }

    .sft-lang-btn {
      min-height: 64px;
      min-width: 48px;
      font-size: 14px;
      font-weight: 600;
      font-family: var(--sft-font-family, 'Inter', system-ui, sans-serif);
      letter-spacing: 0.04em;
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-lang-toggle,
      .sft-lang-btn {
        transition: none;
      }
    }
  `],
})
export class LanguageToggleComponent {
  private readonly localeService = inject(LocaleService);

  readonly currentLocale = computed<SupportedLocale>(() =>
    this.localeService.locale(),
  );

  onLocaleChange(locale: SupportedLocale): void {
    if (locale === 'it' || locale === 'en') {
      this.localeService.switchLang(locale);
    }
  }
}
