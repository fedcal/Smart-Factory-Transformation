import {
  inject,
  Injectable,
  PLATFORM_ID,
  signal,
  computed,
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

  private readonly _theme = signal<Theme>(this._loadInitialTheme());

  /** Current active theme. */
  readonly theme = computed<Theme>(() => this._theme());

  /** True when dark theme is active. */
  readonly isDark = computed<boolean>(() => this._theme() === 'dark');

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

  private _loadInitialTheme(): Theme {
    if (!this.isBrowser) {
      return DEFAULT_THEME; // SSR always dark
    }
    const stored = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
    const theme = stored === 'light' || stored === 'dark' ? stored : DEFAULT_THEME;
    // Apply immediately on load (before first render)
    this._applyToDomDirect(theme);
    return theme;
  }

  private _applyToDom(theme: Theme): void {
    if (!this.isBrowser) return;
    this._applyToDomDirect(theme);
  }

  private _applyToDomDirect(theme: Theme): void {
    this.document.documentElement.setAttribute('data-theme', theme);
  }
}
