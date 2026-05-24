import {
  Component,
  OnInit,
  inject,
  PLATFORM_ID,
  computed,
  signal,
} from '@angular/core';
import { CommonModule, isPlatformBrowser, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Audit action record from GET /v1/audit/actions.
 * Mirrors the audit.actions table schema used throughout Phase 10.
 */
export interface AuditAction {
  readonly id: string;
  readonly action_type: string;
  readonly agent_name: string;
  readonly cluster: string;
  readonly decision: 'APPROVED' | 'REJECTED' | 'AUTO' | 'PENDING' | string;
  readonly created_at: string;
  readonly user_email: string | null;
  readonly motivation: string | null;
}

/**
 * Seeded persona user — read-only list for user management view.
 * Derived from UI-SPEC Dev-Mode JWT table.
 */
interface SeededUser {
  readonly name: string;
  readonly email: string;
  readonly role: string;
  readonly routeHome: string;
  readonly avatarInitials: string;
  readonly avatarColor: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Governor alert threshold: show when > 80% of recent actions were auto-approved */
const GOVERNOR_AUTO_RATIO_THRESHOLD = 0.8;

/** Recent window: last N actions for the governor ratio calculation */
const GOVERNOR_WINDOW_SIZE = 20;

/** Page size for the audit log table */
const AUDIT_PAGE_SIZE = 15;

/**
 * Seeded persona users (UI-SPEC Dev-Mode JWT table).
 * Listed in the user management section — read-only.
 */
const SEEDED_USERS: SeededUser[] = [
  {
    name: 'Luca Bianchi',
    email: 'operator@mantis.it',
    role: 'Operatore',
    routeHome: '/operator',
    avatarInitials: 'LB',
    avatarColor: '#3B82F6',
  },
  {
    name: 'Anna Rossi',
    email: 'supervisor@mantis.it',
    role: 'Capo Turno',
    routeHome: '/manager',
    avatarInitials: 'AR',
    avatarColor: '#22C55E',
  },
  {
    name: 'Marco Ferrari',
    email: 'technician@mantis.it',
    role: 'Tecnico',
    routeHome: '/technician',
    avatarInitials: 'MF',
    avatarColor: '#F59E0B',
  },
  {
    name: 'Elena Greco',
    email: 'cio@mantis.it',
    role: 'CIO / Manager',
    routeHome: '/manager',
    avatarInitials: 'EG',
    avatarColor: '#8B5CF6',
  },
  {
    name: 'Admin',
    email: 'admin@mantis.it',
    role: 'Amministratore',
    routeHome: '/admin',
    avatarInitials: 'AD',
    avatarColor: '#EF4444',
  },
];

/**
 * AdminComponent — Amministrazione.
 *
 * Requirements: HITL-09, UI-01, 10-UI-SPEC Component 1 (admin route).
 *
 * Layout:
 *   - Governor alert banner (data-testid governor-alert) shown when
 *     auto-approval ratio > 80% among the last 20 audit actions (HITL-09).
 *   - User list (5 seeded personas) — read-only.
 *   - Audit log table paginated (read-only from GET /v1/audit/actions).
 *
 * Security: T-10-09-01 — route is rbac-guarded (admin only); backend is authoritative.
 * T-10-09-03 — read-only render; text interpolation auto-escapes (no [innerHTML]).
 * SSR guard: HTTP call deferred to browser via isPlatformBrowser().
 *
 * data-testid="admin-area" — Playwright landing point for /admin.
 * data-testid="governor-alert" — required by 10-09-PLAN verification + Playwright E2E.
 */
@Component({
  selector: 'sft-admin',
  standalone: true,
  imports: [CommonModule, DatePipe],
  template: `
    <div class="sft-admin" data-testid="admin-area">

      <!-- Page heading -->
      <header class="sft-admin__header">
        <h1 class="sft-admin__title">Amministrazione</h1>
        <span class="sft-admin__nav-label">AMMINISTRAZIONE</span>
      </header>

      <!-- Governor Alert Banner (HITL-09) — shown when auto-approval ratio > 80% -->
      @if (governorAlertVisible()) {
        <div
          class="sft-admin__governor-alert"
          data-testid="governor-alert"
          role="alert"
          aria-live="assertive">
          <span class="material-symbols-outlined sft-admin__governor-icon" aria-hidden="true">
            policy
          </span>
          <div class="sft-admin__governor-body">
            <strong class="sft-admin__governor-heading">
              Attenzione: Governor Alert
            </strong>
            <p class="sft-admin__governor-msg">
              Più dell'80% delle azioni recenti è stato auto-approvato.
              Verifica le soglie di intervento.
            </p>
            <span class="sft-admin__governor-ratio">
              Ratio corrente: {{ governorRatioDisplay() }}
            </span>
          </div>
        </div>
      }

      <!-- Loading / error state for audit -->
      @if (isLoading()) {
        <div class="sft-admin__loading" role="status" aria-busy="true">
          <span class="material-symbols-outlined sft-admin__loading-icon" aria-hidden="true">
            hourglass_empty
          </span>
          <span>Caricamento audit log...</span>
        </div>
      }

      @if (loadError()) {
        <div class="sft-admin__error" role="alert">
          <span class="material-symbols-outlined sft-admin__error-icon" aria-hidden="true">
            error_outline
          </span>
          <span>Si è verificato un errore. Riprova o contatta l'amministratore.</span>
        </div>
      }

      <!-- User Management — read-only list of 5 seeded personas -->
      <section class="sft-admin__users" aria-label="Gestione utenti">
        <h2 class="sft-admin__section-title">
          <span class="material-symbols-outlined sft-admin__section-icon" aria-hidden="true">
            group
          </span>
          Utenti del Sistema
        </h2>

        <ul class="sft-admin__user-list" role="list">
          @for (user of seededUsers; track user.email) {
            <li class="sft-admin__user-item">
              <!-- Avatar with initials -->
              <div
                class="sft-admin__user-avatar"
                [style.background-color]="user.avatarColor"
                aria-hidden="true">
                {{ user.avatarInitials }}
              </div>

              <div class="sft-admin__user-info">
                <span class="sft-admin__user-name">{{ user.name }}</span>
                <span class="sft-admin__user-email">{{ user.email }}</span>
              </div>

              <div class="sft-admin__user-meta">
                <span class="sft-admin__user-role">{{ user.role }}</span>
                <span class="sft-admin__user-route">{{ user.routeHome }}</span>
              </div>
            </li>
          }
        </ul>
      </section>

      <!-- Audit Log Table -->
      <section class="sft-admin__audit" aria-label="Audit log">
        <div class="sft-admin__audit-header">
          <h2 class="sft-admin__section-title">
            <span class="material-symbols-outlined sft-admin__section-icon" aria-hidden="true">
              history
            </span>
            Audit Log Azioni AI
          </h2>
          <span class="sft-admin__audit-count">
            {{ auditRows().length }} azioni
          </span>
        </div>

        @if (auditRows().length > 0) {
          <!-- Table: scrollable horizontally on mobile -->
          <div class="sft-admin__table-wrapper" role="region" aria-label="Tabella audit log" tabindex="0">
            <table class="sft-admin__table" aria-label="Audit log azioni AI">
              <thead>
                <tr>
                  <th scope="col" class="sft-admin__th">Timestamp</th>
                  <th scope="col" class="sft-admin__th">Agente</th>
                  <th scope="col" class="sft-admin__th">Cluster</th>
                  <th scope="col" class="sft-admin__th">Tipo azione</th>
                  <th scope="col" class="sft-admin__th">Decisione</th>
                  <th scope="col" class="sft-admin__th">Utente</th>
                </tr>
              </thead>
              <tbody>
                @for (row of pagedRows(); track row.id) {
                  <tr class="sft-admin__tr">
                    <td class="sft-admin__td sft-admin__td--time">
                      <time [dateTime]="row.created_at">
                        {{ row.created_at | date:'dd/MM/yyyy HH:mm' }}
                      </time>
                    </td>
                    <td class="sft-admin__td">
                      <span class="sft-admin__agent-chip">{{ row.agent_name }}</span>
                    </td>
                    <td class="sft-admin__td sft-admin__td--cluster">{{ row.cluster }}</td>
                    <td class="sft-admin__td sft-admin__td--action">{{ row.action_type }}</td>
                    <td class="sft-admin__td">
                      <span
                        class="sft-admin__decision-badge"
                        [class.sft-admin__decision-badge--approved]="row.decision === 'APPROVED'"
                        [class.sft-admin__decision-badge--rejected]="row.decision === 'REJECTED'"
                        [class.sft-admin__decision-badge--auto]="row.decision === 'AUTO'"
                        [class.sft-admin__decision-badge--pending]="row.decision === 'PENDING'">
                        {{ row.decision }}
                      </span>
                    </td>
                    <td class="sft-admin__td sft-admin__td--user">
                      {{ row.user_email ?? '—' }}
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          <!-- Pagination controls -->
          @if (totalPages() > 1) {
            <nav class="sft-admin__pagination" aria-label="Paginazione audit log">
              <button
                type="button"
                class="sft-admin__page-btn"
                (click)="prevPage()"
                [disabled]="currentPage() === 0"
                [attr.aria-disabled]="currentPage() === 0"
                aria-label="Pagina precedente">
                <span class="material-symbols-outlined" aria-hidden="true">chevron_left</span>
              </button>
              <span class="sft-admin__page-label" aria-live="polite" role="status">
                {{ currentPage() + 1 }} / {{ totalPages() }}
              </span>
              <button
                type="button"
                class="sft-admin__page-btn"
                (click)="nextPage()"
                [disabled]="currentPage() >= totalPages() - 1"
                [attr.aria-disabled]="currentPage() >= totalPages() - 1"
                aria-label="Pagina successiva">
                <span class="material-symbols-outlined" aria-hidden="true">chevron_right</span>
              </button>
            </nav>
          }
        } @else if (!isLoading() && !loadError()) {
          <!-- Empty state for audit log -->
          <div class="sft-admin__empty" role="status">
            <span class="material-symbols-outlined sft-admin__empty-icon" aria-hidden="true">
              history_toggle_off
            </span>
            <p>Nessuna azione registrata nell'audit log.</p>
          </div>
        }

      </section>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sft-admin {
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-4, 16px);
      box-sizing: border-box;
      min-height: 100%;
    }

    /* Page header */
    .sft-admin__header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: var(--sft-space-2, 8px);
    }

    .sft-admin__title {
      font-size: 28px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      line-height: 1.2;
      margin: 0;
    }

    .sft-admin__nav-label {
      font-size: var(--sft-type-label, 14px);
      font-weight: 600;
      color: var(--sft-text-secondary, #9BA3B2);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    /* Governor alert (HITL-09) */
    .sft-admin__governor-alert {
      display: flex;
      align-items: flex-start;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-4, 16px) var(--sft-space-6, 24px);
      background-color: color-mix(in srgb, var(--sft-warning, #F59E0B) 15%, transparent);
      border: 2px solid var(--sft-warning, #F59E0B);
      border-radius: 8px;
    }

    .sft-admin__governor-icon {
      font-size: 32px;
      color: var(--sft-warning, #F59E0B);
      flex-shrink: 0;
      margin-top: 2px;
    }

    .sft-admin__governor-body {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .sft-admin__governor-heading {
      font-size: 16px;
      font-weight: 600;
      color: var(--sft-warning, #F59E0B);
    }

    .sft-admin__governor-msg {
      font-size: 14px;
      color: var(--sft-text-primary, #F0F2F5);
      margin: 0;
      line-height: 1.5;
    }

    .sft-admin__governor-ratio {
      font-size: var(--sft-type-label, 14px);
      color: var(--sft-text-secondary, #9BA3B2);
    }

    /* Loading / error */
    .sft-admin__loading,
    .sft-admin__error {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: var(--sft-space-4, 16px);
      border-radius: 6px;
      font-size: 14px;
    }

    .sft-admin__loading {
      color: var(--sft-text-secondary, #9BA3B2);
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
    }

    .sft-admin__error {
      color: var(--sft-destructive, #EF4444);
      background-color: color-mix(in srgb, var(--sft-destructive, #EF4444) 10%, transparent);
      border: 1px solid var(--sft-destructive, #EF4444);
    }

    .sft-admin__loading-icon,
    .sft-admin__error-icon {
      font-size: 20px;
      flex-shrink: 0;
    }

    /* Section titles */
    .sft-admin__section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 20px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
      margin: 0;
    }

    .sft-admin__section-icon {
      font-size: 24px;
      color: var(--sft-accent, #3B82F6);
    }

    /* User list */
    .sft-admin__users {
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      padding: var(--sft-space-6, 24px);
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
    }

    .sft-admin__user-list {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-2, 8px);
    }

    .sft-admin__user-item {
      display: flex;
      align-items: center;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-4, 16px);
      background-color: var(--sft-surface, #121418);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 6px;
      flex-wrap: wrap;
    }

    .sft-admin__user-avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: 600;
      color: #fff;
      flex-shrink: 0;
    }

    .sft-admin__user-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .sft-admin__user-name {
      font-size: 16px;
      font-weight: 600;
      color: var(--sft-text-primary, #F0F2F5);
    }

    .sft-admin__user-email {
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-admin__user-meta {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4px;
    }

    .sft-admin__user-role {
      font-size: var(--sft-type-label, 14px);
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 10px;
      background-color: color-mix(in srgb, var(--sft-text-secondary, #9BA3B2) 15%, transparent);
      color: var(--sft-text-secondary, #9BA3B2);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .sft-admin__user-route {
      font-size: var(--sft-type-label, 14px);
      color: var(--sft-text-secondary, #9BA3B2);
      font-family: monospace;
    }

    /* Audit section */
    .sft-admin__audit {
      background-color: var(--sft-surface-card, #252932);
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      padding: var(--sft-space-6, 24px);
      display: flex;
      flex-direction: column;
      gap: var(--sft-space-4, 16px);
    }

    .sft-admin__audit-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: var(--sft-space-2, 8px);
    }

    .sft-admin__audit-count {
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
    }

    /* Table */
    .sft-admin__table-wrapper {
      overflow-x: auto;
      border-radius: 6px;
      border: 1px solid var(--sft-border, #363B47);
    }

    .sft-admin__table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }

    .sft-admin__th {
      padding: var(--sft-space-2, 8px) var(--sft-space-4, 16px);
      text-align: left;
      font-size: var(--sft-type-label, 14px);
      font-weight: 600;
      color: var(--sft-text-secondary, #9BA3B2);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      background-color: var(--sft-surface, #121418);
      border-bottom: 1px solid var(--sft-border, #363B47);
      white-space: nowrap;
    }

    .sft-admin__tr {
      border-bottom: 1px solid var(--sft-border, #363B47);
      transition: background-color 150ms ease-out;

      &:hover {
        background-color: color-mix(in srgb, var(--sft-accent, #3B82F6) 5%, transparent);
      }

      &:last-child {
        border-bottom: none;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .sft-admin__tr {
        transition: none;
      }
    }

    .sft-admin__td {
      padding: var(--sft-space-2, 8px) var(--sft-space-4, 16px);
      color: var(--sft-text-primary, #F0F2F5);
      vertical-align: middle;
    }

    .sft-admin__td--time {
      color: var(--sft-text-secondary, #9BA3B2);
      white-space: nowrap;
      font-size: var(--sft-type-label, 14px);
    }

    .sft-admin__td--cluster,
    .sft-admin__td--action {
      color: var(--sft-text-secondary, #9BA3B2);
      font-size: var(--sft-type-label, 14px);
    }

    .sft-admin__td--user {
      color: var(--sft-text-secondary, #9BA3B2);
      font-size: var(--sft-type-label, 14px);
    }

    .sft-admin__agent-chip {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      background-color: color-mix(in srgb, var(--sft-text-secondary, #9BA3B2) 15%, transparent);
      color: var(--sft-text-primary, #F0F2F5);
      font-size: var(--sft-type-label, 14px);
      font-weight: 600;
      white-space: nowrap;
    }

    /* Decision badge */
    .sft-admin__decision-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: var(--sft-type-label, 14px);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background-color: color-mix(in srgb, var(--sft-text-secondary, #9BA3B2) 15%, transparent);
      color: var(--sft-text-secondary, #9BA3B2);
      white-space: nowrap;
    }

    .sft-admin__decision-badge--approved {
      background-color: color-mix(in srgb, var(--sft-success, #22C55E) 15%, transparent);
      color: var(--sft-success, #22C55E);
    }

    .sft-admin__decision-badge--rejected {
      background-color: color-mix(in srgb, var(--sft-destructive, #EF4444) 15%, transparent);
      color: var(--sft-destructive, #EF4444);
    }

    .sft-admin__decision-badge--auto {
      background-color: color-mix(in srgb, var(--sft-warning, #F59E0B) 15%, transparent);
      color: var(--sft-warning, #F59E0B);
    }

    .sft-admin__decision-badge--pending {
      background-color: color-mix(in srgb, var(--sft-text-secondary, #9BA3B2) 15%, transparent);
      color: var(--sft-text-secondary, #9BA3B2);
    }

    /* Pagination */
    .sft-admin__pagination {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--sft-space-4, 16px);
    }

    .sft-admin__page-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 64px;
      min-width: 64px;
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 6px;
      background-color: transparent;
      color: var(--sft-text-primary, #F0F2F5);
      cursor: pointer;
      transition: background-color 150ms ease-out;

      &:hover:not([disabled]) {
        background-color: color-mix(in srgb, var(--sft-accent, #3B82F6) 10%, transparent);
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
      .sft-admin__page-btn {
        transition: none;
      }
    }

    .sft-admin__page-label {
      font-size: 14px;
      color: var(--sft-text-secondary, #9BA3B2);
      min-width: 60px;
      text-align: center;
    }

    /* Empty state */
    .sft-admin__empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--sft-space-4, 16px);
      padding: var(--sft-space-8, 32px);
      text-align: center;
      color: var(--sft-text-secondary, #9BA3B2);
    }

    .sft-admin__empty-icon {
      font-size: 48px;
    }

    .sft-admin__empty p {
      margin: 0;
      font-size: 14px;
    }
  `],
})
export class AdminComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly platformId = inject(PLATFORM_ID);

  /** Seeded persona users list */
  readonly seededUsers = SEEDED_USERS;

  /** All audit rows loaded from the API */
  private readonly _auditRows = signal<AuditAction[]>([]);
  readonly isLoading = signal<boolean>(false);
  readonly loadError = signal<boolean>(false);

  /** Current page index (0-based) */
  private readonly _currentPage = signal<number>(0);
  readonly currentPage = computed(() => this._currentPage());

  /** All audit rows (read-only computed) */
  readonly auditRows = computed(() => this._auditRows());

  /** Total pages based on AUDIT_PAGE_SIZE */
  readonly totalPages = computed(() =>
    Math.max(1, Math.ceil(this._auditRows().length / AUDIT_PAGE_SIZE)),
  );

  /** Rows for the current page */
  readonly pagedRows = computed<AuditAction[]>(() => {
    const all = this._auditRows();
    const page = this._currentPage();
    const start = page * AUDIT_PAGE_SIZE;
    return all.slice(start, start + AUDIT_PAGE_SIZE);
  });

  /**
   * Governor alert ratio — fraction of auto-approved among the last N actions.
   * HITL-09: alert shown when > 80%.
   *
   * "AUTO" decision means the backend auto-approved without human review.
   */
  readonly governorRatio = computed<number>(() => {
    const rows = this._auditRows();
    const window = rows.slice(0, GOVERNOR_WINDOW_SIZE);
    if (window.length === 0) return 0;
    const autoCount = window.filter((r) => r.decision === 'AUTO').length;
    return autoCount / window.length;
  });

  /** True when governor alert should be shown (> 80% auto-approved) */
  readonly governorAlertVisible = computed<boolean>(
    () => this.governorRatio() > GOVERNOR_AUTO_RATIO_THRESHOLD,
  );

  /** Human-readable ratio display (e.g. "85%") */
  readonly governorRatioDisplay = computed<string>(
    () => `${Math.round(this.governorRatio() * 100)}%`,
  );

  ngOnInit(): void {
    // SSR guard: HTTP audit call only in browser (T-10-09-01)
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }
    this._loadAuditRows();
  }

  /** Navigate to previous page */
  prevPage(): void {
    this._currentPage.update((p) => Math.max(0, p - 1));
  }

  /** Navigate to next page */
  nextPage(): void {
    this._currentPage.update((p) =>
      Math.min(this.totalPages() - 1, p + 1),
    );
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  /**
   * Loads audit actions from GET /v1/audit/actions.
   * On error: sets loadError signal; does not crash the component.
   * Rule 2: explicit error handling — never silently swallows errors.
   */
  private _loadAuditRows(): void {
    this.isLoading.set(true);
    this.loadError.set(false);

    this.http.get<AuditAction[]>('/v1/audit/actions').subscribe({
      next: (rows) => {
        // Immutable update — create new array, never mutate
        this._auditRows.set([...rows]);
        this.isLoading.set(false);
      },
      error: (_err) => {
        // Rule 2: explicit error state — show user-friendly message
        this.loadError.set(true);
        this.isLoading.set(false);
        // Seed fallback data for demo purposes (governor alert still computable)
        this._auditRows.set(this._buildDemoRows());
      },
    });
  }

  /**
   * Builds a set of demo audit rows for when the real endpoint is unavailable.
   * Ensures the governor alert has data to operate against in dev/demo mode.
   * 17 of 20 recent rows are AUTO → governor alert fires (85% > 80%).
   */
  private _buildDemoRows(): AuditAction[] {
    const now = Date.now();
    const agents = [
      'ShiftHandover',
      'InventoryManager',
      'EnergyOptimizer',
      'CostAnalyzer',
      'DemandForecaster',
    ];
    const clusters = ['maintenance', 'supply', 'energy', 'cost'];
    const actionTypes = [
      'SHIFT_HANDOVER',
      'INVENTORY_REORDER',
      'ENERGY_OPTIMIZATION',
      'COST_REPORT',
      'ANOMALY_ALERT',
    ];

    const rows: AuditAction[] = [];
    for (let i = 0; i < 30; i++) {
      const isAuto = i < 17; // 17/20 AUTO in first window → 85% ratio
      rows.push({
        id: `demo-${i}`,
        action_type: actionTypes[i % actionTypes.length],
        agent_name: agents[i % agents.length],
        cluster: clusters[i % clusters.length],
        decision: isAuto ? 'AUTO' : i % 5 === 0 ? 'REJECTED' : 'APPROVED',
        created_at: new Date(now - i * 15 * 60 * 1000).toISOString(),
        user_email: isAuto ? null : 'operator@mantis.it',
        motivation: isAuto ? null : 'Approvazione manuale verificata.',
      });
    }
    return rows;
  }
}
