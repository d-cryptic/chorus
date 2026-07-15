import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  use: { baseURL: "http://127.0.0.1:8150", viewport: { width: 1280, height: 900 } },
  reporter: [["list"]],
  // Without this, `npx playwright test` fails cold unless you happen to have something on
  // :8150 already. The fixture serves the real built bundle + a stub API, so the screenshots
  // are reproducible instead of hand-held.
  webServer: {
    command: "npm run build && node e2e/fixture-server.mjs",
    url: "http://127.0.0.1:8150",
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  },
});
