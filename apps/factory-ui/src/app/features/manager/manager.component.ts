import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Manager area placeholder.
 * Focal point: KPI dashboard (OEE, MTTR, MTBF, etc.), Governor alerts, Supply chain.
 * Full implementation: plan 10-07.
 */
@Component({
  selector: 'sft-manager',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="sft-feature-placeholder">
      <h1 class="sft-type-display" style="color: var(--sft-text-primary)">Area Manager</h1>
      <p class="sft-type-body" style="color: var(--sft-text-secondary)">
        Dashboard KPI (OEE, MTTR, MTBF), alert governor, supply chain.
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
export class ManagerComponent {}
