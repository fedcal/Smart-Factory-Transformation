/**
 * Pydantic ↔ TypeScript Contract Divergence Guard — SRV-05
 *
 * Purpose: detect silently when the FastAPI OpenAPI export diverges from the
 * committed src/api-types.ts file.  This is the enforcement layer for
 * ROADMAP Success Criterion 4 ("OpenAPI exports, Pydantic/TS contract-tested").
 *
 * How it works:
 *   1. Reads the committed openapi.json from disk.
 *   2. Asserts that all required Pydantic model names are present in the schema.
 *   3. Reads the committed src/api-types.ts and asserts all required type names
 *      appear in the generated TS source (byte-identity check for CI; shape check
 *      for local dev flexibility).
 *
 * Running:
 *   nx test sft-contracts           (via Jest configured below)
 *   cd packages/sft-contracts && npx jest tests/contract.spec.ts
 *
 * To regenerate after model changes:
 *   nx run sft-contracts:generate
 *
 * Requirements: SRV-05 (T-10-11-01 Tampering — type drift mitigation)
 */

import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

// ---------------------------------------------------------------------------
// Paths (relative to this file)
// ---------------------------------------------------------------------------

const CONTRACTS_DIR = path.resolve(__dirname, '..');
const OPENAPI_JSON = path.join(CONTRACTS_DIR, 'openapi.json');
const API_TYPES_TS = path.join(CONTRACTS_DIR, 'src', 'api-types.ts');

// ---------------------------------------------------------------------------
// Models that MUST appear in the OpenAPI schema and generated TS (SRV-05).
// Extend this list when new Pydantic models are added to the gateway.
// ---------------------------------------------------------------------------

const REQUIRED_OPENAPI_SCHEMAS: readonly string[] = [
  'KpiSnapshot',
  'LoginRequest',
  'LoginResponse',
  'MeResponse',
  'ApprovalListResponse',
  'ApprovalResponse',
  'DecideRequest',
  'DecideResponse',
] as const;

// Corresponding identifiers expected in the generated TS file.
// openapi-typescript renders schemas as property keys inside `components.schemas`.
const REQUIRED_TS_IDENTIFIERS: readonly string[] = [
  'KpiSnapshot',
  'LoginRequest',
  'LoginResponse',
  'MeResponse',
  'ApprovalListResponse',
  'ApprovalResponse',
  'DecideRequest',
  'DecideResponse',
] as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Load and parse the committed openapi.json. */
function loadOpenApiSchema(): Record<string, unknown> {
  if (!fs.existsSync(OPENAPI_JSON)) {
    throw new Error(
      `openapi.json not found at ${OPENAPI_JSON}.\n` +
        'Run `nx run sft-contracts:generate` to regenerate.',
    );
  }
  const raw = fs.readFileSync(OPENAPI_JSON, 'utf-8');
  return JSON.parse(raw) as Record<string, unknown>;
}

/** Extract schema component names from the OpenAPI document. */
function extractSchemaNames(schema: Record<string, unknown>): Set<string> {
  const components = schema['components'] as Record<string, unknown> | undefined;
  const schemas = components?.['schemas'] as Record<string, unknown> | undefined;
  return new Set(Object.keys(schemas ?? {}));
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('SRV-05 — Pydantic ↔ TypeScript contract guard', () => {
  let openapiSchema: Record<string, unknown>;
  let schemaNames: Set<string>;
  let apiTypesContent: string;

  beforeAll(() => {
    openapiSchema = loadOpenApiSchema();
    schemaNames = extractSchemaNames(openapiSchema);
    if (!fs.existsSync(API_TYPES_TS)) {
      throw new Error(
        `api-types.ts not found at ${API_TYPES_TS}.\n` +
          'Run `nx run sft-contracts:generate` to regenerate.',
      );
    }
    apiTypesContent = fs.readFileSync(API_TYPES_TS, 'utf-8');
  });

  describe('OpenAPI schema completeness', () => {
    test.each(REQUIRED_OPENAPI_SCHEMAS)(
      'OpenAPI schema contains "%s" (Pydantic model present)',
      (modelName) => {
        expect(schemaNames.has(modelName)).toBe(true);
      },
    );

    test('OpenAPI schema has at least 30 component schemas (gateway surface not shrunk)', () => {
      expect(schemaNames.size).toBeGreaterThanOrEqual(30);
    });
  });

  describe('TypeScript types completeness', () => {
    test.each(REQUIRED_TS_IDENTIFIERS)(
      'api-types.ts contains identifier "%s"',
      (identifier) => {
        // openapi-typescript renders schema names as property keys.
        // We check the raw source for the identifier string.
        expect(apiTypesContent).toContain(identifier);
      },
    );

    test('api-types.ts is non-empty (generation not silently skipped)', () => {
      expect(apiTypesContent.length).toBeGreaterThan(500);
    });

    test('api-types.ts contains "components" namespace (openapi-typescript shape)', () => {
      expect(apiTypesContent).toContain('components');
    });

    test('api-types.ts contains "paths" namespace (routes exported)', () => {
      expect(apiTypesContent).toContain('paths');
    });
  });

  describe('Divergence guard — regenerated schema matches committed', () => {
    /**
     * Regenerate the types from the committed openapi.json on-the-fly and
     * assert that the regenerated content equals the committed api-types.ts.
     *
     * This is the core SRV-05 guard: if a developer edits openapi.json (e.g.
     * after adding a Pydantic model) but forgets to regenerate api-types.ts,
     * this test fails loudly.
     *
     * Skip when:
     *  - openapi-typescript CLI is not available in PATH (e.g. a bare Python
     *    CI image that only runs Python tests); the other tests above still
     *    cover schema completeness.
     *  - SFT_SKIP_REGEN_CHECK=true env var is set (local dev override).
     */
    test('regenerated api-types.ts is byte-identical to committed file', () => {
      if (process.env['SFT_SKIP_REGEN_CHECK'] === 'true') {
        console.info('Skipping regen check: SFT_SKIP_REGEN_CHECK=true');  // eslint-disable-line no-console
        return;
      }

      // Locate the CLI relative to repo root (workspace install).
      const repoRoot = path.resolve(CONTRACTS_DIR, '../..');
      const cliPath = path.join(repoRoot, 'node_modules', '.bin', 'openapi-typescript');

      if (!fs.existsSync(cliPath)) {
        console.warn(  // eslint-disable-line no-console
          'openapi-typescript CLI not found — skipping byte-identity check.\n' +
            `  Expected at: ${cliPath}\n` +
            '  Run `npm install` at repo root to restore.',
        );
        return;
      }

      const tmpOutput = path.join(CONTRACTS_DIR, 'openapi-regen-check.ts.tmp');
      try {
        execSync(
          `"${cliPath}" "${OPENAPI_JSON}" -o "${tmpOutput}"`,
          { stdio: 'pipe', cwd: repoRoot },
        );

        const regenerated = fs.readFileSync(tmpOutput, 'utf-8');

        expect(regenerated).toEqual(apiTypesContent);
      } finally {
        if (fs.existsSync(tmpOutput)) {
          fs.unlinkSync(tmpOutput);
        }
      }
    });
  });
});
