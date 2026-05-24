import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { JwtService } from '../../core/auth/jwt.service';

/**
 * UserChip — displays current user initials + role badge in the TopBar.
 *
 * Requirements: UI-02, 10-UI-SPEC Component 1.
 *   - 64px touch target
 *   - data-testid="user-chip"
 *   - Shows initials derived from JWT email claim
 *   - Shows role badge
 *   - SSR-safe: JwtService handles SSR guard
 */
@Component({
  selector: 'sft-user-chip',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="sft-user-chip"
      data-testid="user-chip"
      role="status"
      [attr.aria-label]="ariaLabel()">
      <div class="sft-user-chip__avatar" aria-hidden="true">
        {{ initials() }}
      </div>
      @if (role()) {
        <span class="sft-user-chip__role sft-type-label">
          {{ role() }}
        </span>
      }
    </div>
  `,
  styles: [`
    :host {
      display: inline-flex;
      align-items: center;
    }

    .sft-user-chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 64px;
      min-width: 64px;
      padding: 0 12px;
      cursor: default;
    }

    .sft-user-chip__avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background-color: var(--sft-border, #363B47);
      color: var(--sft-text-primary, #F0F2F5);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 14px;
      font-family: var(--sft-font-family, 'Inter', system-ui, sans-serif);
      text-transform: uppercase;
      flex-shrink: 0;
    }

    .sft-user-chip__role {
      color: var(--sft-text-secondary);
      font-size: var(--sft-type-label, 14px);
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
  `],
})
export class UserChipComponent {
  private readonly jwtService = inject(JwtService);

  readonly role = computed<string | null>(() => this.jwtService.role());

  readonly initials = computed<string>(() => {
    const email = this._getEmail();
    if (!email) return '?';
    const localPart = email.split('@')[0] ?? '';
    const parts = localPart.split(/[._-]/);
    if (parts.length >= 2) {
      return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase();
    }
    return localPart.slice(0, 2).toUpperCase() || '?';
  });

  readonly ariaLabel = computed<string>(() => {
    const role = this.role();
    return role ? `Utente corrente: ${role}` : 'Utente non autenticato';
  });

  private _getEmail(): string | null {
    const token = this.jwtService.getToken();
    if (!token) return null;
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return null;
      const payload = parts[1];
      if (!payload) return null;
      const padded = payload.replace(/-/g, '+').replace(/_/g, '/');
      const json = atob(padded);
      const parsed = JSON.parse(json) as { email?: string };
      return parsed.email ?? null;
    } catch {
      return null;
    }
  }
}
