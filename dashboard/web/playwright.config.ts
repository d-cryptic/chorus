import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  use: { baseURL: "http://127.0.0.1:8150", viewport: { width: 1280, height: 900 } },
  reporter: [["list"]],
});
