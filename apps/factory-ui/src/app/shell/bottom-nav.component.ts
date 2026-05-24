import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { NavItem } from './nav-rail.component';

/**
 * BottomNav — mobile navigation bar.
 *
 * Visible only on <768px viewports (64px height).
 * Shows max 4 nav items (UI-SPEC AppShell).
 * Touch targets: min-height 64px, full-width tap area.
 * SSR-safe: no browser APIs.
 */
@Component({
  selector: 'sft-bottom-nav',
  standalone: true,
  imports: [CommonModule, RouterModule, MatIconModule],
  template: `
    <nav class="sft-bottom-nav" aria-label="Navigazione mobile">
      @for (item of displayItems(); track item.route) {
        <a
          class="sft-bottom-nav__item"
          [routerLink]="item.route"
          routerLinkActive="sft-bottom-nav__item--active"
          [routerLinkActiveOptions]="{ exact: false }"
          [attr.aria-label]="item.ariaLabel">
          <mat-icon class="sft-bottom-nav__icon" aria-hidden="true">{{ item.icon }}</mat-icon>
          <span class="sft-bottom-nav__label sft-type-label">{{ item.label }}</span>
        </a>
      }
    </nav>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sft-bottom-nav {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      height: var(--sft-bottom-nav-height, 64px);
      background-color: var(--sft-surface-card);
      border-top: 1px solid var(--sft-border);
      display: flex;
      align-items: stretch;
      z-index: 90;

      /* Only visible on mobile */
      @media (min-width: 768px) {
        display: none;
      }
    }

    .sft-bottom-nav__item {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: var(--sft-touch-target, 64px);
      text-decoration: none;
      color: var(--sft-text-secondary);
      cursor: pointer;
      gap: 2px;
      transition: background-color var(--sft-transition-default),
                  color var(--sft-transition-default);

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

    .sft-bottom-nav__item--active {
      color: var(--sft-accent);

      .sft-bottom-nav__icon {
        color: var(--sft-accent);
      }
    }

    .sft-bottom-nav__icon {
      font-family: 'Material Symbols Outlined';
      font-size: 24px;
    }

    .sft-bottom-nav__label {
      font-size: var(--sft-type-label, 14px);
      color: inherit;
      text-align: center;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 100%;
      line-height: 1.2;
    }
  `],
  host: {
    'role': 'navigation',
  },
})
export class BottomNavComponent {
  readonly navItems = input<NavItem[]>([]);

  /** Max 4 items for mobile BottomNav (UI-SPEC constraint) */
  get displayItems(): () => NavItem[] {
    return () => this.navItems().slice(0, 4);
  }
}
