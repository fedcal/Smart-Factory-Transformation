import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for the factory-ui E2E suite.
 *
 * baseURL resolution order:
 *   1. PW_BASE_URL environment variable (set in CI or local override)
 *   2. Default: http://localhost:4200 (standard Angular dev-server port)
 *
 * webServer: boots ui-factory in development mode before the suite runs.
 * Skip webServer when PW_SKIP_WEB_SERVER=true (external running stack in CI).
 *
 * The suite requires a fully operational stack (Angular frontend + FastAPI
 * gateway on :8000). If the stack is unreachable, tests fail explicitly
 * (no silent pass) via expect(response.ok()).toBeTruthy() assertions.
 */

const BASE_URL = process.env['PW_BASE_URL'] ?? 'http://localhost:4200';
const SKIP_WEB_SERVER = process.env['PW_SKIP_WEB_SERVER'] === 'true';

export default defineConfig({
  testDir: './src',
  testMatch: '**/*.spec.ts',

  /* Run tests in files in parallel */
  fullyParallel: false,

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env['CI'],

  /* Retry on CI only */
  retries: process.env['CI'] ? 1 : 0,

  /* Opt out of parallel tests on CI */
  workers: process.env['CI'] ? 1 : undefined,

  /* Reporter to use */
  reporter: [['html', { open: 'never' }], ['list']],

  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: BASE_URL,

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',

    /* Screenshot only on failure */
    screenshot: 'only-on-failure',

    /* Headless by default */
    headless: true,
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Output folder for test artifacts */
  outputDir: '../../dist/.playwright/apps/factory-ui-e2e',

  /**
   * webServer: starts the Angular dev server before running tests.
   * Disabled via PW_SKIP_WEB_SERVER=true when an external stack is running.
   *
   * NOTE: A live backend (FastAPI gateway on :8000) must also be running
   * for the HITL approval flow tests to pass. The webServer here only
   * covers the Angular frontend.
   */
  ...(SKIP_WEB_SERVER
    ? {}
    : {
        webServer: {
          command: 'npx nx serve ui-factory --configuration=development',
          url: BASE_URL,
          reuseExistingServer: !process.env['CI'],
          timeout: 120_000,
          stdout: 'pipe',
          stderr: 'pipe',
        },
      }),
});
