/**
 * Contract tests for ApprovalCardComponent + EvidencePanelComponent.
 *
 * Implements the acceptance contract defined in the Wave 0 scaffold (10-00b).
 * Un-skipped in plan 10-06 as part of the TDD GREEN phase.
 *
 * Architecture decisions (10-CONTEXT.md, HITL-01..07, 10-UI-SPEC §3/§4):
 *   - Renders EvidencePanel sections: input / tool_calls / citations / confidence
 *   - Approve button disabled until motivation textarea >= 10 chars (HITL-07)
 *   - Reject button also disabled until motivation >= 10 chars (HITL-07)
 *   - data-testid attributes required for Playwright E2E (10-UI-SPEC Playwright contract)
 *
 * Required data-testid attributes (10-UI-SPEC, non-exhaustive):
 *   approval-card, evidence-panel, motivation-textarea, approve-btn, reject-btn
 */

import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { FormsModule } from '@angular/forms';
import { TranslocoTestingModule } from '@jsverse/transloco';

import { ApprovalCardComponent, ApprovalCardData } from './approval-card.component';
import { EvidencePanel } from './evidence-panel.component';

const translocoTesting = TranslocoTestingModule.forRoot({
  langs: {
    it: {
      actions: { approve: 'Approva azione', reject: 'Rifiuta', confirm_reject: 'Conferma rifiuto' },
      hitl: {
        motivation_label: 'Motivazione',
        motivation_placeholder: 'Inserisci la motivazione (min. 10 caratteri)...',
        motivation_error: 'La motivazione deve contenere almeno 10 caratteri.',
        destructive_confirm: 'Stai per rifiutare questa azione AI.',
      },
      queue: { cancel: 'Annulla' },
      approval: {
        input_section: 'Input agente',
        tool_calls_section: 'Tool call',
        rag_citations_section: 'Citazioni RAG',
        confidence_section: 'Confidenza',
        acl_restricted: 'Contenuto riservato',
        tool_result_label: 'Risultato:',
        confidence_low: 'Bassa confidenza',
        confidence_medium: 'Confidenza media',
        confidence_high: 'Alta confidenza',
      },
      empty_state: { tool_calls: 'Nessuna tool call', rag_citations: 'Nessuna citazione RAG' },
    },
  },
  translocoConfig: { defaultLang: 'it', availableLangs: ['it'] },
  preloadLangs: true,
});

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

const mockEvidencePanel: EvidencePanel = {
  input: { machine_id: 'LOOM-01', anomaly_score: 0.87 },
  tool_calls_log: [
    { tool_name: 'fetch_sensor_data', args: { sensor_id: 'S01' }, result: { value: 42 }, duration_ms: 120 },
  ],
  rag_citations: [
    {
      source_uri: 'https://docs.mantis.it/sop/loom-maintenance.pdf',
      page: 12,
      lang: 'it',
      chunk_preview: 'Procedura di manutenzione preventiva per telai.',
      relevance_score: 0.92,
      acl_level: 'public',
    },
  ],
  confidence: 0.85,
  agent_name: 'MaintenanceCoach',
  cluster: 'maintenance',
  action_type: 'MAINTENANCE_ALERT',
  timestamp: '2026-05-24T10:00:00Z',
};

const mockPendingCard: ApprovalCardData = {
  id: 'appr-001',
  status: 'pending',
  agent_name: 'MaintenanceCoach',
  cluster: 'maintenance',
  action_type: 'MAINTENANCE_ALERT',
  escalation_tier: 'Operator',
  action_summary: 'Arresto preventivo telaio LOOM-01 raccomandato.',
  sla_seconds: 300,
  sla_started_at: new Date(Date.now() - 30_000).toISOString(),
  evidence_panel: mockEvidencePanel,
};

const mockApprovedCard: ApprovalCardData = {
  ...mockPendingCard,
  id: 'appr-002',
  status: 'approved',
  motivation: 'Approvato dopo analisi del pannello evidenze.',
};

// ---------------------------------------------------------------------------
// Setup — shared beforeEach to avoid compileComponents timeout per-test
// ---------------------------------------------------------------------------

describe('ApprovalCardComponent', () => {
  let fixture: ComponentFixture<ApprovalCardComponent>;
  let component: ApprovalCardComponent;
  let el: HTMLElement;

  function setupComponent(card: ApprovalCardData): void {
    component = fixture.componentInstance;
    component.card = card;
    fixture.detectChanges();
    el = fixture.nativeElement as HTMLElement;
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        NoopAnimationsModule,
        HttpClientTestingModule,
        FormsModule,
        ApprovalCardComponent,
        translocoTesting,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ApprovalCardComponent);
  });

  afterEach(() => {
    fixture.destroy();
  });

  // ---------------------------------------------------------------------------
  // data-testid attributes — Playwright E2E contract
  // ---------------------------------------------------------------------------

  it('renders with data-testid="approval-card" on the host element', () => {
    setupComponent(mockPendingCard);
    expect(el.querySelector('[data-testid="approval-card"]')).toBeTruthy();
  });

  it('renders evidence-panel element with data-testid="evidence-panel"', () => {
    setupComponent(mockPendingCard);
    expect(el.querySelector('[data-testid="evidence-panel"]')).toBeTruthy();
  });

  it('renders motivation-textarea with data-testid="motivation-textarea"', () => {
    setupComponent(mockPendingCard);
    expect(el.querySelector('[data-testid="motivation-textarea"]')).toBeTruthy();
  });

  it('renders approve-btn with data-testid="approve-btn"', () => {
    setupComponent(mockPendingCard);
    expect(el.querySelector('[data-testid="approve-btn"]')).toBeTruthy();
  });

  it('renders reject-btn with data-testid="reject-btn"', () => {
    setupComponent(mockPendingCard);
    expect(el.querySelector('[data-testid="reject-btn"]')).toBeTruthy();
  });

  // ---------------------------------------------------------------------------
  // HITL-07: approve button disabled until motivation >= 10 chars
  // ---------------------------------------------------------------------------

  it('approve-btn is disabled when motivation textarea is empty', () => {
    setupComponent(mockPendingCard);
    const approveBtn = el.querySelector<HTMLButtonElement>('[data-testid="approve-btn"]');
    expect(approveBtn).toBeTruthy();
    expect(approveBtn!.disabled).toBe(true);
  });

  it('approve-btn is disabled when motivation has fewer than 10 characters', fakeAsync(() => {
    setupComponent(mockPendingCard);

    component.onMotivationChange('Short');
    tick();
    fixture.detectChanges();

    const approveBtn = el.querySelector<HTMLButtonElement>('[data-testid="approve-btn"]');
    expect(approveBtn!.disabled).toBe(true);
  }));

  it('approve-btn is enabled when motivation has at least 10 characters', fakeAsync(() => {
    setupComponent(mockPendingCard);

    const longMotivation = 'Motivazione valida per approvare';
    component.onMotivationChange(longMotivation);
    tick();
    fixture.detectChanges();

    const approveBtn = el.querySelector<HTMLButtonElement>('[data-testid="approve-btn"]');
    expect(approveBtn!.disabled).toBe(false);
  }));

  it('reject-btn is also disabled until motivation >= 10 chars (HITL-07)', () => {
    setupComponent(mockPendingCard);
    const rejectBtn = el.querySelector<HTMLButtonElement>('[data-testid="reject-btn"]');
    expect(rejectBtn).toBeTruthy();
    expect(rejectBtn!.disabled).toBe(true);
  });

  // ---------------------------------------------------------------------------
  // EvidencePanel rendering (HITL-06, UI-SPEC §4)
  // ---------------------------------------------------------------------------

  it('renders all 4 evidence panel sections: input, tool_calls, citations, confidence', () => {
    setupComponent(mockPendingCard);
    const sections = el.querySelectorAll('[data-testid^="evidence-section-"]');
    const names = Array.from(sections).map((s) => s.getAttribute('data-testid'));

    expect(names).toContain('evidence-section-input');
    expect(names).toContain('evidence-section-tool-calls');
    expect(names).toContain('evidence-section-citations');
    expect(names).toContain('evidence-section-confidence');
  });

  it('evidence panel shows "Nessuna tool call" when tool_calls_log is empty', () => {
    const cardWithEmptyToolCalls: ApprovalCardData = {
      ...mockPendingCard,
      evidence_panel: { ...mockEvidencePanel, tool_calls_log: [] },
    };
    setupComponent(cardWithEmptyToolCalls);
    expect(el.textContent).toContain('Nessuna tool call');
  });

  it('evidence panel shows "Nessuna citazione RAG" when rag_citations is empty', () => {
    const cardWithEmptyCitations: ApprovalCardData = {
      ...mockPendingCard,
      evidence_panel: { ...mockEvidencePanel, rag_citations: [] },
    };
    setupComponent(cardWithEmptyCitations);
    expect(el.textContent).toContain('Nessuna citazione RAG');
  });

  it('confidence < 0.5 shows "Bassa confidenza" badge (red)', () => {
    const cardLowConf: ApprovalCardData = {
      ...mockPendingCard,
      evidence_panel: { ...mockEvidencePanel, confidence: 0.3 },
    };
    setupComponent(cardLowConf);
    expect(el.textContent).toContain('Bassa confidenza');
  });

  it('confidence >= 0.8 shows "Alta confidenza" badge (green)', () => {
    const cardHighConf: ApprovalCardData = {
      ...mockPendingCard,
      evidence_panel: { ...mockEvidencePanel, confidence: 0.85 },
    };
    setupComponent(cardHighConf);
    expect(el.textContent).toContain('Alta confidenza');
  });

  it('restricted ACL citations show "Contenuto riservato" instead of chunk_preview', () => {
    const restrictedPreview = 'Questo è contenuto classificato top secret.';
    const cardRestricted: ApprovalCardData = {
      ...mockPendingCard,
      evidence_panel: {
        ...mockEvidencePanel,
        rag_citations: [
          {
            source_uri: 'https://internal.mantis.it/restricted/doc.pdf',
            lang: 'it',
            chunk_preview: restrictedPreview,
            relevance_score: 0.75,
            acl_level: 'restricted',
          },
        ],
      },
    };
    setupComponent(cardRestricted);
    expect(el.textContent).toContain('Contenuto riservato');
    expect(el.textContent).not.toContain(restrictedPreview);
  });

  // ---------------------------------------------------------------------------
  // Card status states (10-UI-SPEC §3 stati della card)
  // ---------------------------------------------------------------------------

  it('approved card hides ActionBar (approve/reject buttons not rendered)', () => {
    setupComponent(mockApprovedCard);
    expect(el.querySelector('[data-testid="approve-btn"]')).toBeFalsy();
    expect(el.querySelector('[data-testid="reject-btn"]')).toBeFalsy();
  });

  it('pending card shows ActionBar with both approve and reject buttons', () => {
    setupComponent(mockPendingCard);
    expect(el.querySelector('[data-testid="approve-btn"]')).toBeTruthy();
    expect(el.querySelector('[data-testid="reject-btn"]')).toBeTruthy();
  });
});
