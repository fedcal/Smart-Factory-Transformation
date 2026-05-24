import {
  Component,
  OnInit,
  inject,
  PLATFORM_ID,
  signal,
  computed,
} from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { JwtService } from '../../core/auth/jwt.service';
import { SseService } from '../../core/sse/sse.service';
import { OperatorComponent } from '../operator/operator.component';
import { ManagerComponent } from '../manager/manager.component';
import { TechnicianComponent } from '../technician/technician.component';
import { AdminComponent } from '../admin/admin.component';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Persona step definition — one entry per UI-SPEC Component 7 step.
 *
 * UI-SPEC Copywriting Contract step labels:
 *   step 1: "Operatore (Luca) — Approvazione anomalia"
 *   step 2: "Capo Turno (Anna) — Handover turno"
 *   step 3: "Tecnico (Marco) — Procedura manutenzione"
 *   step 4: "CIO (Elena) — Dashboard ROI"
 *
 * Each step embeds the REAL persona component (not a screenshot) per
 * UI-SPEC: "Componente demo specifico per persona (dati reali dal seed, non mock)".
 */
interface PersonaStep {
  readonly index: number;
  /** Short label shown in the stepper header */
  readonly stepLabel: string;
  /** Avatar initials */
  readonly avatarInitials: string;
  /** Avatar background color per persona */
  readonly avatarColor: string;
  /** Full persona name */
  readonly name: string;
  /** Role label */
  readonly role: string;
  /** 2–3 line scenario description (UI-SPEC Component 7 — PersonaCard) */
  readonly scenario: string;
  /** Route home for "Esci dalla demo" */
  readonly routeHome: string;
}

// ---------------------------------------------------------------------------
// Constants — step definitions matching UI-SPEC + Copywriting Contract
// ---------------------------------------------------------------------------

const PERSONA_STEPS: PersonaStep[] = [
  {
    index: 0,
    stepLabel: 'Operatore (Luca) — Approvazione anomalia',
    avatarInitials: 'LB',
    avatarColor: '#3B82F6',
    name: 'Luca Bianchi',
    role: 'Operatore di Produzione',
    scenario:
      'Luca riceve un alert di anomalia dal telaio TLR-04. ' +
      'Il sistema AI ha proposto uno shutdown preventivo. ' +
      'Luca rivede le evidenze e decide se approvare o rifiutare.',
    routeHome: '/operator',
  },
  {
    index: 1,
    stepLabel: 'Capo Turno (Anna) — Handover turno',
    avatarInitials: 'AR',
    avatarColor: '#22C55E',
    name: 'Anna Rossi',
    role: 'Capo Turno',
    scenario:
      'Anna supervisiona il cambio turno mattino-pomeriggio. ' +
      'Controlla i KPI di produzione (OEE 87.3%) e ' +
      'verifica gli ordini di reintegro scorte proposti dall\'AI.',
    routeHome: '/manager',
  },
  {
    index: 2,
    stepLabel: 'Tecnico (Marco) — Procedura manutenzione',
    avatarInitials: 'MF',
    avatarColor: '#F59E0B',
    name: 'Marco Ferrari',
    role: 'Tecnico di Manutenzione',
    scenario:
      'Marco gestisce l\'intervento sul cuscinetto del telaio TLR-04. ' +
      'Segue la procedura step-by-step guidata dall\'AI ' +
      'e approva il report di manutenzione preventiva.',
    routeHome: '/technician',
  },
  {
    index: 3,
    stepLabel: 'CIO (Elena) — Dashboard ROI',
    avatarInitials: 'EG',
    avatarColor: '#8B5CF6',
    name: 'Elena Greco',
    role: 'CIO / Direttore Operations',
    scenario:
      'Elena analizza le metriche di efficienza operativa del mese. ' +
      'Il sistema AI ha ottimizzato il consumo energetico (-12%) ' +
      'e ridotto il MTTR del 18%. Valuta l\'impatto OEPV.',
    routeHome: '/manager',
  },
];

/** Total number of steps */
const TOTAL_STEPS = PERSONA_STEPS.length;

/**
 * PersonaWalkthrough (data-testid="persona-stepper") — 4-step horizontal stepper.
 *
 * Requirements: UI-08, 10-UI-SPEC Component 7.
 *
 * Layout:
 *   StepStepper header (4 steps: Operatore/Capo Turno/Tecnico/CIO)
 *   PersonaCard (left panel: avatar initials, name, role, scenario)
 *   DemoContent (right panel: embeds REAL persona component)
 *   Navigation bar (Indietro / Avanti / Esci dalla demo)
 *
 * Behaviour:
 *   - Forward/back via "Avanti" / "Indietro" (64px touch, data-testid)
 *   - URL unchanged (stepper local navigation)
 *   - Each step embeds the REAL persona component with real seeded data
 *   - "Esci dalla demo" navigates to the role home of the logged-in user
 *   - T-10-09-02: /demo open to all authenticated; embeds data for their role
 *
 * SSR guard: SseService.connect() via each embedded component's own ngOnInit.
 * data-testid="persona-stepper" — required by 10-09-PLAN verification + E2E.
 * data-testid="demo-nav-next" — next button.
 * data-testid="demo-nav-prev" — prev button.
 */
@Component({
  selector: 'sft-persona-walkthrough',
  standalone: true,
  imports: [
    CommonModule,
    OperatorComponent,
    ManagerComponent,
    TechnicianComponent,
    AdminComponent,
  ],
  template: `
    <div class="sft-demo" data-testid="persona-stepper" aria-label="Demo persona walkthrough">

      <!-- Stepper header — 4 steps -->
      <nav
        class="sft-demo__stepper"
        aria-label="Passaggi demo persona"
        role="tablist">
        @for (step of steps; track step.index) {
          <button
            type="button"
            class="sft-demo__step-btn"
            [class.sft-demo__step-btn--active]="currentIndex() === step.index"
            [class.sft-demo__step-btn--done]="currentIndex() > step.index"
            role="tab"
            [attr.aria-selected]="currentIndex() === step.index"
            [attr.aria-label]="'Passo ' + (step.index + 1) + ': ' + step.stepLabel"
            (click)="goToStep(step.index)">

            <!-- Step indicator dot / number -->
            <span class="sft-demo__step-indicator" aria-hidden="true">
              @if (currentIndex() > step.index) {
                <span class="material-symbols-outlined sft-demo__step-check">
                  check_circle
                </span>
              } @else {
                {{ step.index + 1 }}
              }
            </span>

            <!-- Step label (hidden on mobile — handled by avatar color) -->
            <span class="sft-demo__step-label">{{ step.stepLabel }}</span>

          </button>

          <!-- Connector line between steps -->
          @if (step.index < steps.length - 1) {
            <div
              class="sft-demo__step-connector"
              [class.sft-demo__step-connector--done]="currentIndex() > step.index"
              aria-hidden="true">
            </div>
          }
        }
      </nav>

      <!-- Step progress label (screen reader) -->
      <div
        class="sr-only"
        role="status"
        aria-live="polite">
        Passo {{ currentIndex() + 1 }} di {{ totalSteps }}: {{ currentStep().stepLabel }}
      </div>

      <!-- Main content: PersonaCard + DemoContent -->
      <div class="sft-demo__content" role="tabpanel" [attr.aria-label]="currentStep().stepLabel">

        <!-- PersonaCard (left panel, 280px) -->
        <aside class="sft-demo__persona-card" aria-label="Scheda persona">

          <!-- Avatar with initials -->
          <div
            class="sft-demo__avatar"
            [style.background-color]="currentStep().avatarColor"
            aria-hidden="true">
            {{ currentStep().avatarInitials }}
          </div>

          <div class="sft-demo__persona-info">
            <h2 class="sft-demo__persona-name">{{ currentStep().name }}</h2>
            <span class="sft-demo__persona-role">{{ currentStep().role }}</span>
          </div>

          <p class="sft-demo__persona-scenario">{{ currentStep().scenario }}</p>

          <!-- Step counter pill -->
          <div class="sft-demo__step-counter" aria-hidden="true">
            <span>{{ currentIndex() + 1 }}</span>
            <span class="sft-demo__step-counter-sep">/</span>
            <span>{{ totalSteps }}</span>
          </div>

        </aside>

        <!-- DemoContent — real persona component for the current step -->
        <main class="sft-demo__demo-view" aria-label="Vista persona corrente">
          @switch (currentIndex()) {
            @case (0) {
              <!-- Step 1: Operatore Luca — OperatorComponent -->
              <sft-operator></sft-operator>
            }
            @case (1) {
              <!-- Step 2: Capo Turno Anna — ManagerComponent -->
              <sft-manager></sft-manager>
            }
            @case (2) {
              <!-- Step 3: Tecnico Marco — TechnicianComponent -->
              <sft-technician></sft-technician>
            }
            @case (3) {
              <!-- Step 4: CIO Elena — ManagerComponent (ROI/KPI view) -->
              <sft-manager></sft-manager>
            }
          }
        </main>

      </div>

      <!-- Navigation bar -->
      <nav class="sft-demo__nav-bar" aria-label="Navigazione demo">

        <!-- Indietro -->
        <button
          type="button"
          class="sft-demo__nav-btn sft-demo__nav-btn--prev"
          data-testid="demo-nav-prev"
          [disabled]="currentIndex() === 0"
          [attr.aria-disabled]="currentIndex() === 0"
          (click)="prevStep()"
          aria-label="Passo precedente">
          <span class="material-symbols-outlined sft-demo__nav-icon" aria-hidden="true">
            arrow_back
          </span>
          <span>Indietro</span>
        </button>

        <!-- Esci dalla demo (center) -->
        <button
          type="button"
          class="sft-demo__exit-btn"
          (click)="exitDemo()"
          aria-label="Esci dalla demo e torna alla tua area">
          <span class="material-symbols-outlined sft-demo__exit-icon" aria-hidden="true">
            logout
          </span>
          <span>Esci dalla demo</span>
        </button>

        <!-- Avanti -->
        <button
          type="button"
          class="sft-demo__nav-btn sft-demo__nav-btn--next"
          data-testid="demo-nav-next"
          [disabled]="currentIndex() === totalSteps - 1"
          [attr.aria-disabled]="currentIndex() === totalSteps - 1"
          (click)="nextStep()"
          aria-label="Passo successivo">
          <span>Avanti</span>
          <span class="material-symbols-outlined sft-demo__nav-icon" aria-hidden="true">
            arrow_forward
          </span>
        </button>

      </nav>

    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 100%;
    }

    .sft-demo {
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-4, 16px);
      box-sizing: border-box;
      min-height: 100%;
    }

    /* Screen-reader only utility */
    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border-width: 0;
    }

    /* ------------------------------------------------------------------ */
    /* Stepper header                                                       */
    /* ------------------------------------------------------------------ */

    .sft-demo__stepper {
      display: flex;
      align-items: center;
      gap: 0;
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      padding: var(--sft-space-4, 16px);
      overflow-x: auto;
    }

    .sft-demo__step-btn {
      display: flex;
      align-items: center;
      gap: var(--sft-space-2, 8px);
      padding: var(--sft-space-2, 8px) var(--sft-space-4, 16px);
      min-height: 64px;
      min-width: 64px;
      border: none;
      background: transparent;
      color: var(--sft-text-secondary, #9BA3B2);
      font-size: 14px;
      cursor: pointer;
      border-radius: 6px;
      transition: background-color 150ms ease-out, color 150ms ease-out;
      white-space: nowrap;
      flex-shrink: 0;

      &:hover {
        background-color: color-mix(in srgb, var(--sft-accent, #3B82F6) 8%, transparent);
        color: var(--sft-text-primary, #F0F2F5);
      }

      &:focus-visible {
        outline: 2px solid var(--sft-accent, #3B82F6);
        outline-offset: 2px;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-demo__step-btn {
        transition: none;
      }
    }

    .sft-demo__step-btn--active {
      color: var(--sft-accent, #3B82F6) !important;
      background-color: color-mix(in srgb, var(--sft-accent, #3B82F6) 12%, transparent);
    }

    .sft-demo__step-btn--done {
      color: var(--sft-success, #22C55E) !important;
    }

    .sft-demo__step-indicator {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 2px solid currentColor;
      font-size: 13px;
      font-weight: 600;
      flex-shrink: 0;
    }

    .sft-demo__step-btn--active .sft-demo__step-indicator {
      background-color: var(--sft-accent, #3B82F6);
      color: #fff;
      border-color: var(--sft-accent, #3B82F6);
    }

    .sft-demo__step-btn--done .sft-demo__step-indicator {
      background-color: var(--sft-success, #22C55E);
      border-color: var(--sft-success, #22C55E);
    }

    .sft-demo__step-check {
      font-size: 18px;
      color: #fff;
    }

    .sft-demo__step-label {
      font-size: 14px;
    }

    @media (max-width: 767px) {
      .sft-demo__step-label {
        display: none;
      }
    }

    /* Connector line */
    .sft-demo__step-connector {
      flex: 1;
      min-width: 16px;
      height: 2px;
      background-color: var(--sft-border, #363B47);
      transition: background-color 150ms ease-out;
    }

    .sft-demo__step-connector--done {
      background-color: var(--sft-success, #22C55E);
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-demo__step-connector {
        transition: none;
      }
    }

    /* ------------------------------------------------------------------ */
    /* Main content layout                                                  */
    /* ------------------------------------------------------------------ */

    .sft-demo__content {
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: var(--sft-space-4, 16px);
      align-items: start;
      flex: 1;
      min-height: 0;
    }

    @media (max-width: 1023px) {
      .sft-demo__content {
        grid-template-columns: 1fr;
      }
    }

    /* ------------------------------------------------------------------ */
    /* PersonaCard                                                          */
    /* ------------------------------------------------------------------ */

    .sft-demo__persona-card {
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      padding: var(--sft-space-6, 24px);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--sft-space-4, 16px);
      text-align: center;
      position: sticky;
      top: var(--sft-space-4, 16px);
    }

    @media (max-width: 1023px) {
      .sft-demo__persona-card {
        position: static;
        flex-direction: row;
        text-align: left;
        align-items: center;
      }
    }

    .sft-demo__avatar {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      font-weight: 600;
      color: #fff;
      flex-shrink: 0;
      transition: background-color 200ms ease-out;
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-demo__avatar {
        transition: none;
      }
    }

    @media (max-width: 1023px) {
      .sft-demo__avatar {
        width: 56px;
        height: 56px;
        font-size: 20px;
      }
    }

    .sft-demo__persona-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }

    .sft-demo__persona-name {
      font-size: 20px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      margin: 0;
      line-height: 1.3;
    }

    @media (max-width: 1023px) {
      .sft-demo__persona-name {
        font-size: 16px;
      }
    }

    .sft-demo__persona-role {
      font-size: 14px;
      color: var(--sft-accent, #3B82F6);
      font-weight: 600;
    }

    .sft-demo__persona-scenario {
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
      line-height: 1.6;
      margin: 0;
    }

    @media (max-width: 1023px) {
      .sft-demo__persona-scenario {
        display: none;
      }
    }

    .sft-demo__step-counter {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
      padding: 4px 12px;
      background-color: var(--sft-surface, #121418);
      border-radius: 12px;
    }

    .sft-demo__step-counter-sep {
      color: var(--sft-border, #363B47);
    }

    @media (max-width: 1023px) {
      .sft-demo__step-counter {
        margin-left: auto;
        flex-shrink: 0;
      }
    }

    /* ------------------------------------------------------------------ */
    /* Demo content view                                                    */
    /* ------------------------------------------------------------------ */

    .sft-demo__demo-view {
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      overflow: hidden;
      min-height: 480px;
    }

    /* ------------------------------------------------------------------ */
    /* Navigation bar                                                       */
    /* ------------------------------------------------------------------ */

    .sft-demo__nav-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-4, 16px);
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      flex-wrap: wrap;
    }

    /* Avanti / Indietro buttons (64px touch target) */
    .sft-demo__nav-btn {
      display: flex;
      align-items: center;
      gap: var(--sft-space-2, 8px);
      min-height: 64px;
      min-width: 120px;
      padding: 0 var(--sft-space-6, 24px);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      background-color: transparent;
      color: var(--sft-text-primary, #F0F2F5);
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: background-color 150ms ease-out, border-color 150ms ease-out;

      &:hover:not([disabled]) {
        background-color: color-mix(in srgb, var(--sft-accent, #3B82F6) 10%, transparent);
        border-color: var(--sft-accent, #3B82F6);
        color: var(--sft-accent, #3B82F6);
      }

      &:focus-visible {
        outline: 2px solid var(--sft-accent, #3B82F6);
        outline-offset: 2px;
      }

      &[disabled] {
        opacity: 0.38;
        cursor: not-allowed;
        pointer-events: none;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-demo__nav-btn {
        transition: none;
      }
    }

    .sft-demo__nav-btn--next {
      background-color: var(--sft-accent, #3B82F6);
      border-color: var(--sft-accent, #3B82F6);
      color: #fff;

      &:hover:not([disabled]) {
        background-color: color-mix(in srgb, var(--sft-accent, #3B82F6) 85%, #fff);
        color: #fff;
      }

      &[disabled] {
        background-color: color-mix(in srgb, var(--sft-accent, #3B82F6) 38%, transparent);
        border-color: transparent;
        color: var(--sft-text-secondary, #9BA3B2);
      }
    }

    .sft-demo__nav-icon {
      font-size: 20px;
    }

    /* Exit button */
    .sft-demo__exit-btn {
      display: flex;
      align-items: center;
      gap: var(--sft-space-2, 8px);
      min-height: 64px;
      min-width: 64px;
      padding: 0 var(--sft-space-4, 16px);
      border: none;
      background-color: transparent;
      color: var(--sft-text-secondary, #9BA3B2);
      font-size: 14px;
      cursor: pointer;
      border-radius: 6px;
      transition: color 150ms ease-out;

      &:hover {
        color: var(--sft-text-primary, #F0F2F5);
      }

      &:focus-visible {
        outline: 2px solid var(--sft-accent, #3B82F6);
        outline-offset: 2px;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-demo__exit-btn {
        transition: none;
      }
    }

    .sft-demo__exit-icon {
      font-size: 18px;
    }

    @media (max-width: 767px) {
      .sft-demo__nav-bar {
        flex-direction: column;
        align-items: stretch;
      }

      .sft-demo__nav-btn {
        justify-content: center;
        min-width: 64px;
      }

      .sft-demo__exit-btn {
        justify-content: center;
        order: -1;
      }
    }
  `],
})
export class PersonaWalkthroughComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly jwtService = inject(JwtService);
  private readonly platformId = inject(PLATFORM_ID);

  readonly steps = PERSONA_STEPS;
  readonly totalSteps = TOTAL_STEPS;

  /** Current step index (0-based, signal for reactivity) */
  private readonly _currentIndex = signal<number>(0);
  readonly currentIndex = computed(() => this._currentIndex());

  /** Current step definition */
  readonly currentStep = computed(() => this.steps[this._currentIndex()]);

  ngOnInit(): void {
    // SSR guard: no browser APIs in constructor/ngOnInit
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }
  }

  /** Navigate to a specific step by index (stepper header click) */
  goToStep(index: number): void {
    if (index >= 0 && index < TOTAL_STEPS) {
      this._currentIndex.set(index);
    }
  }

  /** Navigate to the next step */
  nextStep(): void {
    this._currentIndex.update((i) => Math.min(TOTAL_STEPS - 1, i + 1));
  }

  /** Navigate to the previous step */
  prevStep(): void {
    this._currentIndex.update((i) => Math.max(0, i - 1));
  }

  /**
   * Exit the demo and navigate to the logged-in user's role home.
   * Falls back to /operator if role is unresognized.
   */
  exitDemo(): void {
    const role = this.jwtService.getCurrentRole();
    const roleHomeMap: Record<string, string> = {
      operator: '/operator',
      technician: '/technician',
      'shift-supervisor': '/manager',
      manager: '/manager',
      admin: '/admin',
    };
    const home = (role && roleHomeMap[role]) ?? '/operator';
    this.router.navigate([home]);
  }
}
