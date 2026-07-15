/** Serves the built bundle + a fixture API so the UI can be judged BY EYE, reproducibly.
 *
 *  Previously playwright had no webServer and no fixture: the screenshots only worked if you
 *  happened to have something running on :8150 by hand, so `npx playwright test` failed cold
 *  for anyone else (and for CI). The UI is the product surface here; it needs a real,
 *  repeatable render, not a hand-held one.
 */
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join } from "node:path";

const ROOT = new URL("../../public/", import.meta.url).pathname;
const now = Date.now();

const S = (o) => ({
  id: o.id, tweet_id: o.id, tweet_url: `https://x.com/i/web/status/${o.id}`,
  author_handle: o.author ?? "tom_doerr", author_tier: o.tier ?? "B",
  tweet_text: o.text, score: o.score ?? 0.72,
  factors: JSON.stringify({ fresh: 0.94, upside: 0.7, pillar_name: "AI" }),
  pillar: "AI", angle: o.angle ?? "counterexample",
  drafts: JSON.stringify(o.drafts ?? ["a dry, specific reply that reads like a person."]),
  thread: JSON.stringify(o.thread ?? []), longform: o.longform ?? null,
  media: JSON.stringify(o.media ?? []), gif: null,
  rationale: "20m old, 0 replies", target: o.target ?? "reply",
  status: o.status ?? "queued", verified: o.verified, created_at: now - (o.age ?? 20) * 60000,
});

const DATA = {
  // Shapes MUST match the worker exactly: App.tsx reads sg.suggestions, sp.total,
  // cf.settings. A fixture that invents its own shape renders an empty page and tests nothing.
  "/api/suggestions": { counts: { queued: 3, posts: 2 }, suggestions: [
    S({ id: "1", text: "Self-hosted Obsidian vault sync for iPhone and iPad. Syncs peer-to-peer, no cloud.", age: 20,
        drafts: ["p2p sync is the easy half. the hard half is what happens when two devices disagree offline for a week.",
                 "no cloud is doing a lot of work in that sentence. what's the conflict resolution story?"] }),
    S({ id: "2", author: "eatonphil", text: "Three ways a self-hosted memory engine silently breaks.", age: 48, target: "post",
        thread: ["most 'it works' memory setups fail quietly, not loudly.", "cosine and BM25 do not share a scale. a threshold tuned on one silently disables the other.", "list endpoints that return empty content make dedupe a no-op."],
        drafts: ["most 'it works' memory setups fail quietly, not loudly."] }),
    S({ id: "4", author: "TheAhmadOsman", text: "shipped it", target: "reply", status: "posted", verified: 1,
        drafts: ["local AI is undeniably huge. ngl, the skill set here is clutch."] }),
    S({ id: "5", author: "sh_reya", text: "clicked but never sent", target: "reply", status: "posted", verified: 0,
        drafts: ["yes and no. branding matters, but tools amplify it."] }),
    S({ id: "3", author: "risingsayak", text: "Why a high follower floor is a timezone filter in disguise.", age: 90, target: "post",
        longform: "picking anchors by follower count feels like quality control. it isn't. ".repeat(9),
        drafts: ["a follower floor is a timezone filter wearing a quality-control hat."] }),
  ]},
  "/api/posted": { counts: {}, suggestions: [] },
  "/api/status": { lastRun: { started_at: now - 240000, finished_at: now - 200000, suggested: 3, error: null, credits: 981000 }, alerts: [], creditsPerDay: 12400, provider: { name: "example-provider", url: "https://example.invalid" } },
  "/api/settings": { settings: { paused: 0, killed: 0, autonomy: "suggest", daily_ceiling_usd: 0.65, quiet_hours: "0-7" } },
  "/api/spend": { total: 0.5063 },
  "/api/insights": { insights: [
    { kind: "post", scope: "post", subject_id: "s1", confidence: 0.286,
      payload: JSON.stringify({ verdict: "worked", engagement: 7, median: 2, author: "session",
                                angle: "relatable tech pain" }),
      evidence: JSON.stringify(["7 vs median 2"]), created_at: now },
    { kind: "best_time", scope: "user", subject_id: "self", confidence: 0.412,
      payload: JSON.stringify({ best_hour: 1, ranked: [{ key: 1, posted: 2, total: 5, rate: 0.4 }] }),
      evidence: JSON.stringify(["h1 2/5"]), created_at: now },
    { kind: "winning_shape", scope: "user", subject_id: "self", confidence: 0.47,
      payload: JSON.stringify({ best_accepted: "post", ranked: [{ key: "post", posted: 9, total: 9, rate: 1 }], followers_by_shape: {}, best_by_followers: null }),
      evidence: JSON.stringify(["post 9/9 accepted", "thread: 0 measured post(s) — below min-sample, no claim"]), created_at: now },
    { kind: "useful_account", scope: "network", subject_id: "targets", confidence: 0,
      payload: JSON.stringify({ state: "insufficient_data", n: 21, need: 5 }), evidence: JSON.stringify([]), created_at: now },
  ], playbook: null },
  // The worker returns `byPillar: byPillar.results` -- ARRAYS, not {results}. Getting this
  // wrong white-screens the Insights tab with "(e.byPillar||[]).filter is not a function",
  // which is a fixture bug that LOOKS exactly like a UI bug. Match the contract.
  "/api/review": {
    byPillar: [{ k: "AI", posted: 9, total: 9 }, { k: "infra", posted: 2, total: 5 }],
    byTier: [{ k: "B", posted: 7, total: 10 }, { k: "C", posted: 4, total: 9 }],
    reasons: [{ k: "off-voice", n: 3 }, { k: "too generic", n: 2 }],
    spend: [{ k: "2026-07-15", usd: 0.5063 }, { k: "2026-07-14", usd: 0.31 }],
    weights: [{ k: "pillar", v: 0.22 }],
  },
};

const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml" };

createServer(async (req, res) => {
  const path = req.url.split("?")[0];
  if (path.startsWith("/api/")) {
    if (req.method === "POST") { res.writeHead(200, { "content-type": "application/json" }); return res.end(JSON.stringify({ ok: true, queued: true })); }
    let body = DATA[path] ?? {};
    // FILTER like the real worker does. It ignored ?status= and ?target= entirely, so every
    // tab got every row: the Posted-tab test passed because the fixture handed it posted rows
    // while sitting on the Queued tab. It would have passed with the status filter completely
    // broken. A stand-in that answers differently from the thing it stands in for tests
    // nothing — the same shape as a dry-run that skips the code path it is previewing.
    if (path === "/api/suggestions") {
      const q = new URL(req.url, "http://x").searchParams;
      const status = q.get("status") ?? "queued";
      const target = q.get("target");
      const rows = (body.suggestions ?? []).filter(
        (r) => (r.status ?? "queued") === status && (!target || r.target === target));
      body = { ...body, suggestions: rows };
    }
    res.writeHead(200, { "content-type": "application/json" });
    return res.end(JSON.stringify(body));
  }
  try {
    const file = path === "/" ? "index.html" : path.slice(1);
    const buf = await readFile(join(ROOT, file));
    res.writeHead(200, { "content-type": MIME[extname(file)] ?? "application/octet-stream" });
    res.end(buf);
  } catch {
    const buf = await readFile(join(ROOT, "index.html"));
    res.writeHead(200, { "content-type": "text/html" });
    res.end(buf);
  }
}).listen(8150, "127.0.0.1", () => console.log("fixture on http://127.0.0.1:8150"));
