import {
  inject,
  Injectable,
  PLATFORM_ID,
  signal,
  computed,
  afterNextRender,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { DOCUMENT } from '@angular/common';

export type Theme = 'dark' | 'light';

const THEME_STORAGE_KEY = 'sft_theme';
const DEFAULT_THEME: Theme = 'dark';

/**
 * ThemeService — dark/light toggle with localStorage persistence.
 *
 * SSR guard: All localStorage and document access is behind isPlatformBrowser()
 * (T-10-05-01). SSR always renders with dark theme (factory floor default).
 *
 * Implementation:
 *   - Applies theme via `document.documentElement.setAttribute('data-theme', theme)`
 *   - Persists selection in localStorage key `sft_theme`
 *   - Defaults to dark on initial load (UI-05)
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly document = inject(DOCUMENT);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  /**
   * WR-07: _theme is initialised only from localStorage (no DOM access).
   * DOM application is deferred to afterNextRender() in the constructor so
   * that this.document is guaranteed to be fully initialised and the DOM is
   * ready. This avoids any risk of calling _applyToDomDirect() before the
   * DOCUMENT injection completes during field initialiser execution.
   */
  private readonly _theme = signal<Theme>(this._readStoredTheme());

  /** Current active theme. */
  readonly theme = computed<Theme>(() => this._theme());

  /** True when dark theme is active. */
  readonly isDark = computed<boolean>(() => this._theme() === 'dark');

  constructor() {
    // WR-07: apply the initial theme to the DOM after the next render cycle,
    // guaranteeing that DOCUMENT is available and the DOM is ready.
    // afterNextRender() is a no-op on SSR (server never calls the callback).
    afterNextRender(() => {
      this._applyToDomDirect(this._theme());
    });
  }

  /**
   * Sets the given theme, applies it to the document root,
   * and persists in localStorage (browser only).
   */
  setTheme(theme: Theme): void {
    this._theme.set(theme);
    this._applyToDom(theme);
    if (this.isBrowser) {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    }
  }

  /**
   * Toggles between dark and light themes.
   */
  toggle(): void {
    const next: Theme = this._theme() === 'dark' ? 'light' : 'dark';
    this.setTheme(next);
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  /**
   * WR-07: reads the stored theme from localStorage without touching the DOM.
   * DOM application is deferred to afterNextRender() in the constructor.
   * On SSR this returns DEFAULT_THEME without any storage or DOM access.
   */
  private _readStoredTheme(): Theme {
    if (!this.isBrowser) {
      return DEFAULT_THEME; // SSR always dark
    }
    const stored = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
    return stored === 'light' || stored === 'dark' ? stored : DEFAULT_THEME;
  }

  private _applyToDom(theme: Theme): void {
    if (!this.isBrowser) return;
    this._applyToDomDirect(theme);
  }

  private _applyToDomDirect(theme: Theme): void {
    this.document.documentElement.setAttribute('data-theme', theme);
  }
}
