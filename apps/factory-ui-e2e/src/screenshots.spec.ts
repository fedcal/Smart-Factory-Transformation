/**
 * Bilingual Mock-UI Screenshot Spec — UI-09
 *
 * Captures key screen states in both IT (default) and EN locales for the
 * documentation site (docs/docs/assets/screenshots/).
 *
 * Screens captured:
 *   - Login page (IT + EN)
 *   - Operator dashboard with approval card (IT + EN)
 *   - Manager dashboard with KPI grid (IT + EN)
 *
 * Requirements: UI-09 (bilingual mock-UI docs/screenshots), UI-07 (i18n toggle).
 *
 * Running:
 *   nx e2e ui-factory-e2e --spec=screenshots.spec.ts
 *   -- requires a fully running stack (Angular :4200 + FastAPI :8000).
 *
 * CI / headless environments:
 *   Set SFT_SKIP_SCREENSHOTS=true to skip live capture (docs the intent but
 *   does not fail CI when no display/browser is available).
 *   Screenshots are committed to docs/docs/assets/screenshots/ for static docs.
 *
 * Screenshot output path:
 *   docs/docs/assets/screenshots/<locale>/<page>-<timestamp>.png
 *   (static committed versions live at docs/docs/assets/screenshots/ without
 *    timestamp suffix — the spec overwrites those in-place on each capture run.)
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const OPERATOR_EMAIL = 'operator@mantis.it';
const OPERATOR_PASSWORD = 'mantis2026';

const MANAGER_EMAIL = 'supervisor@mantis.it';
const MANAGER_PASSWORD = 'mantis2026';

/** Path to the screenshots directory inside the docs site. */
const SCREENSHOTS_DIR = path.resolve(
  __dirname,
  '../../../docs/docs/assets/screenshots',
);

const SKIP_SCREENSHOTS = process.env['SFT_SKIP_SCREENSHOTS'] === 'true';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Ensure the screenshots directory structure exists.
 * Creates: screenshots/it/ and screenshots/en/
 */
function ensureScreenshotDirs(): void {
  for (const locale of ['it', 'en']) {
    fs.mkdirSync(path.join(SCREENSHOTS_DIR, locale), { recursive: true });
  }
}

/**
 * Save a screenshot to the docs assets directory.
 * The name is deterministic (no timestamp) so docs can reference a stable path.
 */
async function saveScreenshot(
  page: import('@playwright/test').Page,
  locale: 'it' | 'en',
  name: string,
): Promise<void> {
  const filePath = path.join(SCREENSHOTS_DIR, locale, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: false });
}

/**
 * Switch the UI locale via the language toggle.
 * Waits for the transloco loader to complete (≤ 500 ms per UI-SPEC).
 */
async function switchToLocale(
  page: import('@playwright/test').Page,
  locale: 'it' | 'en',
): Promise<void> {
  const toggle = page.getByTestId('language-toggle');
  const localeButton = toggle.getByText(locale.toUpperCase());
  await localeButton.click();
  // Allow transloco to swap locale strings (max 500 ms per UI-SPEC i18n contract).
  await page.waitForTimeout(600);
}

/**
 * Attempt to log in as the given persona via the login form.
 * Returns true on success, false if the login form is not available
 * (e.g. a stub/dev-mode app without real auth routing).
 */
async function loginAs(
  page: import('@playwright/test').Page,
  email: string,
  password: string,
): Promise<boolean> {
  try {
    await page.goto('/auth/login', { waitUntil: 'domcontentloaded', timeout: 10_000 });
    const emailField = page.getByLabel(/email/i).or(page.getByPlaceholder(/email/i));
    if (!(await emailField.isVisible({ timeout: 3_000 }).catch(() => false))) {
      return false;
    }
    await emailField.fill(email);
    await page.getByLabel(/password/i).fill(password);
    await page.getByRole('button', { name: /accedi|sign in/i }).click();
    await page.waitForURL(/\/(operator|manager|technician|admin|demo)/, { timeout: 8_000 });
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Suite
// ---------------------------------------------------------------------------

test.describe('UI-09 — Bilingual mock-UI screenshots', () => {
  test.beforeAll(() => {
    if (!SKIP_SCREENSHOTS) {
      ensureScreenshotDirs();
    }
  });

  test.skip(SKIP_SCREENSHOTS, 'SFT_SKIP_SCREENSHOTS=true — skipping live screenshot capture');

  /**
   * Login page — Italian (default locale)
   */
  test('capture login page — IT', async ({ page }) => {
    await page.goto('/auth/login', { waitUntil: 'domcontentloaded', timeout: 15_000 });
    // Wait for the login card to be visible before capturing.
    await page.waitForSelector('form, [data-testid="login-form"]', { timeout: 8_000 });
    await saveScreenshot(page, 'it', 'login');
  });

  /**
   * Login page — English (after locale toggle)
   */
  test('capture login page — EN', async ({ page }) => {
    await page.goto('/auth/login', { waitUntil: 'domcontentloaded', timeout: 15_000 });
    await page.waitForSelector('form, [data-testid="login-form"]', { timeout: 8_000 });
    // Language toggle may be on the login page or only available after login.
    const toggleVisible = await page
      .getByTestId('language-toggle')
      .isVisible({ timeout: 2_000 })
      .catch(() => false);
    if (toggleVisible) {
      await switchToLocale(page, 'en');
    }
    await saveScreenshot(page, 'en', 'login');
  });

  /**
   * Operator dashboard — Italian
   * Captures the approval queue feed with at least the card placeholder.
   */
  test('capture operator approval dashboard — IT', async ({ page }) => {
    const loggedIn = await loginAs(page, OPERATOR_EMAIL, OPERATOR_PASSWORD);
    if (!loggedIn) {
      // Navigate directly in dev-mode when auth is bypassed.
      await page.goto('/operator', { waitUntil: 'domcontentloaded', timeout: 15_000 });
    }
    await page.waitForSelector(
      '[data-testid="approval-card"], [data-testid="kpi-grid"], main',
      { timeout: 10_000 },
    );
    await saveScreenshot(page, 'it', 'operator-approval');
  });

  /**
   * Operator dashboard — English
   */
  test('capture operator approval dashboard — EN', async ({ page }) => {
    const loggedIn = await loginAs(page, OPERATOR_EMAIL, OPERATOR_PASSWORD);
    if (!loggedIn) {
      await page.goto('/operator', { waitUntil: 'domcontentloaded', timeout: 15_000 });
    }
    await page.waitForSelector(
      '[data-testid="approval-card"], [data-testid="kpi-grid"], main',
      { timeout: 10_000 },
    );
    const toggleVisible = await page
      .getByTestId('language-toggle')
      .isVisible({ timeout: 2_000 })
      .catch(() => false);
    if (toggleVisible) {
      await switchToLocale(page, 'en');
    }
    await saveScreenshot(page, 'en', 'operator-approval');
  });

  /**
   * Manager KPI dashboard — Italian
   */
  test('capture manager KPI dashboard — IT', async ({ page }) => {
    const loggedIn = await loginAs(page, MANAGER_EMAIL, MANAGER_PASSWORD);
    if (!loggedIn) {
      await page.goto('/manager', { waitUntil: 'domcontentloaded', timeout: 15_000 });
    }
    await page.waitForSelector(
      '[data-testid="kpi-grid"], [data-testid="kpi-tile"], main',
      { timeout: 10_000 },
    );
    await saveScreenshot(page, 'it', 'manager-dashboard');
  });

  /**
   * Manager KPI dashboard — English
   */
  test('capture manager KPI dashboard — EN', async ({ page }) => {
    const loggedIn = await loginAs(page, MANAGER_EMAIL, MANAGER_PASSWORD);
    if (!loggedIn) {
      await page.goto('/manager', { waitUntil: 'domcontentloaded', timeout: 15_000 });
    }
    await page.waitForSelector(
      '[data-testid="kpi-grid"], [data-testid="kpi-tile"], main',
      { timeout: 10_000 },
    );
    const toggleVisible = await page
      .getByTestId('language-toggle')
      .isVisible({ timeout: 2_000 })
      .catch(() => false);
    if (toggleVisible) {
      await switchToLocale(page, 'en');
    }
    await saveScreenshot(page, 'en', 'manager-dashboard');
  });
});

/**
 * CI / Human-verified note (UI-09):
 * ─────────────────────────────────────────────────────────────────────────────
 * Live screenshot capture requires a fully running stack:
 *   - Angular frontend (nx serve ui-factory)
 *   - FastAPI gateway (uvicorn svc_api_gateway.main:app)
 *   - TimescaleDB + seed data
 *
 * In a CI environment without a display or seeded backend:
 *   SFT_SKIP_SCREENSHOTS=true nx e2e ui-factory-e2e --spec=screenshots.spec.ts
 *
 * The static screenshots committed to docs/docs/assets/screenshots/ serve as
 * the docs artifacts when live capture is not available.
 *
 * To regenerate screenshots after UI changes:
 *   1. Start the full stack (docker compose up -d)
 *   2. nx e2e ui-factory-e2e --spec=screenshots.spec.ts
 *   3. git add docs/docs/assets/screenshots/
 *   4. git commit -m "docs: update mock-UI screenshots (UI-09)"
 * ─────────────────────────────────────────────────────────────────────────────
 */
