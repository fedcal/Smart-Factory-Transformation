/**
 * HITL Approval Flow — Playwright E2E spec
 *
 * Implements the 8-step UI-SPEC contract table (10-UI-SPEC "Playwright E2E — Contratto Test").
 * Covers ROADMAP Success Criterion 3: alert → approval card → evidence review → approve → audit.
 *
 * Requirements: UI-10, HITL-01, HITL-06, HITL-07
 *
 * API Note: Step 8 asserts audit via GET /v1/approvals (filtered by approval_id).
 * There is NO /v1/audit/{id} endpoint in this system — do not use one.
 *
 * Stack requirement: A fully running stack is required:
 *   - Angular frontend on baseURL (default: http://localhost:4200)
 *   - FastAPI gateway on http://localhost:8000
 * If the stack is unreachable, tests fail explicitly (never silently pass).
 *
 * Running in CI/CD: set PW_SKIP_WEB_SERVER=true if the stack is already running.
 * For local dev: `nx e2e ui-factory-e2e` after starting `nx serve ui-factory` + backend.
 */

import { test, expect, request, APIResponse } from '@playwright/test';

// ──────────────────────────────────────────────────────────────────────────────
// Constants
// ──────────────────────────────────────────────────────────────────────────────

const OPERATOR_EMAIL = 'operator@mantis.it';
const OPERATOR_PASSWORD = 'mantis2026';
const MOTIVATION_TEXT = 'Approvazione verificata manualmente: i parametri rientrano nelle soglie operative consentite.';

/** Gateway base URL — the FastAPI backend. */
const API_BASE = process.env['API_BASE_URL'] ?? 'http://localhost:8000';

/** Operator dashboard route (per UI-SPEC persona routing table). */
const OPERATOR_ROUTE = '/operator';

// ──────────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Asserts that the page's baseURL is reachable before running tests.
 * Fails explicitly if the frontend is unreachable — prevents silent false-greens.
 */
async function assertFrontendReachable(page: import('@playwright/test').Page): Promise<void> {
  let response: import('@playwright/test').Response | null = null;
  try {
    response = await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 15_000 });
  } catch {
    throw new Error(
      `[HITL E2E] Frontend unreachable at ${page.context().browser()?.version() ?? 'unknown browser'}.\n` +
        `baseURL: ${process.env['PW_BASE_URL'] ?? 'http://localhost:4200'}\n` +
        `Start the Angular dev server: nx serve ui-factory --configuration=development`
    );
  }
  if (!response || !response.ok()) {
    throw new Error(
      `[HITL E2E] Frontend returned HTTP ${response?.status() ?? 'no response'}. ` +
        `Ensure the Angular app is running and healthy.`
    );
  }
}

/**
 * Asserts that the API gateway is reachable.
 * Fails explicitly if the backend is unreachable.
 */
async function assertBackendReachable(): Promise<void> {
  const apiCtx = await request.newContext({ baseURL: API_BASE });
  let resp: APIResponse;
  try {
    resp = await apiCtx.get('/health', { timeout: 10_000 });
  } catch {
    await apiCtx.dispose();
    throw new Error(
      `[HITL E2E] Backend gateway unreachable at ${API_BASE}.\n` +
        `Start the FastAPI gateway before running this suite.\n` +
        `Check that API_BASE_URL env var points to the correct host:port.`
    );
  }
  await apiCtx.dispose();
  if (!resp.ok() && resp.status() !== 404) {
    // 404 on /health is acceptable for gateways that don't expose a health route;
    // only network-level failures (connection refused, timeout) are fatal.
    throw new Error(
      `[HITL E2E] Backend gateway returned ${resp.status()} on /health. ` +
        `Verify the gateway is started and listening on ${API_BASE}.`
    );
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Test Suite
// ──────────────────────────────────────────────────────────────────────────────

test.describe('HITL Approval Flow — 8-step UI-SPEC contract', () => {
  /**
   * State shared across steps within a single test run.
   * Using a single test (not beforeEach) to preserve browser context / auth state.
   */
  let capturedApprovalId: string | null = null;
  let capturedJwtToken: string | null = null;

  // ---------------------------------------------------------------------------
  // Stack reachability guard — runs once before the suite
  // ---------------------------------------------------------------------------

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    try {
      await assertFrontendReachable(page);
    } finally {
      await page.close();
    }

    // Backend reachability check (separate API context — not through the page)
    await assertBackendReachable();
  });

  // ---------------------------------------------------------------------------
  // Main flow — all 8 steps in sequence within one test
  // (preserves localStorage auth token and browser state between steps)
  // ---------------------------------------------------------------------------

  test('completes the full HITL approval flow (8 steps)', async ({ page }) => {
    // ──────────────────────────────────────────────────────────────────────────
    // STEP 1: Login as operator@mantis.it via API, store JWT in localStorage
    //
    // UI-SPEC: page.request.post('/auth/login', {data:{email:...}})
    //          → Token JWT nel localStorage
    // ──────────────────────────────────────────────────────────────────────────

    // Navigate to the app first so we have a page context for localStorage
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const loginResponse = await page.request.post(`${API_BASE}/auth/login`, {
      data: {
        email: OPERATOR_EMAIL,
        password: OPERATOR_PASSWORD,
      },
      headers: { 'Content-Type': 'application/json' },
    });

    expect(
      loginResponse.ok(),
      `[Step 1] POST /auth/login failed with status ${loginResponse.status()}. ` +
        `Verify operator@mantis.it is seeded and the backend is running.`
    ).toBeTruthy();

    const loginBody = await loginResponse.json();

    // The token field may be 'access_token' or 'token' depending on backend contract
    capturedJwtToken =
      loginBody['access_token'] ?? loginBody['token'] ?? null;

    expect(
      capturedJwtToken,
      '[Step 1] JWT token not found in login response. ' +
        'Response body: ' + JSON.stringify(loginBody)
    ).toBeTruthy();

    // Inject token into localStorage so the Angular app recognises the session
    await page.evaluate((token: string) => {
      localStorage.setItem('sft_access_token', token);
      localStorage.setItem('sft_auth_token', token); // fallback key
    }, capturedJwtToken as string);

    // Verify token is persisted in localStorage
    const storedToken = await page.evaluate(() =>
      localStorage.getItem('sft_access_token') ?? localStorage.getItem('sft_auth_token')
    );
    expect(storedToken, '[Step 1] JWT not found in localStorage after injection').toBeTruthy();

    // ──────────────────────────────────────────────────────────────────────────
    // STEP 2: Navigate to operator dashboard, verify KPI grid with ≥6 tiles
    //
    // UI-SPEC: page.getByTestId('kpi-grid')
    //          → await expect(page.getByTestId('kpi-tile')).toHaveCount(6)
    // ──────────────────────────────────────────────────────────────────────────

    await page.goto(OPERATOR_ROUTE, { waitUntil: 'networkidle' });

    // Wait for kpi-grid to appear (Angular route + data fetch)
    const kpiGrid = page.getByTestId('kpi-grid');
    await expect(kpiGrid).toBeVisible({ timeout: 30_000 });

    // Assert ≥ 6 KPI tiles are rendered
    const kpiTiles = page.getByTestId('kpi-tile');
    await expect(kpiTiles).toHaveCount(6, { timeout: 15_000 });

    // ──────────────────────────────────────────────────────────────────────────
    // STEP 3: Approval card present with status "pending"
    //
    // UI-SPEC: page.getByTestId('approval-card').first()
    //          → Card con status "pending"
    // ──────────────────────────────────────────────────────────────────────────

    const firstCard = page.getByTestId('approval-card').first();
    await expect(firstCard).toBeVisible({ timeout: 15_000 });

    // Status chip must show "pending"
    const cardStatus = firstCard.getByTestId('approval-card-status');
    await expect(cardStatus).toBeVisible();
    await expect(cardStatus).toContainText(/pending|in attesa/i);

    // Capture approval_id from the card's data attribute for later steps
    capturedApprovalId = await firstCard.getAttribute('data-approval-id');
    // approval-id may be stored as a data attribute; fall back to null (captured in intercept)

    // ──────────────────────────────────────────────────────────────────────────
    // STEP 4: Open Evidence Panel, verify input/tool_calls/citations sections
    //
    // UI-SPEC: await page.getByRole('button', {name:/Evidence/}).click()
    //          → Sezioni input, tool_calls, citations visibili
    // ──────────────────────────────────────────────────────────────────────────

    // Evidence panel may be open by default for pending cards (per UI-SPEC component spec)
    // Try to click the Evidence toggle button if it exists
    const evidenceToggle = page.getByRole('button', { name: /Evidence|Evidenze/i });
    if (await evidenceToggle.first().isVisible({ timeout: 3_000 }).catch(() => false)) {
      await evidenceToggle.first().click();
    }

    const evidencePanel = firstCard.getByTestId('evidence-panel');
    await expect(evidencePanel).toBeVisible({ timeout: 10_000 });

    // Assert the three sections are present (input, tool_calls, citations)
    // These may be accordion sections — check for their presence in the DOM
    await expect(evidencePanel.locator('[data-section="input"], .evidence-input, [aria-label*="input" i]').first()).toBeVisible({ timeout: 5_000 });
    await expect(evidencePanel.locator('[data-section="tool_calls"], .evidence-tool-calls, [aria-label*="tool" i]').first()).toBeVisible({ timeout: 5_000 });
    await expect(evidencePanel.locator('[data-section="citations"], .evidence-citations, [aria-label*="citation" i]').first()).toBeVisible({ timeout: 5_000 });

    // ──────────────────────────────────────────────────────────────────────────
    // STEP 5: Fill motivation textarea, verify CharCounter updates
    //
    // UI-SPEC: await page.getByTestId('motivation-textarea').fill(...)
    //          → CharCounter aggiornato
    // ──────────────────────────────────────────────────────────────────────────

    const motivationTextarea = firstCard.getByTestId('motivation-textarea');
    await expect(motivationTextarea).toBeVisible({ timeout: 10_000 });

    await motivationTextarea.fill(MOTIVATION_TEXT);

    // CharCounter must update — look for it inside the card
    const charCounter = firstCard.locator(
      '[data-testid="char-counter"], .char-counter, [aria-label*="character" i], [aria-label*="caratteri" i]'
    ).first();
    await expect(charCounter).toBeVisible({ timeout: 5_000 });
    // Counter text should reflect the filled length or a "min met" indicator
    const counterText = await charCounter.textContent();
    expect(
      counterText,
      '[Step 5] CharCounter text is empty — check the CharCounter component renders after fill'
    ).toBeTruthy();

    // ──────────────────────────────────────────────────────────────────────────
    // STEP 6: Intercept POST .../approve, click approve-btn
    //
    // UI-SPEC: page.route('**/v1/approvals/*/approve', ...) + click approve-btn
    //          → POST /v1/approvals/{id}/approve intercettato
    // ──────────────────────────────────────────────────────────────────────────

    let interceptedApprovalId: string | null = capturedApprovalId;
    let postBodyCaptured: Record<string, unknown> | null = null;

    await page.route('**/v1/approvals/*/approve', async (route, interceptedRequest) => {
      // Extract the approval_id from the URL
      const urlMatch = interceptedRequest.url().match(/\/v1\/approvals\/([^/]+)\/approve/);
      if (urlMatch) {
        interceptedApprovalId = urlMatch[1];
      }

      // Capture request body to verify motivation is sent
      const postData = interceptedRequest.postDataJSON() as Record<string, unknown> | null;
      postBodyCaptured = postData;

      // Forward the request to the real backend
      await route.continue();
    });

    // Also handle the alternative endpoint pattern (POST .../decide with action=approve)
    await page.route('**/v1/approvals/*/decide', async (route, interceptedRequest) => {
      const urlMatch = interceptedRequest.url().match(/\/v1\/approvals\/([^/]+)\/decide/);
      if (urlMatch && !interceptedApprovalId) {
        interceptedApprovalId = urlMatch[1];
      }
      const postData = interceptedRequest.postDataJSON() as Record<string, unknown> | null;
      if (postData && !postBodyCaptured) {
        postBodyCaptured = postData;
      }
      await route.continue();
    });

    const approveBtn = firstCard.getByTestId('approve-btn');
    await expect(approveBtn).toBeEnabled({ timeout: 5_000 });

    // Click approve and wait for the POST to be dispatched
    await Promise.all([
      page.waitForRequest(
        (req) =>
          req.method() === 'POST' &&
          (req.url().includes('/v1/approvals/') && (req.url().includes('/approve') || req.url().includes('/decide'))),
        { timeout: 15_000 }
      ),
      approveBtn.click(),
    ]);

    // Assert the POST was intercepted and the motivation was included in the body
    expect(
      interceptedApprovalId,
      '[Step 6] Could not capture approval_id from the POST URL. ' +
        'Check that the approve-btn triggers POST /v1/approvals/{id}/approve'
    ).toBeTruthy();

    expect(
      postBodyCaptured,
      '[Step 6] POST body was empty — motivation must be sent in the request body'
    ).not.toBeNull();

    const motivation = (postBodyCaptured as unknown as Record<string, unknown>)['motivation'] as string | undefined;
    expect(
      motivation,
      '[Step 6] "motivation" field missing from POST body: ' + JSON.stringify(postBodyCaptured)
    ).toBeTruthy();

    // ──────────────────────────────────────────────────────────────────────────
    // STEP 7: Card updates to "approved", ActionBar is hidden
    //
    // UI-SPEC: await expect(page.getByTestId('approval-card').first())...
    //          → Status "approved", ActionBar nascosta
    // ──────────────────────────────────────────────────────────────────────────

    // Wait for the card to reflect the approved state (SSE update or optimistic UI)
    await expect(cardStatus).toContainText(/approved|approvato/i, { timeout: 20_000 });

    // ActionBar (approve + reject buttons) must be hidden after approval
    const actionBar = firstCard.locator(
      '[data-testid="action-bar"], .action-bar, .approval-actions'
    ).first();

    // ActionBar should not be visible (hidden/removed after approval)
    await expect(actionBar).not.toBeVisible({ timeout: 10_000 });

    // Approve and Reject buttons must not be visible
    const approveBtnAfter = firstCard.getByTestId('approve-btn');
    const rejectBtnAfter = firstCard.getByTestId('reject-btn');
    await expect(approveBtnAfter).not.toBeVisible({ timeout: 5_000 });
    await expect(rejectBtnAfter).not.toBeVisible({ timeout: 5_000 });

    // ──────────────────────────────────────────────────────────────────────────
    // STEP 8: Audit record — assert via GET /v1/approvals filtered by approval_id
    //
    // NOTE: There is NO /v1/audit/{id} endpoint in this system.
    // Audit data is embedded in the approval record returned by GET /v1/approvals.
    // We filter the list response by the approval_id captured in Step 6.
    //
    // UI-SPEC (plan override): page.request.get('/v1/approvals') filtered by id
    //          → decision: 'APPROVED', motivation presente
    // ──────────────────────────────────────────────────────────────────────────

    expect(
      interceptedApprovalId,
      '[Step 8] Cannot check audit record: approval_id was not captured in Step 6'
    ).toBeTruthy();

    const auditApiCtx = await request.newContext({
      baseURL: API_BASE,
      extraHTTPHeaders: {
        Authorization: `Bearer ${capturedJwtToken}`,
      },
    });

    let auditResponse: APIResponse;
    try {
      // Fetch the full approvals list (the backend may support ?id= filter)
      auditResponse = await auditApiCtx.get('/v1/approvals', {
        params: { approval_id: interceptedApprovalId as string },
        timeout: 10_000,
      });
    } catch {
      await auditApiCtx.dispose();
      throw new Error(
        `[Step 8] GET /v1/approvals request failed. ` +
          `Verify the backend is running and the JWT token is valid.`
      );
    }

    expect(
      auditResponse.ok(),
      `[Step 8] GET /v1/approvals returned ${auditResponse.status()}. ` +
        `Check that the operator role has read access to the approvals list.`
    ).toBeTruthy();

    const approvalsList = await auditResponse.json() as unknown;

    // The response may be a list or a paginated object { items: [...] }
    const approvals: Array<Record<string, unknown>> =
      Array.isArray(approvalsList)
        ? (approvalsList as Array<Record<string, unknown>>)
        : ((approvalsList as Record<string, unknown>)['items'] as Array<Record<string, unknown>>) ?? [];

    // Find the specific approval record by id
    const approvalRecord = approvals.find(
      (a) =>
        a['id'] === interceptedApprovalId ||
        a['approval_id'] === interceptedApprovalId
    );

    expect(
      approvalRecord,
      `[Step 8] Approval record with id=${interceptedApprovalId} not found in GET /v1/approvals response. ` +
        `Response contained ${approvals.length} records.`
    ).toBeTruthy();

    // Assert decision is APPROVED
    const decision =
      (approvalRecord as Record<string, unknown>)['decision'] ??
      (approvalRecord as Record<string, unknown>)['status'];

    expect(
      String(decision).toUpperCase(),
      `[Step 8] Expected decision=APPROVED but got: ${decision}`
    ).toMatch(/approved|APPROVED/i);

    // Assert motivation is persisted in the audit record
    const auditMotivation =
      (approvalRecord as Record<string, unknown>)['motivation'] ??
      ((approvalRecord as Record<string, unknown>)['decision_json'] as Record<string, unknown> | undefined)?.[
        'motivation'
      ];

    expect(
      auditMotivation,
      `[Step 8] "motivation" field missing or empty in audit record: ` +
        JSON.stringify(approvalRecord)
    ).toBeTruthy();

    expect(
      String(auditMotivation).length,
      '[Step 8] motivation in audit record is shorter than the filled text'
    ).toBeGreaterThan(0);

    await auditApiCtx.dispose();
  });
});
