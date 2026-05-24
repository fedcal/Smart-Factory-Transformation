import {
  Component,
  OnInit,
  signal,
  computed,
  inject,
  PLATFORM_ID,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { filter, map } from 'rxjs/operators';

import { TopBarComponent } from './top-bar.component';
import { NavRailComponent, NavItem } from './nav-rail.component';
import { BottomNavComponent } from './bottom-nav.component';

/**
 * Route → area label mapping (UI-SPEC Copywriting Contract — IT primary).
 * Uppercase nav labels are reserved for nav items only (not reused elsewhere).
 */
const ROUTE_AREA_LABELS: Record<string, string> = {
  '/operator':   'AREA OPERATORE',
  '/technician': 'AREA TECNICA',
  '/manager':    'AREA MANAGER',
  '/admin':      'AMMINISTRAZIONE',
  '/demo':       'DEMO PERSONA',
};

/**
 * Navigation items — persona routes (UI-SPEC Route table + Copywriting Contract).
 * Icons: Material Symbols Outlined.
 */
const PERSONA_NAV_ITEMS: NavItem[] = [
  {
    label:     'AREA OPERATORE',
    icon:      'engineering',
    route:     '/operator',
    ariaLabel: 'Area Operatore — approvazioni e alert',
  },
  {
    label:     'AREA TECNICA',
    icon:      'construction',
    route:     '/technician',
    ariaLabel: 'Area Tecnica — manutenzione e RCA',
  },
  {
    label:     'AREA MANAGER',
    icon:      'dashboard',
    route:     '/manager',
    ariaLabel: 'Area Manager — KPI e dashboard di controllo',
  },
  {
    label:     'AMMINISTRAZIONE',
    icon:      'admin_panel_settings',
    route:     '/admin',
    ariaLabel: 'Amministrazione — utenti e audit log',
  },
  {
    label:     'DEMO PERSONA',
    icon:      'play_circle',
    route:     '/demo',
    ariaLabel: 'Demo Persona — walkthrough guidato',
  },
];

/**
 * AppShell — root layout component.
 *
 * Structure:
 *   TopBar (64px, fixed)
 *   NavigationRail (72px desktop / 56px tablet, fixed left)
 *   BottomNav (64px, mobile only, fixed bottom)
 *   <router-outlet> (main content, scrollable)
 *
 * Responsive behaviour (UI-SPEC):
 *   ≥1024px  → NavigationRail full (72px) + 2-column layout
 *   768–1023 → NavigationRail compact (56px, icon-only) + 1 column
 *   <768px   → BottomNav + 1 column full-width
 *
 * SSR-safe: no localStorage/EventSource/window in constructors.
 * Theme: dark by default at :root (CSS); toggle via [data-theme="light"] on <html>.
 * isPlatformBrowser guard used for any browser-only code.
 */
@Component({
  selector: 'sft-app-shell',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    TopBarComponent,
    NavRailComponent,
    BottomNavComponent,
  ],
  template: `
    <!-- TopBar: 64px fixed header -->
    <sft-top-bar
      [areaTitle]="currentAreaLabel()"
      [sseConnected]="sseConnected()"
      (themeToggleClicked)="onThemeToggle()">
    </sft-top-bar>

    <!-- NavigationRail: desktop/tablet left sidebar -->
    <sft-nav-rail [navItems]="navItems"></sft-nav-rail>

    <!-- Main content area — offset for TopBar + NavRail -->
    <main class="sft-shell-content" role="main" id="main-content">
      <router-outlet></router-outlet>
    </main>

    <!-- BottomNav: mobile only -->
    <sft-bottom-nav [navItems]="navItems"></sft-bottom-nav>

    <!-- Skip-to-content link for keyboard users -->
    <a href="#main-content" class="sft-skip-link">
      Salta al contenuto principale
    </a>
  `,
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
      background-color: var(--sft-surface);
    }

    /* Main content: offset for fixed TopBar + NavigationRail */
    .sft-shell-content {
      margin-top: var(--sft-topbar-height, 64px);
      margin-left: var(--sft-nav-rail-width, 72px);
      min-height: calc(100vh - var(--sft-topbar-height, 64px));
      padding: var(--sft-space-4);
      overflow-x: hidden;

      /* Tablet: narrower nav rail */
      @media (max-width: 1023px) and (min-width: 768px) {
        margin-left: var(--sft-nav-rail-compact, 56px);
      }

      /* Mobile: no left margin, add bottom padding for BottomNav */
      @media (max-width: 767px) {
        margin-left: 0;
        padding-bottom: calc(var(--sft-bottom-nav-height, 64px) + var(--sft-space-4));
      }
    }

    /* Skip link — visible on focus for keyboard navigation */
    .sft-skip-link {
      position: absolute;
      top: -100px;
      left: var(--sft-space-4);
      padding: var(--sft-space-2) var(--sft-space-4);
      background-color: var(--sft-accent);
      color: #ffffff;
      font-family: var(--sft-font-family);
      font-size: 14px;
      font-weight: 600;
      border-radius: 4px;
      z-index: 200;
      transition: top var(--sft-transition-default);
      text-decoration: none;

      &:focus {
        top: var(--sft-space-2);
      }
    }
  `],
})
export class AppShellComponent implements OnInit {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly router = inject(Router);

  /** Navigation items for all persona routes */
  readonly navItems: NavItem[] = PERSONA_NAV_ITEMS;

  /** Current area label derived from active route */
  readonly currentAreaLabel = signal<string>('Smart Factory');

  /**
   * SSE connection state.
   * Stub: always false until SseService (10-05) is wired.
   * SSR-safe: no EventSource in constructor.
   */
  readonly sseConnected = signal<boolean>(false);

  ngOnInit(): void {
    // Update area label on route changes (browser only — router events are browser-side)
    if (isPlatformBrowser(this.platformId)) {
      this.router.events.pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        map((event) => this.resolveAreaLabel(event.urlAfterRedirects)),
      ).subscribe((label) => {
        this.currentAreaLabel.set(label);
      });

      // Set initial area label from current URL
      this.currentAreaLabel.set(this.resolveAreaLabel(this.router.url));
    }
  }

  /**
   * Toggle theme between dark (default) and light.
   * SSR-safe: guarded by isPlatformBrowser.
   * Toggles [data-theme="light"] on <html> element.
   * Stub until ThemeService (10-06) provides full implementation.
   */
  onThemeToggle(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    const html = document.documentElement;
    const isLight = html.getAttribute('data-theme') === 'light';

    if (isLight) {
      html.removeAttribute('data-theme');
    } else {
      html.setAttribute('data-theme', 'light');
    }
  }

  private resolveAreaLabel(url: string): string {
    // Find matching route prefix
    const matchedRoute = Object.keys(ROUTE_AREA_LABELS).find((route) =>
      url === route || url.startsWith(route + '/'),
    );
    return matchedRoute ? ROUTE_AREA_LABELS[matchedRoute] : 'Smart Factory';
  }
}
