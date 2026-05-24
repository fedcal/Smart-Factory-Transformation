import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterModule } from '@angular/router';

/**
 * Login page (UI-SPEC Component 2).
 *
 * - Centered layout, max-width 400px
 * - Mat form fields for email + password
 * - 64px CTA button (accent)
 * - Dev-mode persona quick-select chips (plan 10-05 wires real auth)
 * - Copy: Italian primary (UI-SPEC Copywriting Contract)
 *
 * Full auth implementation: plan 10-05 (JwtService, real login POST).
 */
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
    RouterModule,
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
              [attr.aria-describedby]="loginForm.get('email')?.invalid ? 'email-error' : null">
            @if (loginForm.get('email')?.invalid && loginForm.get('email')?.touched) {
              <mat-error id="email-error">Inserire un indirizzo email valido.</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline" class="sft-login-field">
            <mat-label>Password</mat-label>
            <input
              matInput
              [type]="showPassword ? 'text' : 'password'"
              formControlName="password"
              autocomplete="current-password">
            <button
              mat-icon-button
              matSuffix
              type="button"
              class="sft-login-pwd-toggle"
              [attr.aria-label]="showPassword ? 'Nascondi password' : 'Mostra password'"
              (click)="showPassword = !showPassword">
              <span class="material-symbols-outlined" aria-hidden="true">
                {{ showPassword ? 'visibility_off' : 'visibility' }}
              </span>
            </button>
          </mat-form-field>

          <!-- Error state -->
          @if (errorMessage) {
            <div class="sft-login-error" role="alert" aria-live="assertive">
              {{ errorMessage }}
            </div>
          }

          <!-- CTA button — 64px, accent, full width -->
          <button
            mat-flat-button
            type="submit"
            class="sft-login-cta"
            color="primary"
            [disabled]="loading || loginForm.invalid">
            @if (loading) {
              <mat-spinner diameter="20" aria-label="Accesso in corso"></mat-spinner>
            } @else {
              Accedi
            }
          </button>
        </form>

        <!-- Dev-mode persona quick-select (visible in development only) -->
        <div class="sft-login-devmode" *ngIf="isDevMode">
          <p class="sft-type-label" style="color: var(--sft-text-secondary); margin-bottom: 8px;">
            Accesso rapido (dev)
          </p>
          <div class="sft-login-chips">
            @for (persona of devPersonas; track persona.email) {
              <button
                type="button"
                class="sft-login-chip sft-type-label"
                (click)="fillDevCredentials(persona)">
                Accedi come {{ persona.label }}
              </button>
            }
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .sft-login-page {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: var(--sft-space-4);
      background-color: var(--sft-surface);
    }

    .sft-login-card {
      background-color: var(--sft-surface-card);
      border: 1px solid var(--sft-border);
      border-radius: 12px;
      padding: var(--sft-space-8);
      width: 100%;
      max-width: 400px;
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4);
    }

    .sft-login-brand {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--sft-space-2);
      text-align: center;
    }

    .sft-login-logo {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 56px;
      height: 56px;
      border-radius: 12px;
      background-color: var(--sft-accent);
      color: #ffffff;
      font-weight: 600;
      font-size: 20px;
      font-family: var(--sft-font-family);
    }

    .sft-login-title {
      color: var(--sft-text-primary);
      margin: 0;
    }

    .sft-login-subtitle {
      color: var(--sft-text-secondary);
      margin: 0;
    }

    .sft-login-field {
      width: 100%;
    }

    .sft-login-cta {
      width: 100%;
      min-height: var(--sft-touch-target, 64px);
      font-size: 16px;
      font-weight: 600;
    }

    .sft-login-error {
      padding: var(--sft-space-2) var(--sft-space-4);
      border-radius: 4px;
      background-color: color-mix(in srgb, var(--sft-destructive) 12%, transparent);
      border: 1px solid var(--sft-destructive);
      color: var(--sft-destructive);
      font-size: 14px;
      font-family: var(--sft-font-family);
    }

    .sft-login-devmode {
      border-top: 1px solid var(--sft-border);
      padding-top: var(--sft-space-4);
    }

    .sft-login-chips {
      display: flex;
      flex-wrap: wrap;
      gap: var(--sft-space-2);
    }

    .sft-login-chip {
      padding: var(--sft-space-1) var(--sft-space-2);
      border: 1px solid var(--sft-border);
      border-radius: 16px;
      background-color: var(--sft-surface);
      color: var(--sft-text-secondary);
      cursor: pointer;
      min-height: 32px;
      font-family: var(--sft-font-family);

      &:hover {
        border-color: var(--sft-accent);
        color: var(--sft-accent);
      }

      &:focus-visible {
        outline: var(--sft-focus-ring);
        outline-offset: var(--sft-focus-ring-offset);
      }
    }
  `],
})
export class LoginComponent {
  private readonly fb = new (class FbShim {
    group(controls: Record<string, unknown>) {
      return { controls, invalid: false };
    }
  })();

  readonly loginForm: FormGroup;
  showPassword = false;
  loading = false;
  errorMessage = '';

  /** Dev-mode visibility: true in non-production environments */
  readonly isDevMode = true; // Will be replaced by environment check in 10-05

  /** Dev-mode persona credentials (from UI-SPEC seeded users) */
  readonly devPersonas = [
    { label: 'Operator',    email: 'operator@mantis.it',   password: 'mantis2026', route: '/operator' },
    { label: 'Supervisor',  email: 'supervisor@mantis.it', password: 'mantis2026', route: '/manager' },
    { label: 'Technician',  email: 'technician@mantis.it', password: 'mantis2026', route: '/technician' },
    { label: 'CIO',         email: 'cio@mantis.it',        password: 'mantis2026', route: '/manager' },
    { label: 'Admin',       email: 'admin@mantis.it',      password: 'mantis2026', route: '/admin' },
  ];

  constructor(private readonly formBuilder: FormBuilder) {
    this.loginForm = this.formBuilder.group({
      email:    ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
    });
  }

  fillDevCredentials(persona: { email: string; password: string }): void {
    this.loginForm.patchValue({
      email:    persona.email,
      password: persona.password,
    });
  }

  onSubmit(): void {
    if (this.loginForm.invalid) return;
    // Auth logic wired in plan 10-05 (JwtService.login())
    this.errorMessage = 'Autenticazione non ancora configurata. Disponibile in Piano 10-05.';
  }
}
