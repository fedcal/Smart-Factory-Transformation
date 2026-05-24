import {
  inject,
  Injectable,
  PLATFORM_ID,
  signal,
  computed,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { DOCUMENT } from '@angular/common';
import { TranslocoService } from '@jsverse/transloco';

export type SupportedLocale = 'it' | 'en';

const LOCALE_STORAGE_KEY = 'sft_locale';
const DEFAULT_LOCALE: SupportedLocale = 'it';

/**
 * LocaleService — wraps transloco for runtime IT/EN toggle.
 *
 * Requirements (UI-07, 10-CONTEXT post_research_resolution #1):
 *   - Switches locale WITHOUT page reload
 *   - Persists selection in localStorage key `sft_locale`
 *   - SSR default is always 'it' (no browser at server-render time)
 *   - Updates `document.documentElement.lang` on switch
 *
 * transloco handles lazy-loading of locale JSON files from assets/i18n/{lang}.json
 * via the HttpLoader configured in app.config.ts.
 */
@Injectable({ providedIn: 'root' })
export class LocaleService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly document = inject(DOCUMENT);
  private readonly transloco = inject(TranslocoService);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  private readonly _locale = signal<SupportedLocale>(this._loadInitialLocale());

  /** Currently active locale code. */
  readonly locale = computed<SupportedLocale>(() => this._locale());

  /** True when English is the active locale. */
  readonly isEnglish = computed<boolean>(() => this._locale() === 'en');

  /**
   * Switches the active locale at runtime (NO page reload).
   *
   * Steps:
   *  1. Load the translation file lazily via transloco
   *  2. Set transloco's active language
   *  3. Update document.documentElement.lang
   *  4. Persist in localStorage (browser only)
   */
  switchLang(locale: SupportedLocale): void {
    this._locale.set(locale);

    // Load + switch transloco (lazy-loads assets/i18n/{locale}.json if not cached)
    this.transloco.load(locale).subscribe(() => {
      this.transloco.setActiveLang(locale);
    });

    // Update <html lang="..."> attribute
    if (this.isBrowser) {
      this.document.documentElement.lang = locale;
      localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    }
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  private _loadInitialLocale(): SupportedLocale {
    if (!this.isBrowser) {
      return DEFAULT_LOCALE; // SSR: always Italian
    }
    const stored = localStorage.getItem(LOCALE_STORAGE_KEY) as SupportedLocale | null;
    return stored === 'it' || stored === 'en' ? stored : DEFAULT_LOCALE;
  }
}
