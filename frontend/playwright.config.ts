import { defineConfig, devices } from "@playwright/test";

/** Runs against the production build (`npm run start`) per the release
 * verification checklist -- `webServer` starts it automatically if nothing
 * is already listening on port 3000. The backend is expected to already be
 * running locally (see README/CLAUDE.md for the `uvicorn` setup) with the
 * seeded owner@g-erp.example user, since these are live smoke tests, not
 * mocked-API tests. */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run start",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
