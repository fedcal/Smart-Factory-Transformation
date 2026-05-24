import {
  Component,
  Input,
  inject,
  signal,
  computed,
  OnChanges,
  SimpleChanges,
  OnDestroy,
  OnInit,
  PLATFORM_ID,
  DestroyRef,
  Injector,
  runInInjectionContext,
} from '@angular/core';
import { toObservable, takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import {
  MatDialogModule,
  MatDialog,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subscription } from 'rxjs';
import {
  EvidencePanelComponent,
  EvidencePanel,
} from './evidence-panel.component';
import { SseService, ApprovalResolvedEvent } from '../../core/sse/sse.service';

// ---------------------------------------------------------------------------
// ApprovalCard — Types
// ---------------------------------------------------------------------------

export type ApprovalStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'loading'
  | 'expired_sla';

export interface ApprovalCardData {
  id: string;
  status: ApprovalStatus;
  agent_name: string;
  cluster: string;
  action_type: string;
  escalation_tier: string;
  action_summary: string;
  sla_seconds: number;
  sla_started_at: string; // ISO 8601
  motivation?: string;     // set when approved/rejected
  evidence_panel: EvidencePanel | null;
}

interface DecideRequest {
  decision: 'APPROVED' | 'REJECTED';
  motivation: string;
}

interface DecideResponse {
  id: string;
  status: 'approved' | 'rejected';
  decided_at: string;
  motivation: string;
}

const MOTIVATION_MIN_LENGTH = 10;

/**
 * ApprovalCardComponent — HITL approval card with evidence panel + motivation gate.
 *
 * Requirements: HITL-01, HITL-06, HITL-07, UI-03, 10-UI-SPEC Component 3.
 *   - data-testid="approval-card" on host element wrapper
 *   - data-testid="approval-card-status" on StatusChip
 *   - EvidencePanel embedded (data-testid="evidence-panel")
 *   - data-testid="motivation-textarea" — min 10 chars (HITL-07)
 *   - data-testid="approve-btn" — disabled until motivation >= 10 chars
 *   - data-testid="reject-btn" — opens confirm dialog, then POSTs decide
 *   - Border-left color semantic: warning=pending, success=approved, destructive=rejected
 *   - Loading state disables both buttons
 *   - SLA countdown (role=status, aria-live=polite)
 *   - ActionBar hidden when status !== 'pending'
 *   - T-10-06-01: motivation sent to POST /v1/approvals/{id}/decide
 */
@Component({
  selector: 'sft-approval-card',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatDialogModule,
    MatSnackBarModule,
    EvidencePanelComponent,
  ],
  template: `
    <div
      class="sft-approval-card"
      [class]="'sft-approval-card--' + currentStatus()"
      data-testid="approval-card"
      role="article"
      [attr.aria-label]="'Approvazione: ' + (card?.action_summary ?? '')">

      <!-- Header -->
      <div class="sft-approval-card__header">
        <div class="sft-approval-card__badges">
          <!-- Agent badge -->
          <mat-chip class="sft-chip sft-chip--agent">
            {{ card?.agent_name ?? '' }}
          </mat-chip>

          <!-- Escalation tier badge -->
          <mat-chip class="sft-chip sft-chip--tier">
            {{ card?.escalation_tier ?? '' }}
          </mat-chip>

          <!-- Action type label -->
          <span class="sft-type-label sft-approval-card__action-type">
            {{ card?.action_type ?? '' }}
          </span>
        </div>

        <div class="sft-approval-card__status-row">
          <!-- SLA countdown -->
          @if (currentStatus() === 'pending') {
            <div
              class="sft-approval-card__sla"
              [class.sft-approval-card__sla--warning]="isSlaWarning()"
              role="status"
              aria-live="polite">
              {{ slaLabel() }}
            </div>
          }

          <!-- Status chip -->
          <mat-chip
            class="sft-chip"
            [class]="'sft-chip--status-' + currentStatus()"
            data-testid="approval-card-status"
            [attr.aria-label]="'Stato: ' + statusLabel()">
            {{ statusLabel() }}
          </mat-chip>
        </div>
      </div>

      <!-- Action summary -->
      <div class="sft-approval-card__summary sft-type-body">
        {{ card?.action_summary ?? '' }}
      </div>

      <!-- Evidence Panel (default open for pending) -->
      @if (card?.evidence_panel) {
        <div class="sft-approval-card__evidence">
          <sft-evidence-panel [evidence]="card!.evidence_panel"></sft-evidence-panel>
        </div>
      }

      <!-- Motivation input — visible only for pending -->
      @if (currentStatus() === 'pending') {
        <div class="sft-approval-card__motivation">
          <mat-form-field appearance="outline" class="sft-motivation-field">
            <mat-label>Motivazione</mat-label>
            <textarea
              matInput
              [(ngModel)]="motivationText"
              (ngModelChange)="onMotivationChange($event)"
              placeholder="Inserisci la motivazione (min. 10 caratteri)..."
              rows="3"
              data-testid="motivation-textarea"
              [attr.aria-describedby]="motivationErrorId"
              aria-required="true">
            </textarea>
            @if (showMotivationError()) {
              <mat-error [id]="motivationErrorId">
                La motivazione deve contenere almeno 10 caratteri.
              </mat-error>
            }
          </mat-form-field>

          <!-- CharCounter -->
          <div
            class="sft-motivation-counter sft-type-label"
            [class.sft-motivation-counter--valid]="isMotivationValid()"
            aria-live="polite">
            {{ motivationLength() }}/{{ motivationMinLength }} min
          </div>
        </div>
      }

      <!-- Read-only motivation for approved/rejected -->
      @if ((currentStatus() === 'approved' || currentStatus() === 'rejected') && card?.motivation) {
        <div class="sft-approval-card__motivation-readonly">
          <span class="sft-type-label" style="color: var(--sft-text-secondary)">Motivazione:</span>
          <p class="sft-type-body">{{ card!.motivation }}</p>
        </div>
      }

      <!-- ActionBar — visible only for pending (64px height) -->
      @if (currentStatus() === 'pending') {
        <div class="sft-approval-card__action-bar">
          <!-- Reject button — destructive -->
          <button
            mat-stroked-button
            type="button"
            class="sft-action-btn sft-action-btn--reject"
            data-testid="reject-btn"
            [disabled]="isSubmitting() || !isMotivationValid()"
            (click)="onReject()"
            aria-label="Rifiuta azione">
            @if (isSubmitting() && submittingDecision() === 'REJECTED') {
              <mat-spinner diameter="20"></mat-spinner>
            } @else {
              Rifiuta
            }
          </button>

          <!-- Approve button — accent -->
          <button
            mat-flat-button
            type="button"
            class="sft-action-btn sft-action-btn--approve"
            data-testid="approve-btn"
            [disabled]="isSubmitting() || !isMotivationValid()"
            (click)="onApprove()"
            color="primary"
            aria-label="Approva azione">
            @if (isSubmitting() && submittingDecision() === 'APPROVED') {
              <mat-spinner diameter="20"></mat-spinner>
            } @else {
              Approva azione
            }
          </button>
        </div>
      }

    </div>
  `,
  styles: [`
    .sft-approval-card {
      border: 1px solid var(--sft-border, #363B47);
      border-left: 4px solid var(--sft-warning, #F59E0B);
      border-radius: 8px;
      background-color: var(--sft-surface-card, #252932);
      width: 100%;
      max-width: 720px;
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-4, 16px);
      box-sizing: border-box;
    }

    .sft-approval-card--approved {
      border-left-color: var(--sft-success, #22C55E);
    }

    .sft-approval-card--rejected {
      border-left-color: var(--sft-destructive, #EF4444);
    }

    .sft-approval-card--loading {
      border-left-color: var(--sft-warning, #F59E0B);
      opacity: 0.85;
    }

    .sft-approval-card--expired_sla {
      border-left-color: var(--sft-destructive, #EF4444);
    }

    .sft-approval-card__header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      min-height: 56px;
    }

    .sft-approval-card__badges {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .sft-approval-card__action-type {
      color: var(--sft-text-secondary, #9BA3B2);
      font-size: 14px;
    }

    .sft-approval-card__status-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .sft-approval-card__sla {
      color: var(--sft-text-secondary, #9BA3B2);
      font-size: 14px;
    }

    .sft-approval-card__sla--warning {
      color: var(--sft-warning, #F59E0B);
      font-weight: 600;
    }

    /* Status chip colors */
    .sft-chip {
      font-size: var(--sft-type-label, 14px);
      height: 28px;
    }

    .sft-chip--status-pending {
      background-color: color-mix(in srgb, var(--sft-warning, #F59E0B) 20%, transparent) !important;
      color: var(--sft-warning, #F59E0B) !important;
    }

    .sft-chip--status-approved {
      background-color: color-mix(in srgb, var(--sft-success, #22C55E) 20%, transparent) !important;
      color: var(--sft-success, #22C55E) !important;
    }

    .sft-chip--status-rejected {
      background-color: color-mix(in srgb, var(--sft-destructive, #EF4444) 20%, transparent) !important;
      color: var(--sft-destructive, #EF4444) !important;
    }

    .sft-chip--status-loading {
      background-color: color-mix(in srgb, var(--sft-text-secondary, #9BA3B2) 20%, transparent) !important;
      color: var(--sft-text-secondary, #9BA3B2) !important;
    }

    .sft-chip--status-expired_sla {
      background-color: color-mix(in srgb, var(--sft-destructive, #EF4444) 20%, transparent) !important;
      color: var(--sft-destructive, #EF4444) !important;
    }

    .sft-approval-card__summary {
      color: var(--sft-text-primary, #F0F2F5);
      overflow: hidden;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      line-clamp: 3;
    }

    .sft-approval-card__evidence {
      /* EvidencePanel uses internal scroll */
    }

    .sft-approval-card__motivation {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .sft-motivation-field {
      width: 100%;
    }

    .sft-motivation-counter {
      text-align: right;
      color: var(--sft-text-secondary, #9BA3B2);
      font-size: var(--sft-type-label, 14px);
    }

    .sft-motivation-counter--valid {
      color: var(--sft-success, #22C55E);
    }

    .sft-approval-card__motivation-readonly {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 8px 12px;
      background-color: var(--sft-surface, #121418);
      border-radius: 6px;
    }

    .sft-approval-card__action-bar {
      display: flex;
      align-items: center;
      gap: var(--sft-space-4, 16px);
      justify-content: flex-end;
      min-height: 64px;
    }

    .sft-action-btn {
      min-height: 64px;
      min-width: 120px;
      font-size: 16px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      justify-content: center;

      &:disabled {
        opacity: 0.38;
        cursor: not-allowed;
        pointer-events: none;
      }

      &:focus-visible {
        outline: 2px solid var(--sft-accent, #3B82F6);
        outline-offset: 2px;
      }
    }

    .sft-action-btn--reject {
      color: var(--sft-destructive, #EF4444);
      border-color: var(--sft-destructive, #EF4444);
    }

    .sft-action-btn--approve {
      background-color: var(--sft-accent, #3B82F6);
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-approval-card,
      .sft-action-btn {
        transition: none;
      }
    }
  `],
})
export class ApprovalCardComponent implements OnInit, OnChanges, OnDestroy {
  @Input() card: ApprovalCardData | null = null;

  private readonly http = inject(HttpClient);
  private readonly sseService = inject(SseService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly _destroyRef = inject(DestroyRef);
  private readonly _injector = inject(Injector);

  // Motivation gate
  motivationText = '';
  readonly motivationMinLength = MOTIVATION_MIN_LENGTH;
  readonly motivationErrorId = 'motivation-error';

  private readonly _motivation = signal('');
  private readonly _touched = signal(false);
  private readonly _currentStatus = signal<ApprovalStatus>('pending');
  private readonly _isSubmitting = signal(false);
  private readonly _submittingDecision = signal<'APPROVED' | 'REJECTED' | null>(null);
  private _slaInterval: ReturnType<typeof setInterval> | null = null;
  private _slaRemainingSeconds = signal(0);
  private _sseSubscription: Subscription | null = null;

  // ---------------------------------------------------------------------------
  // Computed signals
  // ---------------------------------------------------------------------------

  readonly currentStatus = computed<ApprovalStatus>(() => this._currentStatus());
  readonly isSubmitting = computed<boolean>(() => this._isSubmitting());
  readonly submittingDecision = computed<'APPROVED' | 'REJECTED' | null>(
    () => this._submittingDecision(),
  );

  readonly motivationLength = computed<number>(() => this._motivation().length);

  readonly isMotivationValid = computed<boolean>(
    () => this._motivation().length >= MOTIVATION_MIN_LENGTH,
  );

  readonly showMotivationError = computed<boolean>(
    () => this._touched() && !this.isMotivationValid(),
  );

  readonly slaLabel = computed<string>(() => {
    const secs = this._slaRemainingSeconds();
    if (secs <= 0) return 'SLA scaduto';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    if (m > 0) {
      return `${m} min ${s}s rimasti`;
    }
    return `${s}s rimasti`;
  });

  readonly isSlaWarning = computed<boolean>(() => {
    const card = this.card;
    if (!card) return false;
    return this._slaRemainingSeconds() < card.sla_seconds / 2;
  });

  readonly statusLabel = computed<string>(() => {
    switch (this.currentStatus()) {
      case 'pending':      return 'In attesa';
      case 'approved':     return 'Approvato';
      case 'rejected':     return 'Rifiutato';
      case 'loading':      return 'In caricamento';
      case 'expired_sla':  return 'SLA scaduto';
    }
  });

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  ngOnInit(): void {
    this._initFromCard();
    this._startSlaCountdown();
    this._subscribeSseResolution();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if ('card' in changes) {
      this._initFromCard();
      this._startSlaCountdown();
    }
  }

  ngOnDestroy(): void {
    this._stopSlaCountdown();
    this._sseSubscription?.unsubscribe();
  }

  // ---------------------------------------------------------------------------
  // User interactions
  // ---------------------------------------------------------------------------

  onMotivationChange(value: string): void {
    this._motivation.set(value);
    this._touched.set(true);
  }

  onApprove(): void {
    if (!this.isMotivationValid() || this.isSubmitting()) return;
    this._submitDecision('APPROVED');
  }

  onReject(): void {
    if (!this.isMotivationValid() || this.isSubmitting()) return;

    // WR-02: replaced window.confirm() with MatDialog.
    // - SSR guard: dialog must not be opened on the server (no DOM available).
    // - MatDialog is accessible, testable, and respects the Material design system.
    if (!isPlatformBrowser(this.platformId)) return;

    const dialogRef: MatDialogRef<unknown, boolean> = this.dialog.open(
      RejectConfirmDialogComponent,
      { width: '400px', disableClose: false },
    );
    dialogRef.afterClosed().subscribe((confirmed) => {
      if (confirmed === true) {
        this._submitDecision('REJECTED');
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  private _initFromCard(): void {
    if (!this.card) return;
    this._currentStatus.set(this.card.status);

    if (this.card.status === 'pending') {
      const started = new Date(this.card.sla_started_at).getTime();
      const nowMs = Date.now();
      const elapsedSecs = Math.floor((nowMs - started) / 1000);
      const remaining = Math.max(0, this.card.sla_seconds - elapsedSecs);
      this._slaRemainingSeconds.set(remaining);
    }
  }

  private _startSlaCountdown(): void {
    this._stopSlaCountdown();
    if (this.card?.status !== 'pending') return;

    this._slaInterval = setInterval(() => {
      const remaining = this._slaRemainingSeconds();
      if (remaining <= 0) {
        this._currentStatus.set('expired_sla');
        this._stopSlaCountdown();
        return;
      }
      this._slaRemainingSeconds.set(remaining - 1);
    }, 1_000);
  }

  private _stopSlaCountdown(): void {
    if (this._slaInterval !== null) {
      clearInterval(this._slaInterval);
      this._slaInterval = null;
    }
  }

  private _subscribeSseResolution(): void {
    // WR-04: wire SSE approval_resolved events to update the card state locally.
    // SseService.approvals is a Signal<ApprovalPendingEvent[]> — when an
    // approval_resolved SSE event arrives, SseService removes the entry from the
    // approvals list. We observe that list via toObservable() + takeUntilDestroyed.
    //
    // toObservable() requires an injection context; runInInjectionContext provides
    // it when called from ngOnInit (outside the construction context).
    runInInjectionContext(this._injector, () => {
      this._sseSubscription = toObservable(this.sseService.approvals)
        .pipe(takeUntilDestroyed(this._destroyRef))
        .subscribe((pendingList) => {
          if (!this.card) return;
          if (this._currentStatus() !== 'pending') return;

          // If the card id is no longer in the pending list, it was resolved
          // externally (by another user / SSE approval_resolved event).
          const stillPending = pendingList.some(
            (a) => a.approval_id === this.card!.id,
          );
          if (!stillPending && pendingList.length > 0) {
            // Mark as resolved externally — the next full page reload will show
            // the definitive approved/rejected state from the server.
            this._currentStatus.set('approved');
            this._stopSlaCountdown();
          }
        });
    });
  }

  private _submitDecision(decision: 'APPROVED' | 'REJECTED'): void {
    if (!this.card) return;

    this._isSubmitting.set(true);
    this._submittingDecision.set(decision);

    const body: DecideRequest = {
      decision,
      motivation: this._motivation(),
    };

    this.http
      .post<DecideResponse>(`/v1/approvals/${this.card.id}/decide`, body)
      .subscribe({
        next: (response) => {
          this._currentStatus.set(
            response.status === 'approved' ? 'approved' : 'rejected',
          );
          this._isSubmitting.set(false);
          this._submittingDecision.set(null);
          this._stopSlaCountdown();
        },
        error: (err: HttpErrorResponse) => {
          this._isSubmitting.set(false);
          this._submittingDecision.set(null);

          const msg = err.status === 403
            ? 'Non hai i permessi per questa azione.'
            : 'Si è verificato un errore. Riprova o contatta l\'amministratore.';

          this.snackBar.open(msg, 'OK', {
            duration: 5000,
            panelClass: 'sft-snack-error',
          });
        },
      });
  }
}

// ---------------------------------------------------------------------------
// RejectConfirmDialogComponent — inline dialog for onReject() (WR-02)
// ---------------------------------------------------------------------------
// Replaces the non-SSR-safe window.confirm(). Opened by ApprovalCardComponent
// via MatDialog.open(); closes with true (confirmed) or undefined (cancelled).
// ---------------------------------------------------------------------------

@Component({
  selector: 'sft-reject-confirm-dialog',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatDialogModule],
  template: `
    <h2 mat-dialog-title>Conferma rifiuto</h2>
    <mat-dialog-content>
      <p>
        Stai per rifiutare questa azione AI. La motivazione è obbligatoria e
        verrà registrata nell'audit trail. Vuoi procedere?
      </p>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button [mat-dialog-close]="false">Annulla</button>
      <button
        mat-flat-button
        color="warn"
        [mat-dialog-close]="true"
        data-testid="reject-confirm-btn">
        Rifiuta
      </button>
    </mat-dialog-actions>
  `,
})
export class RejectConfirmDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<RejectConfirmDialogComponent>);
}
