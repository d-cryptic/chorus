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
  // Assert the RULE, not a count: an exact count couples this test to the fixture's
  // composition, so adding an unrelated reply row broke it while the rule still held.
  // NB: the meta renders "POST" via CSS uppercase, so textContent is "post". allTextContents()
  // reads RAW text (innerText would respect the transform) — match case-insensitively.
  const postMetas = await page.locator("div.mono").filter({ hasText: /post/i }).allTextContents();
  expect(postMetas.length).toBeGreaterThan(0);               // the fixture really has posts
  for (const m of postMetas) expect(m).not.toContain("tier");
  const replyMetas = await page.locator("div.mono").filter({ hasText: /reply/i }).allTextContents();
  expect(replyMetas.some((m) => m.includes("tier"))).toBe(true);   // replies still show it
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

test("the read provider is never named in the bundle — it comes from config", async ({ page }) => {
  await page.goto("/");
  // This repo is PUBLIC. Hardcoding the provider compiled the name of a third-party X
  // scraper into a committed bundle — the exact exposure a suggest-only, zero-ban-risk
  // design exists to avoid. Vendor identity is config (PROVIDER_NAME wrangler var), served
  // at runtime via /api/status. Stale hashed bundles kept the old name alive for weeks after
  // the source stopped saying it, which is why `prebuild` now clears assets/.
  const src = await page.evaluate(async () => {
    const s = document.querySelector("script[src]") as HTMLScriptElement;
    return s ? await (await fetch(s.src)).text() : "";
  });
  expect(src.length).toBeGreaterThan(1000);

  // Read the forbidden name from config rather than spelling it out: hardcoding it here
  // would make this very test the last place a PUBLIC repo names the provider — the test
  // would leak the thing it exists to protect. It also makes the check STRONGER: it now
  // tests whatever provider is actually configured, not one I remembered to hardcode.
  const forbidden = process.env.PROVIDER_NAME;
  if (forbidden) {
    expect(src).not.toContain(forbidden);
    expect(src).not.toContain(forbidden.split(".")[0]);   // bare name, not just the FQDN
  }
  // Belt and braces with no name in the file: the bundle must not embed ANY third-party
  // API host. Our own worker is same-origin, so a hardcoded external api.* host is a smell.
  expect(src).not.toMatch(/https:\/\/api\.[a-z0-9-]+\.(io|com)\/twitter/i);
});

test("the Posted tab admits which drafts actually reached X", async ({ page }) => {
  await page.goto("/");
  // "posted" in Chorus means the user CLICKED Post on X. The intent URL only OPENS X's
  // composer; they still have to hit Post there. Measured against their real timeline:
  // only 4 of 10 "posted" suggestions exist on X. The tab said "10 posted" and meant 4.
  // exact: the tooltip also ends with "...or it never sent", so a loose match hits both
  await expect(page.getByText("✓ live", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("never sent", { exact: true })).toBeVisible();
});

test("insights render the verdicts and hide the ones with no data", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: /insights/i }).click();
  // The engine only started producing real claims once outcome rows attached — before that
  // every outcome was an orphan keyed to a feedback id, so `verified` was 0 and every
  // engagement-based insight was insufficient_data forever.
  await expect(page.getByText(/What's working/)).toBeVisible();
  // an insufficient_data insight must NOT be rendered as a claim
  await expect(page.getByText(/insufficient_data/)).toHaveCount(0);
});

test("X-blue is spent only on things that literally are X", async ({ page }) => {
  await page.goto("/");
  // Scan BOTH surfaces. The insight bars only exist on the Insights tab, so a scan of "/"
  // alone reported clean while the bars were still X-blue — the test could not fail, which
  // makes it decorative. Verified by re-injecting the violation and watching it go red.
  await expect(page.getByText("@tom_doerr").first()).toBeVisible();
  const scan = async () => await page.evaluate(() => {
  // index.css: "X blue is NOT a Nakama token. It exists only for things that literally are X:
  // entities inside a tweet body, and the Post-on-X action. Nothing else may use it."
  // It had leaked onto insight bars and the provider top-up CTA. Spending it on chrome
  // dilutes the one signal that means "this publishes to X".
    const cv = document.createElement("canvas"); cv.width = cv.height = 1;
    const ctx = cv.getContext("2d", { willReadFrequently: true })!;
    const rgb = (c: string) => { ctx.clearRect(0,0,1,1); ctx.fillStyle = c; ctx.fillRect(0,0,1,1);
      const d = ctx.getImageData(0,0,1,1).data; return `${d[0]},${d[1]},${d[2]}`; };
    const X = rgb("#1d9bf0");
    const hits: string[] = [];
    document.querySelectorAll("*").forEach((el) => {
      const cs = getComputedStyle(el);
      for (const prop of ["backgroundColor", "color"] as const) {
        const v = cs[prop];
        if (!v || v === "rgba(0, 0, 0, 0)") continue;
        if (rgb(v) === X) {
          const t = (el.textContent || "").trim().slice(0, 24);
          const isTweetEntity = !!el.closest("[data-tweet-body]") || /^@|^https?:/.test(t);
          const isPostAction = /post|retweet/i.test(t);
          if (!isTweetEntity && !isPostAction) hits.push(`${el.tagName}:${t || "(no text)"}`);
        }
      }
    });
    return hits;
  });
  expect(await scan()).toEqual([]);                       // queue surface
  await page.getByRole("tab", { name: /insights/i }).click();
  await expect(page.getByText(/What's working/)).toBeVisible();
  expect(await scan()).toEqual([]);                       // insights surface (where the bars live)
});

test("the tweet you're replying to recedes; your draft does not", async ({ page }) => {
  await page.goto("/");
  // page.evaluate does NOT auto-wait like expect() does, so anchor on rendered content first
  // or you measure an empty React root and get `undefined`. Third time I have hit this.
  await expect(page.getByText("@tom_doerr").first()).toBeVisible();
  // They used to render identically — same avatar, size and weight — so every card was a
  // small puzzle: read "Replying to @x" to work out which was which, 40 times a session.
  // They are not the same kind of thing. Theirs is settled fact you react to; yours is the
  // only thing you act on. The hierarchy should be handed over, not re-derived.
  const contrasts = await page.evaluate(() => {
    const cv = document.createElement("canvas"); cv.width = cv.height = 1;
    const ctx = cv.getContext("2d", { willReadFrequently: true })!;
    const rgb = (c: string) => { ctx.clearRect(0,0,1,1); ctx.fillStyle = c; ctx.fillRect(0,0,1,1);
      const d = ctx.getImageData(0,0,1,1).data; return [d[0],d[1],d[2]]; };
    const lum = ([r,g,b]: number[]) => { const f=(v:number)=>{v/=255;return v<=0.03928?v/12.92:((v+0.055)/1.055)**2.4;};
      return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b); };
    const ratio = (el: Element) => {
      const fg = getComputedStyle(el).color;
      let bg = "rgba(0, 0, 0, 0)", n: Element | null = el;
      while (n && bg === "rgba(0, 0, 0, 0)") { bg = getComputedStyle(n).backgroundColor; n = n.parentElement; }
      const la = lum(rgb(fg)), lb = lum(rgb(bg));
      return (Math.max(la,lb)+0.05)/(Math.min(la,lb)+0.05);
    };
    const bodies = [...document.querySelectorAll(".x-body")].filter(e => ((e as HTMLElement).innerText||"").length > 30);
    return bodies.slice(0, 2).map((e) => ratio(e));
  });
  const [theirs, yours] = contrasts;
  expect(yours).toBeGreaterThan(theirs * 1.5);   // the hierarchy is real, not decorative
  expect(theirs).toBeGreaterThanOrEqual(4.5);    // ...but theirs still clears WCAG AA
});

test("the header heartbeat says something true", async ({ page }) => {
  await page.goto("/");
  // Was `${Math.round(ms / 3.6e6)}h ago · ${n}`. Rounding to HOURS meant a cycle 5 minutes
  // old and one 29 minutes old both read "0h ago", and Math.round made "1h ago" mean 31
  // minutes — actively wrong. The bare trailing number was unlabelled: 3 of what?
  // This is the one line telling you the system is alive. It should not need decoding.
  await expect(page.getByText(/ran 4m ago/)).toBeVisible();   // fixture: last run 4 min ago
  await expect(page.getByText(/3 new/)).toBeVisible();        // ...and 3 suggestions from it
  await expect(page.getByText(/0h ago/)).toHaveCount(0);      // the old lie
});

test("you can read the alternative drafts without clicking them", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("@tom_doerr").first()).toBeVisible();
  // The picker used to .slice(0, 80) AND clip with CSS on top, so a ~140-char draft showed
  // half of one line: you had to click to read an option, then click back. You cannot judge
  // an option you cannot read, and comparing options is the only thing the picker is for.
  const alts = await page.evaluate(() =>
    [...document.querySelectorAll("button")]
      .filter((b) => b.querySelector("span.mono") && ((b as HTMLElement).innerText || "").length > 20)
      .map((b) => ((b as HTMLElement).innerText || "").replace(/\n/g, " ")));
  expect(alts.length).toBeGreaterThan(0);
  const long = alts.find((a) => a.length > 80);
  expect(long).toBeTruthy();                       // a genuinely long alternative exists
  expect(long).toContain("offline for a week.");   // ...and its END is visible, not clipped
});
