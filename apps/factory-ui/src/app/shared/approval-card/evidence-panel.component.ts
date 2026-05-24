import {
  Component,
  Input,
  computed,
  signal,
  OnChanges,
  SimpleChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';

// ---------------------------------------------------------------------------
// Evidence Panel — TypeScript Interfaces (10-UI-SPEC Component 4)
// ---------------------------------------------------------------------------

export interface ToolCallEntry {
  tool_name: string;
  args: Record<string, unknown>;
  result: unknown;
  duration_ms?: number;
}

export interface RagCitation {
  source_uri: string;
  page?: number;
  version?: string;
  lang: 'it' | 'en';
  chunk_preview: string;  // max 200 chars
  relevance_score: number; // 0.0 – 1.0
  acl_level: 'public' | 'internal' | 'restricted';
}

export interface EvidencePanel {
  input: Record<string, unknown>;
  tool_calls_log: ToolCallEntry[];
  rag_citations: RagCitation[];
  confidence: number; // 0.0 – 1.0
  agent_name: string;
  cluster: string;
  action_type: string;
  timestamp: string;  // ISO 8601
}

/** Confidence threshold mapping (10-UI-SPEC §4) */
export type ConfidenceLevel = 'low' | 'medium' | 'high';

function getConfidenceLevel(confidence: number): ConfidenceLevel {
  if (confidence < 0.5) return 'low';
  if (confidence < 0.8) return 'medium';
  return 'high';
}

function isValidUrl(uri: string): boolean {
  try {
    const url = new URL(uri);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * EvidencePanelComponent — renders agent evidence_panel JSONB inline.
 *
 * Requirements: HITL-06, UI-03, 10-UI-SPEC Component 4.
 *   - data-testid="evidence-panel"
 *   - Accordions for each section: input / tool_calls / citations / confidence
 *   - data-testid="evidence-section-input|tool-calls|citations|confidence"
 *   - Rendering rules per UI-SPEC §4 table
 *   - ACL restricted: hides chunk_preview (T-10-06-03)
 *   - source_uri: link only if valid URL (T-10-06-02)
 *   - No innerHTML — all interpolation via Angular textContent binding (T-10-06-02)
 *   - max-height 480px with internal scroll
 */
@Component({
  selector: 'sft-evidence-panel',
  standalone: true,
  imports: [
    CommonModule,
    MatExpansionModule,
    MatProgressBarModule,
    MatChipsModule,
  ],
  template: `
    <div
      class="sft-evidence-panel"
      data-testid="evidence-panel"
      [attr.aria-label]="'Pannello evidenze: ' + (evidence?.agent_name ?? 'agente')">

      <mat-accordion class="sft-evidence-accordion" multi>

        <!-- Input Section -->
        <mat-expansion-panel
          data-testid="evidence-section-input"
          class="sft-evidence-section">
          <mat-expansion-panel-header>
            <mat-panel-title class="sft-type-label">Input agente</mat-panel-title>
          </mat-expansion-panel-header>
          <div class="sft-evidence-input-wrap">
            <pre class="sft-evidence-pre"><code class="sft-evidence-code">{{ inputJson() }}</code></pre>
          </div>
        </mat-expansion-panel>

        <!-- Tool Calls Section -->
        <mat-expansion-panel
          data-testid="evidence-section-tool-calls"
          class="sft-evidence-section">
          <mat-expansion-panel-header>
            <mat-panel-title class="sft-type-label">Tool call</mat-panel-title>
          </mat-expansion-panel-header>
          @if (hasToolCalls()) {
            <div class="sft-evidence-tool-calls">
              @for (call of evidence?.tool_calls_log ?? []; track call.tool_name; let i = $index) {
                <div class="sft-evidence-tool-call">
                  <div class="sft-type-label sft-evidence-tool-name">
                    {{ call.tool_name }}
                    @if (call.duration_ms !== undefined) {
                      <span class="sft-evidence-tool-duration">{{ call.duration_ms }}ms</span>
                    }
                  </div>
                  <pre class="sft-evidence-pre sft-evidence-pre--compact">
                    <code class="sft-evidence-code">{{ formatJson(call.args) }}</code>
                  </pre>
                  <div class="sft-type-label sft-evidence-tool-result-label">Risultato:</div>
                  <pre class="sft-evidence-pre sft-evidence-pre--compact">
                    <code class="sft-evidence-code">{{ formatJson(call.result) }}</code>
                  </pre>
                </div>
              }
            </div>
          } @else {
            <p class="sft-evidence-empty">Nessuna tool call</p>
          }
        </mat-expansion-panel>

        <!-- RAG Citations Section -->
        <mat-expansion-panel
          data-testid="evidence-section-citations"
          class="sft-evidence-section">
          <mat-expansion-panel-header>
            <mat-panel-title class="sft-type-label">Citazioni RAG</mat-panel-title>
          </mat-expansion-panel-header>
          @if (hasRagCitations()) {
            <div class="sft-evidence-citations">
              @for (cite of evidence?.rag_citations ?? []; track cite.source_uri; let i = $index) {
                <div class="sft-evidence-citation">
                  <div class="sft-evidence-citation-header">
                    @if (isValidUri(cite.source_uri)) {
                      <a
                        [href]="cite.source_uri"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="sft-evidence-citation-link">
                        {{ cite.source_uri }}
                      </a>
                    } @else {
                      <span class="sft-evidence-citation-uri">{{ cite.source_uri }}</span>
                    }
                    @if (cite.page !== undefined) {
                      <span class="sft-type-label sft-evidence-citation-page">p. {{ cite.page }}</span>
                    }
                    <span class="sft-type-label sft-evidence-citation-lang">{{ cite.lang.toUpperCase() }}</span>
                    <span class="sft-type-label sft-evidence-citation-score">
                      {{ (cite.relevance_score * 100).toFixed(0) }}%
                    </span>
                  </div>
                  @if (cite.acl_level === 'restricted') {
                    <p class="sft-evidence-restricted">Contenuto riservato</p>
                  } @else {
                    <p class="sft-evidence-chunk">{{ cite.chunk_preview }}</p>
                  }
                </div>
              }
            </div>
          } @else {
            <p class="sft-evidence-empty">Nessuna citazione RAG</p>
          }
        </mat-expansion-panel>

        <!-- Confidence Section -->
        <mat-expansion-panel
          data-testid="evidence-section-confidence"
          class="sft-evidence-section"
          [expanded]="true">
          <mat-expansion-panel-header>
            <mat-panel-title class="sft-type-label">Confidenza</mat-panel-title>
          </mat-expansion-panel-header>
          <div class="sft-evidence-confidence">
            <div class="sft-evidence-confidence-bar-wrap">
              <mat-progress-bar
                mode="determinate"
                [value]="confidencePercent()"
                [color]="confidenceColor()"
                aria-label="Livello di confidenza">
              </mat-progress-bar>
              <span class="sft-type-label sft-evidence-confidence-label">
                {{ confidencePercent() }}%
              </span>
            </div>
            <div class="sft-evidence-confidence-badge"
                 [class]="'sft-confidence-badge--' + confidenceLevel()">
              {{ confidenceBadgeLabel() }}
            </div>
          </div>
        </mat-expansion-panel>

      </mat-accordion>
    </div>
  `,
  styles: [`
    .sft-evidence-panel {
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 8px;
      overflow: hidden;
      max-height: 480px;
      overflow-y: auto;
    }

    .sft-evidence-accordion {
      display: block;
    }

    .sft-evidence-section {
      border-bottom: 1px solid var(--sft-border, #363B47);

      &:last-child {
        border-bottom: none;
      }
    }

    .sft-evidence-pre {
      margin: 0;
      padding: 8px 12px;
      overflow-x: auto;
      max-height: 160px;
      font-size: 13px;
      line-height: 1.5;
      background-color: var(--sft-surface, #121418);
      border-radius: 4px;
    }

    .sft-evidence-pre--compact {
      max-height: 80px;
    }

    .sft-evidence-code {
      font-family: 'Courier New', Courier, monospace;
      color: var(--sft-text-primary, #F0F2F5);
      white-space: pre-wrap;
      word-break: break-word;
    }

    .sft-evidence-input-wrap {
      padding: 8px 0;
    }

    .sft-evidence-empty {
      color: var(--sft-text-secondary, #9BA3B2);
      font-size: 14px;
      margin: 0;
      padding: 8px 0;
    }

    .sft-evidence-tool-calls {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .sft-evidence-tool-call {
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 6px;
      padding: 8px 12px;
    }

    .sft-evidence-tool-name {
      color: var(--sft-accent, #3B82F6);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
    }

    .sft-evidence-tool-duration {
      color: var(--sft-text-secondary, #9BA3B2);
      font-weight: 400;
    }

    .sft-evidence-tool-result-label {
      color: var(--sft-text-secondary, #9BA3B2);
      margin: 6px 0 4px 0;
    }

    .sft-evidence-citations {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .sft-evidence-citation {
      border: 1px solid var(--sft-border, #363B47);
      border-radius: 6px;
      padding: 8px 12px;
    }

    .sft-evidence-citation-header {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 6px;
    }

    .sft-evidence-citation-link {
      color: var(--sft-accent, #3B82F6);
      text-decoration: none;
      font-size: 13px;
      word-break: break-all;

      &:hover {
        text-decoration: underline;
      }

      &:focus-visible {
        outline: 2px solid var(--sft-accent, #3B82F6);
        outline-offset: 2px;
      }
    }

    .sft-evidence-citation-uri {
      color: var(--sft-text-secondary, #9BA3B2);
      font-size: 13px;
      word-break: break-all;
    }

    .sft-evidence-citation-page,
    .sft-evidence-citation-lang,
    .sft-evidence-citation-score {
      color: var(--sft-text-secondary, #9BA3B2);
      font-size: 12px;
    }

    .sft-evidence-restricted {
      color: var(--sft-warning, #F59E0B);
      font-size: 13px;
      font-style: italic;
      margin: 0;
    }

    .sft-evidence-chunk {
      color: var(--sft-text-primary, #F0F2F5);
      font-size: 13px;
      line-height: 1.5;
      margin: 0;
    }

    .sft-evidence-confidence {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .sft-evidence-confidence-bar-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    mat-progress-bar {
      flex: 1;
      height: 8px;
      border-radius: 4px;
    }

    .sft-evidence-confidence-label {
      color: var(--sft-text-primary, #F0F2F5);
      min-width: 40px;
    }

    .sft-evidence-confidence-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 10px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      width: fit-content;
    }

    .sft-confidence-badge--low {
      background-color: color-mix(in srgb, var(--sft-destructive, #EF4444) 20%, transparent);
      color: var(--sft-destructive, #EF4444);
    }

    .sft-confidence-badge--medium {
      background-color: color-mix(in srgb, var(--sft-warning, #F59E0B) 20%, transparent);
      color: var(--sft-warning, #F59E0B);
    }

    .sft-confidence-badge--high {
      background-color: color-mix(in srgb, var(--sft-success, #22C55E) 20%, transparent);
      color: var(--sft-success, #22C55E);
    }

    @media (prefers-reduced-motion: reduce) {
      mat-progress-bar {
        transition: none;
      }
    }
  `],
})
export class EvidencePanelComponent implements OnChanges {
  @Input() evidence: EvidencePanel | null = null;

  private readonly _evidenceSignal = signal<EvidencePanel | null>(null);

  ngOnChanges(changes: SimpleChanges): void {
    if ('evidence' in changes) {
      this._evidenceSignal.set(this.evidence);
    }
  }

  readonly hasToolCalls = computed<boolean>(() => {
    const ev = this._evidenceSignal();
    return (ev?.tool_calls_log?.length ?? 0) > 0;
  });

  readonly hasRagCitations = computed<boolean>(() => {
    const ev = this._evidenceSignal();
    return (ev?.rag_citations?.length ?? 0) > 0;
  });

  readonly confidencePercent = computed<number>(() => {
    const ev = this._evidenceSignal();
    if (!ev) return 0;
    return Math.round(ev.confidence * 100);
  });

  readonly confidenceLevel = computed<ConfidenceLevel>(() => {
    const ev = this._evidenceSignal();
    if (!ev) return 'low';
    return getConfidenceLevel(ev.confidence);
  });

  readonly confidenceColor = computed<'primary' | 'accent' | 'warn'>(() => {
    switch (this.confidenceLevel()) {
      case 'high':   return 'primary';
      case 'medium': return 'accent';
      case 'low':    return 'warn';
    }
  });

  readonly confidenceBadgeLabel = computed<string>(() => {
    switch (this.confidenceLevel()) {
      case 'high':   return 'Alta confidenza';
      case 'medium': return 'Confidenza media';
      case 'low':    return 'Bassa confidenza';
    }
  });

  readonly inputJson = computed<string>(() => {
    const ev = this._evidenceSignal();
    if (!ev?.input) return '{}';
    return JSON.stringify(ev.input, null, 2);
  });

  formatJson(value: unknown): string {
    if (value === null || value === undefined) return 'null';
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }

  isValidUri(uri: string): boolean {
    return isValidUrl(uri);
  }
}
