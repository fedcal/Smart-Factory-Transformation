import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Admin area placeholder.
 * Focal point: User management, full audit log.
 * Full implementation: plan 10-07.
 */
@Component({
  selector: 'sft-admin',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="sft-feature-placeholder">
      <h1 class="sft-type-display" style="color: var(--sft-text-primary)">Amministrazione</h1>
      <p class="sft-type-body" style="color: var(--sft-text-secondary)">
        Gestione utenti, audit log completo.
        <br>Implementazione completa: Piano 10-07.
      </p>
    </div>
  `,
  styles: [`
    .sft-feature-placeholder {
      padding: var(--sft-space-6);
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4);
    }
  `],
})
export class AdminComponent {}
