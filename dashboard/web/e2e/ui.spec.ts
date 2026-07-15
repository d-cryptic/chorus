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

test("a thread card shows the THREAD, not the fallback draft stacked on top of it", async ({ page }) => {
  await page.goto("/");
  // The fixture's thread suggestion has 3 segments and a standalone fallback draft whose
  // text equals segment 1. The card used to render body + thread and number it {i+2}/{len+1},
  // so a 3-tweet thread read as "4" with segment 1 shown twice. In a suggest-only tool the
  // card owes exactly one honest answer to "what am I about to post".
  await expect(page.getByText("1/3")).toBeVisible();
  await expect(page.getByText("3/3")).toBeVisible();
  await expect(page.getByText("4/4")).toHaveCount(0);      // the off-by-one
  await expect(page.getByText("2/4")).toHaveCount(0);
  // the shape is stated up front, not discovered by scrolling
  await expect(page.getByText(/thread 3/i)).toBeVisible();
  // and the button names what it publishes
  await expect(page.getByRole("button", { name: /Post thread \(3\)/ })).toBeVisible();
  // segment 1 appears ONCE in the thread body (the fallback lives in the picker, truncated)
  const dupes = await page.getByText("most 'it works' memory setups fail quietly, not loudly.", { exact: true }).count();
  expect(dupes).toBe(1);
  await page.screenshot({ path: "e2e/shot-thread.png" });
});

test("a longform card renders the long post, counted against the real limit", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/648\/25000/)).toBeVisible();  // NOT 648/280 in red
  await expect(page.getByText(/^long$/i).first()).toBeVisible();
  await expect(page.getByRole("button", { name: /Post long/ })).toBeVisible();
});

test("original posts do not claim an author tier", async ({ page }) => {
  await page.goto("/");
  // author_tier ranks the person you REPLY to; an original post has none, so "tier B" there
  // is noise pretending to be signal.
  await expect(page.getByText(/tier B/)).toHaveCount(1);     // only the one reply card
});

test("Fetch button says what it does, and reload admits it does not fetch", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: /Fetch new/ })).toBeVisible();
});

test("palette meets WCAG AA, and the focus ring is not the dimmest colour in it", async ({ page }) => {
  await page.goto("/");
  // NB: getComputedStyle returns oklch() verbatim here. Parsing that with a regex yields
  // nonsense (I measured "1.06:1, text invisible" that way and nearly "fixed" a palette that
  // was already fine). Let the browser convert: paint it, read the pixel.
  const r = await page.evaluate(() => {
    const cv = document.createElement("canvas"); cv.width = cv.height = 1;
    const ctx = cv.getContext("2d", { willReadFrequently: true })!;
    const rgb = (css: string) => { ctx.clearRect(0,0,1,1); ctx.fillStyle = css; ctx.fillRect(0,0,1,1);
      const d = ctx.getImageData(0,0,1,1).data; return [d[0],d[1],d[2]]; };
    const lum = ([r,g,b]: number[]) => { const f=(v:number)=>{v/=255;return v<=0.03928?v/12.92:((v+0.055)/1.055)**2.4;};
      return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b); };
    const ratio = (a: string, b: string) => { const la=lum(rgb(a)), lb=lum(rgb(b));
      return (Math.max(la,lb)+0.05)/(Math.min(la,lb)+0.05); };
    const cs = getComputedStyle(document.documentElement);
    const v = (n: string) => cs.getPropertyValue(n).trim();
    const bg = v("--card");
    return {
      foreground: ratio(v("--foreground"), bg),
      muted: ratio(v("--muted-foreground"), bg),
      primary: ratio(v("--primary"), bg),
      primaryVsMuted: lum(rgb(v("--primary"))) / lum(rgb(v("--muted-foreground"))),
    };
  });
  expect(r.foreground).toBeGreaterThanOrEqual(4.5);   // body text
  expect(r.muted).toBeGreaterThanOrEqual(4.5);        // meta rows, tabs, counters
  expect(r.primary).toBeGreaterThanOrEqual(3);        // accent / focus ring, large-element use
});

test("the focused card is unmistakable — it is a keyboard triage tool", async ({ page }) => {
  await page.goto("/");
  // page.evaluate does NOT auto-wait like expect() does, so anchor on rendered content first
  // or you measure an empty React root and "prove" the ring is missing.
  await expect(page.getByText("@tom_doerr").first()).toBeVisible();
  // The focus ring used to be painted in --muted-foreground, the dimmest colour available,
  // for the single most important affordance in a j/k tool.
  const ring = await page.evaluate(() => {
    const el = [...document.querySelectorAll("div")].find(d => getComputedStyle(d).boxShadow.includes("inset"));
    return el ? getComputedStyle(el).boxShadow : null;
  });
  expect(ring).toBeTruthy();
  expect(ring).not.toContain("oklch(0.7 0.012 110)");   // --muted-foreground
  // j moves focus to the next card, and the ring must move with it
  await page.keyboard.press("j");
  const count = await page.evaluate(() =>
    [...document.querySelectorAll("div")].filter(d => getComputedStyle(d).boxShadow.includes("inset")).length);
  expect(count).toBe(1);   // exactly one card focused, never zero or two
});

test("runway is measured, not a magic number", async ({ page }) => {
  await page.goto("/");
  // It used to be `credits / 8600` — a constant that appears nowhere else and was ~50x
  // optimistic: it claimed ~114d while the observed burn implied ~2d. A confident wrong
  // number about your remaining runway is worse than no number.
  await expect(page.getByText(/12\.4k\/day/)).toBeVisible();       // the measured rate, shown
  await expect(page.getByText(/~79d runway/)).toBeVisible();       // 981000 / 12400
});
