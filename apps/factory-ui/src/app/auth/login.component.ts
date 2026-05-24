import {
  Component,
  inject,
  signal,
  computed,
  OnInit,
  PLATFORM_ID,
} from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import {
  FormsModule,
  ReactiveFormsModule,
  FormBuilder,
  Validators,
} from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { JwtService } from '../core/auth/jwt.service';
import { SseService } from '../core/sse/sse.service';
import { UserRole } from '../core/auth/rbac.guard';

/**
 * LoginComponent — login page with dev-mode persona quick-select.
 *
 * Requirements: UI-02, HITL-01, 10-UI-SPEC Component 2.
 *   - Centered 400px card on --sft-surface-card
 *   - Mat form fields: email + password (show/hide, 64px)
 *   - 64px CTA accent button, full width
 *   - Dev-mode chip group with 5 seeded personas (UI-SPEC JWT table)
 *   - On submit: POST /auth/login → JwtService.setToken → SseService.connect → navigate
 *   - Error snackbar (transloco-keyed messages)
 *   - Loading spinner-in-button (button disabled)
 *   - SSR-safe: form works server side, no localStorage direct access
 *
 * Route home mapping (UI-SPEC):
 *   operator → /operator
 *   shift-supervisor → /manager
 *   manager → /manager
 *   technician → /technician
 *   admin → /admin
 */

interface LoginResponse {
  access_token: string;
  token_type: string;
}

/** Seeded dev persona credentials (UI-SPEC seeded users — password: mantis2026) */
const DEV_PERSONAS: { label: string; email: string; password: string; route: string }[] = [
  { label: 'Operator',    email: 'operator@mantis.it',   password: 'mantis2026', route: '/operator' },
  { label: 'Supervisor',  email: 'supervisor@mantis.it', password: 'mantis2026', route: '/manager' },
  { label: 'Technician',  email: 'technician@mantis.it', password: 'mantis2026', route: '/technician' },
  { label: 'CIO',         email: 'cio@mantis.it',        password: 'mantis2026', route: '/manager' },
  { label: 'Admin',       email: 'admin@mantis.it',      password: 'mantis2026', route: '/admin' },
];

/** Maps JWT role claim to the persona home route. */
const ROLE_ROUTE_MAP: Record<UserRole, string> = {
  operator: '/operator',
  'shift-supervisor': '/manager',
  manager: '/manager',
  technician: '/technician',
  admin: '/admin',
};

/**
 * SSE stream URLs (relative — proxied via API gateway).
 * CR-04: /v1/stream/events does not exist; the real endpoints are:
 *   /v1/stream/kpi        — live KPI updates (all roles)
 *   /v1/stream/approvals  — approval events (operator/supervisor/manager/admin)
 *   /v1/stream/alerts     — alert events (all roles, HITL-10 rate-limited)
 *
 * The KPI channel is connected after login as the universal primary channel.
 * Approvals and alerts channels are connected by their respective feature
 * components (ApprovalQueueComponent, AlertFeedComponent) when mounted.
 */
const SSE_KPI_URL = '/v1/stream/kpi';

@Component({
  selector: 'sft-login',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="sft-login-page">
      <div class="sft-login-card" role="main">

        <!-- Logo + title -->
        <div class="sft-login-brand">
          <div class="sft-login-logo" aria-hidden="true">SF</div>
          <h1 class="sft-type-display sft-login-title">Smart Factory</h1>
          <p class="sft-type-label sft-login-subtitle">Mantis Textile Group</p>
        </div>

        <!-- Login form -->
        <form [formGroup]="loginForm" (ngSubmit)="onSubmit()" novalidate>

          <mat-form-field appearance="outline" class="sft-login-field">
            <mat-label>Indirizzo email</mat-label>
            <input
              matInput
              type="email"
              formControlName="email"
              placeholder="operatore@mantis.it"
              autocomplete="email"
              [attr.aria-describedby]="loginForm.get('email')?.invalid && loginForm.get('email')?.touched ? 'email-error' : null">
            @if (loginForm.get('email')?.invalid && loginForm.get('email')?.touched) {
              <mat-error id="email-error">Inserire un indirizzo email valido.</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline" class="sft-login-field">
            <mat-label>Password</mat-label>
            <input
              matInput
              [type]="showPassword() ? 'text' : 'password'"
              formControlName="password"
              autocomplete="current-password">
            <button
              mat-icon-button
              matSuffix
              type="button"
              class="sft-login-pwd-toggle"
              [attr.aria-label]="showPassword() ? 'Nascondi password' : 'Mostra password'"
              (click)="togglePassword()">
              <span class="material-symbols-outlined" aria-hidden="true">
                {{ showPassword() ? 'visibility_off' : 'visibility' }}
              </span>
            </button>
          </mat-form-field>

          <!-- Error state -->
          @if (errorMessage()) {
            <div class="sft-login-error" role="alert" aria-live="assertive">
              {{ errorMessage() }}
            </div>
          }

          <!-- CTA button — 64px, accent, full width -->
          <button
            mat-flat-button
            type="submit"
            class="sft-login-cta"
            color="primary"
            [disabled]="loading() || loginForm.invalid">
            @if (loading()) {
              <mat-spinner diameter="20" aria-label="Accesso in corso"></mat-spinner>
            } @else {
              Accedi
            }
          </button>

        </form>

        <!-- Dev-mode persona quick-select -->
        @if (isDevMode()) {
          <div class="sft-login-devmode">
            <p class="sft-type-label sft-login-devmode-label">
              Accesso rapido (dev)
            </p>
            <div class="sft-login-chips">
              @for (persona of devPersonas; track persona.email) {
                <button
                  type="button"
                  class="sft-login-chip sft-type-label"
                  [disabled]="loading()"
                  (click)="fillDevCredentials(persona)">
                  Accedi come {{ persona.label }}
                </button>
              }
            </div>
          </div>
        }

      </div>
    </div>
  `,
  styles: [`
    .sft-login-page {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: var(--sft-space-4, 16px);
      background-color: var(--sft-surface, #121418);
    }

    .sft-login-card {
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 12px;
      padding: var(--sft-space-8, 32px);
      width: 100%;
      max-width: 400px;
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
    }

    .sft-login-brand {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--sft-space-2, 8px);
      text-align: center;
    }

    .sft-login-logo {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 56px;
      height: 56px;
      border-radius: 12px;
      background-color: var(--sft-accent, #3B82F6);
      color: #ffffff;
      font-weight: 600;
      font-size: 20px;
      font-family: var(--sft-font-family, 'Inter', system-ui, sans-serif);
    }

    .sft-login-title {
      color: var(--sft-text-primary, #F0F2F5);
      margin: 0;
    }

    .sft-login-subtitle {
      color: var(--sft-text-secondary, #9BA3B2);
      margin: 0;
    }

    .sft-login-field {
      width: 100%;
    }

    .sft-login-pwd-toggle {
      min-height: 64px;
      min-width: 64px;
    }

    .sft-login-cta {
      width: 100%;
      min-height: 64px;
      font-size: 16px;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .sft-login-error {
      padding: var(--sft-space-2, 8px) var(--sft-space-4, 16px);
      border-radius: 4px;
      background-color: color-mix(in srgb, var(--sft-destructive, #EF4444) 12%, transparent);
      border: 1px solid var(--sft-destructive, #EF4444);
      color: var(--sft-destructive, #EF4444);
      font-size: 14px;
      font-family: var(--sft-font-family, 'Inter', system-ui, sans-serif);
    }

    .sft-login-devmode {
      border-top: 1px solid var(--sft-border, #363B47);
      padding-top: var(--sft-space-4, 16px);
    }

    .sft-login-devmode-label {
      color: var(--sft-text-secondary, #9BA3B2);
      margin: 0 0 8px 0;
    }

    .sft-login-chips {
      display: flex;
      flex-wrap: wrap;
      gap: var(--sft-space-2, 8px);
    }

    .sft-login-chip {
      padding: var(--sft-space-1, 4px) var(--sft-space-2, 8px);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 16px;
      background-color: var(--sft-surface, #121418);
      color: var(--sft-text-secondary, #9BA3B2);
      cursor: pointer;
      min-height: 32px;
      font-family: var(--sft-font-family, 'Inter', system-ui, sans-serif);
      transition: border-color 150ms ease-out, color 150ms ease-out;

      &:hover:not(:disabled) {
        border-color: var(--sft-accent, #3B82F6);
        color: var(--sft-accent, #3B82F6);
      }

      &:focus-visible {
        outline: 2px solid var(--sft-accent, #3B82F6);
        outline-offset: 2px;
      }

      &:disabled {
        opacity: 0.38;
        cursor: not-allowed;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-login-chip,
      .sft-login-cta {
        transition: none;
      }
    }
  `],
})
export class LoginComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly http = inject(HttpClient);
  private readonly jwtService = inject(JwtService);
  private readonly sseService = inject(SseService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly platformId = inject(PLATFORM_ID);

  readonly loginForm = this.fb.group({
    email:    ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  readonly showPassword = signal(false);
  readonly loading = signal(false);
  readonly errorMessage = signal('');

  /** Dev-mode chip group — always visible (factory demo environment) */
  readonly isDevMode = computed<boolean>(() => true);

  /** Seeded dev persona credentials (UI-SPEC) */
  readonly devPersonas = DEV_PERSONAS;

  ngOnInit(): void {
    // If already authenticated, redirect to the persona home
    if (this.jwtService.isAuthenticated()) {
      const role = this.jwtService.role();
      const route = role ? (ROLE_ROUTE_MAP[role] ?? '/operator') : '/operator';
      this.router.navigate([route]);
    }
  }

  togglePassword(): void {
    this.showPassword.update((v) => !v);
  }

  fillDevCredentials(persona: { email: string; password: string }): void {
    this.loginForm.patchValue({
      email:    persona.email,
      password: persona.password,
    });
  }

  onSubmit(): void {
    if (this.loginForm.invalid || this.loading()) return;

    this.loading.set(true);
    this.errorMessage.set('');

    const { email, password } = this.loginForm.getRawValue();

    this.http.post<LoginResponse>('/auth/login', { email, password }).subscribe({
      next: (response) => {
        this._handleLoginSuccess(response.access_token);
      },
      error: (err: HttpErrorResponse) => {
        this._handleLoginError(err);
      },
    });
  }

  private _handleLoginSuccess(token: string): void {
    this.jwtService.setToken(token);

    // Connect the KPI SSE channel with the new token (browser only — SseService guards SSR).
    // CR-04: use the real /v1/stream/kpi endpoint (not the non-existent /v1/stream/events).
    // Approvals and alerts channels are connected by their feature components when mounted.
    if (isPlatformBrowser(this.platformId)) {
      this.sseService.connect(SSE_KPI_URL, token);
    }

    const role = this.jwtService.role();
    const route = role ? (ROLE_ROUTE_MAP[role] ?? '/operator') : '/operator';

    this.loading.set(false);
    this.router.navigate([route]);
  }

  private _handleLoginError(err: HttpErrorResponse): void {
    this.loading.set(false);

    if (err.status === 401 || err.status === 403) {
      this.errorMessage.set(
        'Credenziali non valide. Controlla email e password.',
      );
    } else {
      this.errorMessage.set(
        'Si è verificato un errore. Riprova o contatta l\'amministratore.',
      );
    }

    this.snackBar.open(
      this.errorMessage(),
      'OK',
      { duration: 5000, panelClass: 'sft-snack-error' },
    );
  }
}
