import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Operator area placeholder.
 * Focal point: ApprovalQueueFeed (red badge count) + AlertFeed.
 * Full implementation: plan 10-07.
 */
@Component({
  selector: 'sft-operator',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="sft-feature-placeholder">
      <h1 class="sft-type-display" style="color: var(--sft-text-primary)">Area Operatore</h1>
      <p class="sft-type-body" style="color: var(--sft-text-secondary)">
        Approvazioni pendenti, alert in tempo reale, procedura guidata.
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
export class OperatorComponent {}
