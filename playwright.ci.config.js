import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 180_000,
  expect: { timeout: 20_000 },
  retries: 0,
  reporter: 'list',
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:8000',
    trace: 'retain-on-failure'
  },
  webServer: {
    command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
    url: 'http://127.0.0.1:8000',
    reuseExistingServer: true,
    timeout: 180_000
  },
  globalSetup: './tests/global-setup.js',
  globalTeardown: './tests/global-teardown.js'
});