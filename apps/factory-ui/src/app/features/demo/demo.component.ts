import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Demo persona walkthrough placeholder.
 * Accessible to all authenticated roles (including dev-mode).
 * Full implementation: plan 10-08.
 */
@Component({
  selector: 'sft-demo',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="sft-feature-placeholder">
      <h1 class="sft-type-display" style="color: var(--sft-text-primary)">Demo Persona</h1>
      <p class="sft-type-body" style="color: var(--sft-text-secondary)">
        Walkthrough guidato: Operatore (Luca), Capo Turno (Anna), Tecnico (Marco), CIO (Elena).
        <br>Implementazione completa: Piano 10-08.
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
export class DemoComponent {}
