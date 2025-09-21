import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 120_000,
  expect: { timeout: 15_000 },
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:8000',
    trace: 'retain-on-failure'
  },
  webServer: {
    command: 'powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\run_server.ps1',
    url: 'http://127.0.0.1:8000',
    reuseExistingServer: true,
    timeout: 120_000
  },
  globalSetup: './tests/global-setup.js',
  globalTeardown: './tests/global-teardown.js'
});
