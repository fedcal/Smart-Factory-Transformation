import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, RouterLinkActive } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

/** Navigation item definition */
export interface NavItem {
  /** Display label (IT — UI-SPEC Copywriting Contract) */
  label: string;
  /** Material Symbols icon name */
  icon: string;
  /** Router path */
  route: string;
  /** ARIA label for icon-only condensed mode */
  ariaLabel: string;
}

/**
 * NavigationRail — left sidebar navigation.
 *
 * Desktop (≥1024px): 72px wide, icon + label + uppercase section label.
 * Tablet  (768–1023px): 56px wide, icon only (condensed).
 * Mobile  (<768px): hidden (BottomNav takes over).
 *
 * Touch targets: nav items ≥64px min-height (UI-02).
 * Active state: accent left indicator + accent icon color.
 * SSR-safe: no browser APIs in constructor.
 */
@Component({
  selector: 'sft-nav-rail',
  standalone: true,
  imports: [CommonModule, RouterModule, MatIconModule, MatTooltipModule],
  template: `
    <nav class="sft-nav-rail" aria-label="Navigazione principale">
      @for (item of navItems(); track item.route) {
        <a
          class="sft-nav-rail__item"
          [routerLink]="item.route"
          routerLinkActive="sft-nav-rail__item--active"
          [routerLinkActiveOptions]="{ exact: false }"
          [attr.aria-label]="item.ariaLabel"
          [matTooltip]="item.label"
          matTooltipPosition="right"
          [matTooltipShowDelay]="200">
          <mat-icon class="sft-nav-rail__icon" aria-hidden="true">{{ item.icon }}</mat-icon>
          <span class="sft-nav-rail__label sft-nav-label">{{ item.label }}</span>
        </a>
      }
    </nav>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sft-nav-rail {
      position: fixed;
      top: var(--sft-topbar-height, 64px);
      left: 0;
      bottom: 0;
      width: var(--sft-nav-rail-width, 72px);
      background-color: var(--sft-surface-card);
      border-right: 1px solid var(--sft-border);
      display: flex;
      flex-direction: column;
      padding-top: var(--sft-space-2);
      overflow-y: auto;
      overflow-x: hidden;
      z-index: 90;

      /* Tablet: condensed (icon only, 56px width) */
      @media (max-width: 1023px) and (min-width: 768px) {
        width: var(--sft-nav-rail-compact, 56px);
      }

      /* Mobile: hidden */
      @media (max-width: 767px) {
        display: none;
      }
    }

    .sft-nav-rail__item {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: var(--sft-touch-target, 64px);
      padding: var(--sft-space-2) var(--sft-space-1);
      text-decoration: none;
      color: var(--sft-text-secondary);
      cursor: pointer;
      border-left: 3px solid transparent;
      transition: background-color var(--sft-transition-default),
                  color var(--sft-transition-default),
                  border-color var(--sft-transition-default);
      position: relative;

      &:hover {
        background-color: color-mix(in srgb, var(--sft-surface-card) 100%, var(--sft-accent) 8%);
        color: var(--sft-text-primary);
      }

      &:focus-visible {
        outline: var(--sft-focus-ring);
        outline-offset: var(--sft-focus-ring-offset);
      }

      &:active {
        transform: scale(0.97);
      }

      @media (prefers-reduced-motion: reduce) {
        &:active {
          transform: none;
        }
      }
    }

    .sft-nav-rail__item--active {
      color: var(--sft-accent);
      border-left-color: var(--sft-accent);
      background-color: color-mix(in srgb, var(--sft-surface-card) 100%, var(--sft-accent) 12%);

      .sft-nav-rail__icon {
        color: var(--sft-accent);
      }
    }

    .sft-nav-rail__icon {
      font-family: 'Material Symbols Outlined';
      font-size: 24px;
      flex-shrink: 0;
    }

    .sft-nav-rail__label {
      font-size: var(--sft-type-label, 14px);
      color: inherit;
      text-align: center;
      letter-spacing: 0.06em;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: calc(var(--sft-nav-rail-width, 72px) - 8px);
      line-height: 1.2;

      /* Tablet: hide label, show only icon */
      @media (max-width: 1023px) and (min-width: 768px) {
        display: none;
      }
    }
  `],
})
export class NavRailComponent {
  readonly navItems = input<NavItem[]>([]);
}
