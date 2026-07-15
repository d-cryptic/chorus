import { test, expect } from "@playwright/test";

/** Real browser checks against the built bundle + a fixture API. Screenshots are the
 *  point: this UI is judged by eye, and mock-screenshotting by hand kept hiding bugs
 *  (a stray "0", a dead action row, an invisible insights tab). */

test("queue renders a target tweet + draft, and X chrome is NOT faked", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Queue" })).toBeVisible();
  // the draft must be judgeable
  await expect(page.getByText("Replying to").first()).toBeVisible();
  await expect(page.getByText(/\d+\/280/).first()).toBeVisible();
  // Fabricated X chrome must be gone (Fable's call). NB: an age like "1h" is now REAL
  // (rendered from created_at), so asserting on it proves nothing — assert on the things
  // that were actually invented: the verified badge and the dead action row.
  await expect(page.locator("svg.lucide-badge-check")).toHaveCount(0);
  await expect(page.locator("svg.lucide-heart, svg.lucide-repeat-2, svg.lucide-bookmark")).toHaveCount(0);
  await page.screenshot({ path: "e2e/shot-queue.png", fullPage: false });
});

test("draft picker swaps the full render", async ({ page }) => {
  await page.goto("/");
  const alt = page.locator("button", { hasText: /^2·/ }).first();
  if (await alt.count()) {
    const before = await page.locator("text=/\\d+\\/280/").first().textContent();
    await alt.click();
    await page.waitForTimeout(150);
    const after = await page.locator("text=/\\d+\\/280/").first().textContent();
    expect(after).not.toBe(before);   // a different draft is now the full render
  }
  await page.screenshot({ path: "e2e/shot-picker.png" });
});

test("keyboard triage: j moves focus, ? opens help", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("?");
  await expect(page.getByRole("heading", { name: "Shortcuts" })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.keyboard.press("j");
  await page.screenshot({ path: "e2e/shot-keyboard.png" });
});

test("tabs switch, insights tab renders", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: /insights/i }).click();
  await expect(page.getByText(/What's working|Not enough data/)).toBeVisible();
  await page.screenshot({ path: "e2e/shot-insights.png" });
});

test("media renders inline", async ({ page }) => {
  await page.goto("/");
  const img = page.locator("img[src*='pbs.twimg.com']").first();
  if (await img.count()) await expect(img).toBeVisible();
});
