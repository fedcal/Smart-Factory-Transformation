import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Technician area placeholder.
 * Focal point: Maintenance tasks, RCA, step-by-step procedure.
 * Full implementation: plan 10-07.
 */
@Component({
  selector: 'sft-technician',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="sft-feature-placeholder">
      <h1 class="sft-type-display" style="color: var(--sft-text-primary)">Area Tecnica</h1>
      <p class="sft-type-body" style="color: var(--sft-text-secondary)">
        Manutenzione, analisi delle cause radice (RCA), procedura step-by-step.
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
export class TechnicianComponent {}
