// Chorus queue API + static host.
// - Human surface: behind Cloudflare Access (JWT-verified, single email), fails closed.
// - Box surface (/api/box/* + legacy /api/ingest,/api/spend POST): token-authed, GET reads + POST
//   writes so budget-guard / opportunity-rank / rank-tune / outcome-track / morning-digest can
//   actually read+write the store (Fable review #3). No X write path exists anywhere.

import { jwtVerify, createRemoteJWKSet } from "jose";

export interface Env {
  DB: D1Database;
  ASSETS: Fetcher;
  ALLOWED_EMAIL: string;
  ACCESS_TEAM_DOMAIN?: string;
  ACCESS_AUD?: string;
  INGEST_TOKEN?: string;
  DEV_OPEN?: string;
}

const json = (d: unknown, s = 200) =>
  new Response(JSON.stringify(d), { status: s, headers: { "content-type": "application/json" } });

const STATUS: Record<string, string> = {
  posted: "posted", posted_edited: "posted", dismissed: "dismissed", snoozed: "snoozed",
};
const localDay = (o = 330) => new Date(Date.now() + o * 60000).toISOString().slice(0, 10); // IST

let JWKS: ReturnType<typeof createRemoteJWKSet> | null = null;
async function verifyAccess(req: Request, env: Env, url: URL): Promise<boolean> {
  // DEV_OPEN only works on localhost — a fat-fingered prod uncomment can NEVER disable auth (Fable).
  if (env.DEV_OPEN === "1" && /^(localhost|127\.|0\.0\.0\.0)/.test(url.hostname)) return true;
  const token =
    req.headers.get("Cf-Access-Jwt-Assertion") ??
    req.headers.get("cookie")?.match(/CF_Authorization=([^;]+)/)?.[1];
  if (!token || !env.ACCESS_TEAM_DOMAIN || !env.ACCESS_AUD) return false;
  const iss = `https://${env.ACCESS_TEAM_DOMAIN}.cloudflareaccess.com`;
  JWKS ??= createRemoteJWKSet(new URL(`${iss}/cdn-cgi/access/certs`));
  try {
    const { payload } = await jwtVerify(token, JWKS, { issuer: iss, audience: env.ACCESS_AUD });
    return payload.email === env.ALLOWED_EMAIL;
  } catch {
    return false;
  }
}
const boxAuthed = (req: Request, env: Env) =>
  !!env.INGEST_TOKEN && req.headers.get("authorization") === `Bearer ${env.INGEST_TOKEN}`;

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    if (!url.pathname.startsWith("/api/")) return env.ASSETS.fetch(req);

    const legacyBoxPost = req.method === "POST" && (url.pathname === "/api/ingest" || url.pathname === "/api/spend");
    if (url.pathname.startsWith("/api/box/") || legacyBoxPost) {
      if (!boxAuthed(req, env)) return json({ error: "unauthorized" }, 401);
      return box(req, env, url);
    }

    if (!(await verifyAccess(req, env, url))) return json({ error: "forbidden" }, 403);
    return human(req, env, url);
  },

  // Expiry sweep — wired via [triggers] crons in wrangler.toml.
  async scheduled(_e: ScheduledEvent, env: Env) {
    await env.DB.prepare("UPDATE suggestion SET status='expired' WHERE status='queued' AND expires_at IS NOT NULL AND expires_at <= ?")
      .bind(Date.now()).run();
  },
};

async function human(req: Request, env: Env, url: URL): Promise<Response> {
  try {
    if (req.method === "GET" && url.pathname === "/api/suggestions") {
      const status = url.searchParams.get("status") ?? "queued";
      const limit = Math.min(Number(url.searchParams.get("limit") ?? 50) || 50, 200);
      const now = Date.now();
      const { results } = await env.DB.prepare(
        `SELECT * FROM suggestion
           WHERE (status = ?1 OR (status='snoozed' AND snooze_until IS NOT NULL AND snooze_until <= ?2))
             AND (expires_at IS NULL OR expires_at > ?2)
           ORDER BY score DESC LIMIT ?3`
      ).bind(status, now, limit).all();
      return json({ suggestions: results });
    }
    if (req.method === "GET" && url.pathname === "/api/spend") return json(await spendToday(env));
    if (req.method === "GET" && url.pathname === "/api/status") {
      const row = await env.DB.prepare("SELECT started_at, finished_at, suggested, error FROM run_log ORDER BY id DESC LIMIT 1").first();
      return json({ lastRun: row ?? null });
    }
    // Human control surface for the safety switches. Without this the kill-switch is
    // only reachable via raw SQL, which makes it useless in the moment you need it.
    if (req.method === "GET" && url.pathname === "/api/settings") {
      const row = await env.DB.prepare(
        "SELECT paused, killed, daily_ceiling_usd, quiet_hours, denylist, autonomy_level FROM settings WHERE id=1"
      ).first();
      return json({ settings: row ?? {} });
    }

    if (req.method === "POST" && url.pathname === "/api/settings") {
      if (req.headers.get("X-Chorus") !== "1") return json({ error: "csrf" }, 400);
      const b = await req.json<any>().catch(() => ({}));
      const sets: string[] = [];
      const vals: any[] = [];
      if (b.paused !== undefined) { sets.push("paused=?"); vals.push(b.paused ? 1 : 0); }
      if (b.killed !== undefined) { sets.push("killed=?"); vals.push(b.killed ? 1 : 0); }
      if (b.daily_ceiling_usd !== undefined) {
        const v = Number(b.daily_ceiling_usd);
        if (!Number.isFinite(v) || v < 0 || v > 100) return json({ error: "ceiling must be 0..100" }, 400);
        sets.push("daily_ceiling_usd=?"); vals.push(v);
      }
      if (b.quiet_hours !== undefined) { sets.push("quiet_hours=?"); vals.push(b.quiet_hours || null); }
      if (b.denylist !== undefined) { sets.push("denylist=?"); vals.push(b.denylist || null); }
      if (!sets.length) return json({ error: "nothing to update" }, 400);
      await env.DB.prepare(`UPDATE settings SET ${sets.join(", ")} WHERE id=1`).bind(...vals).run();
      const row = await env.DB.prepare(
        "SELECT paused, killed, daily_ceiling_usd, quiet_hours, denylist FROM settings WHERE id=1"
      ).first();
      return json({ settings: row });
    }

    if (req.method === "GET" && url.pathname === "/api/insights") {
      const { results } = await env.DB.prepare(
        "SELECT kind, scope, subject_id, payload, confidence, evidence, created_at FROM insight WHERE status='active' ORDER BY confidence DESC, created_at DESC LIMIT 100"
      ).all();
      const pb = await env.DB.prepare(
        "SELECT phase, doc, created_at FROM playbook ORDER BY created_at DESC LIMIT 1"
      ).first();
      return json({ insights: results, playbook: pb ?? null });
    }

    if (req.method === "GET" && url.pathname === "/api/review") {
      const [byPillar, byTier, reasons, spend, weights] = await Promise.all([
        env.DB.prepare(`SELECT s.pillar AS k, SUM(CASE WHEN f.action IN ('posted','posted_edited') THEN 1 ELSE 0 END) AS posted, COUNT(*) AS total FROM feedback f JOIN suggestion s ON s.id=f.suggestion_id GROUP BY s.pillar`).all(),
        env.DB.prepare(`SELECT s.author_tier AS k, SUM(CASE WHEN f.action IN ('posted','posted_edited') THEN 1 ELSE 0 END) AS posted, COUNT(*) AS total FROM feedback f JOIN suggestion s ON s.id=f.suggestion_id GROUP BY s.author_tier`).all(),
        env.DB.prepare(`SELECT reason AS k, COUNT(*) AS n FROM feedback WHERE action='dismissed' AND reason IS NOT NULL GROUP BY reason ORDER BY n DESC LIMIT 10`).all(),
        env.DB.prepare(`SELECT day AS k, SUM(usd) AS usd FROM spend_ledger GROUP BY day ORDER BY day DESC LIMIT 7`).all(),
        env.DB.prepare(`SELECT key AS k, value AS v FROM weights ORDER BY value DESC`).all(),
      ]);
      return json({ byPillar: byPillar.results, byTier: byTier.results, reasons: reasons.results, spend: spend.results, weights: weights.results });
    }
    const m = url.pathname.match(/^\/api\/suggestions\/([^/]+)\/action$/);
    if (req.method === "POST" && m) {
      if (req.headers.get("X-Chorus") !== "1") return json({ error: "bad request" }, 400);
      const id = decodeURIComponent(m[1]);
      const b = (await req.json()) as { action: string; final_text?: string; reason?: string; snooze_hours?: number };
      const st = STATUS[b.action];
      if (!st) return json({ error: "bad action" }, 400);
      const now = Date.now();
      const snooze = b.action === "snoozed" ? now + (b.snooze_hours ?? 2) * 3600_000 : null;
      const res = await env.DB.prepare(
        "UPDATE suggestion SET status=?, acted_at=?, snooze_until=?, final_text=COALESCE(?,final_text), posted_url=COALESCE(?,posted_url), dismiss_reason=COALESCE(?,dismiss_reason) WHERE id=?"
      ).bind(st, now, snooze, b.final_text ?? null, (b as any).posted_url ?? null, b.reason ?? null, id).run();
      if (!res.meta.changes) return json({ error: "not found" }, 404);
      await env.DB.prepare("INSERT INTO feedback (suggestion_id, action, final_text, reason, ts) VALUES (?,?,?,?,?)")
        .bind(id, b.action, b.final_text ?? null, b.reason ?? null, now).run();
      // Mirror to Supermemory chorus:self via a box cron reading new feedback rows (M0), or the
      // Convex act mutation schedules mirrorFeedback (M1). See docs/memory.md.
      return json({ ok: true, status: st });
    }
    return json({ error: "not found" }, 404);
  } catch {
    return json({ error: "internal error" }, 500);
  }
}

async function spendToday(env: Env) {
  const row = await env.DB.prepare("SELECT COALESCE(SUM(usd),0) AS total FROM spend_ledger WHERE day = ?")
    .bind(localDay()).first<{ total: number }>();
  return { day: localDay(), total: row?.total ?? 0 };
}

// Token-authed box surface — the box reads state (budget/weights/settings) and writes results.
async function box(req: Request, env: Env, url: URL): Promise<Response> {
  const p = url.pathname;
  try {
    if (req.method === "GET" && p === "/api/box/spend") return json(await spendToday(env));
    if (req.method === "GET" && p === "/api/box/weights") {
      const { results } = await env.DB.prepare("SELECT key, value FROM weights").all();
      return json({ weights: results });
    }
    if (req.method === "GET" && p === "/api/box/digest") {
      const now = Date.now();
      const top = await env.DB.prepare("SELECT tweet_text, author_handle, score, angle FROM suggestion WHERE status='queued' AND (expires_at IS NULL OR expires_at > ?) ORDER BY score DESC LIMIT 5").bind(now).all();
      const run = await env.DB.prepare("SELECT started_at, finished_at, suggested, error FROM run_log ORDER BY id DESC LIMIT 1").first();
      return json({ top: top.results, spend: await spendToday(env), lastRun: run ?? null });
    }
    if (req.method === "GET" && p === "/api/box/pending-outcomes") {
      const { results } = await env.DB.prepare(
        "SELECT s.id, s.posted_url FROM suggestion s LEFT JOIN outcome o ON o.suggestion_id = s.id WHERE s.status='posted' AND s.posted_url IS NOT NULL AND o.suggestion_id IS NULL LIMIT 50"
      ).all();
      return json({ pending: results });
    }
    if (req.method === "GET" && p === "/api/box/queue") {
      const lim = Math.min(Number(url.searchParams.get("limit") ?? 10) || 10, 50);
      const { results } = await env.DB.prepare(
        "SELECT id, tweet_id, tweet_url, tweet_text, author_handle, score, angle, drafts FROM suggestion WHERE status='queued' AND (expires_at IS NULL OR expires_at > ?) ORDER BY score DESC LIMIT ?"
      ).bind(Date.now(), lim).all();
      return json({ queue: results });
    }
    if (req.method === "GET" && p === "/api/box/feedback") {
      const since = Number(url.searchParams.get("since") ?? 0) || 0;
      const { results } = await env.DB.prepare(
        "SELECT f.id, f.action, f.final_text, f.reason, f.ts, s.author_handle, s.angle, s.factors, o.likes, o.replies FROM feedback f JOIN suggestion s ON s.id=f.suggestion_id LEFT JOIN outcome o ON o.suggestion_id=s.id WHERE f.ts > ? ORDER BY f.ts LIMIT 500"
      ).bind(since).all();
      return json({ feedback: results });
    }
    // Latest stored fingerprint — lets the box skip paid L3 synthesis when nothing moved.
    if (req.method === "GET" && p === "/api/box/insights") {
      const row = await env.DB.prepare(
        "SELECT fingerprint FROM insight WHERE status='active' AND fingerprint IS NOT NULL ORDER BY created_at DESC LIMIT 1"
      ).first<{ fingerprint: string }>();
      const { results } = await env.DB.prepare(
        "SELECT id, kind, scope, subject_id, payload, confidence, evidence, created_at FROM insight WHERE status='active' ORDER BY created_at DESC LIMIT 200"
      ).all();
      return json({ fingerprint: row?.fingerprint ?? null, insights: results });
    }

    if (req.method === "POST" && p === "/api/box/insights") {
      const body = await req.json<any>().catch(() => ({}));
      const list = Array.isArray(body?.insights) ? body.insights : [];
      const fp = body?.fingerprint ?? null;
      const now = Date.now();
      // Deterministic id => a re-run replaces its own row, never duplicates (v0 rule).
      for (const i of list) {
        if (!i?.id || !i?.kind) continue;
        await env.DB.prepare(
          `INSERT INTO insight (id, kind, scope, subject_id, term, payload, confidence, evidence, status, fingerprint, created_at)
           VALUES (?,?,?,?,?,?,?,?,'active',?,?)
           ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, confidence=excluded.confidence,
             evidence=excluded.evidence, status='active', fingerprint=excluded.fingerprint,
             created_at=excluded.created_at, superseded_by=NULL`
        ).bind(i.id, i.kind, i.scope ?? "user", i.subject_id ?? null, i.term ?? null,
               JSON.stringify(i.payload ?? {}), Number(i.confidence ?? 0),
               JSON.stringify(i.evidence ?? []), fp, now).run();
      }
      return json({ stored: list.length });
    }

    if (req.method === "POST" && p === "/api/box/playbook") {
      const b = await req.json<any>().catch(() => ({}));
      if (!b?.doc) return json({ error: "doc required" }, 400);
      await env.DB.prepare(
        "INSERT INTO playbook (phase, doc, fingerprint, created_at) VALUES (?,?,?,?)"
      ).bind(b.phase ?? "cold_start", JSON.stringify(b.doc), b.fingerprint ?? null, Date.now()).run();
      return json({ ok: true });
    }

    if (req.method === "GET" && p === "/api/box/settings") {
      const row = await env.DB.prepare("SELECT paused, daily_ceiling_usd, quiet_hours, denylist, killed, autonomy_level FROM settings WHERE id=1").first();
      return json({ settings: row ?? { paused: 0, daily_ceiling_usd: 0.65, killed: 0, autonomy_level: "L1" } });
    }
    const b = req.method === "POST" ? ((await req.json()) as any) : {};
    const now = Date.now();
    if (req.method === "POST" && p === "/api/box/action") {
      const st = STATUS[b.action];
      if (!st) return json({ error: "bad action" }, 400);
      const snooze = b.action === "snoozed" ? now + (b.snooze_hours ?? 2) * 3600_000 : null;
      const r = await env.DB.prepare(
        "UPDATE suggestion SET status=?, acted_at=?, snooze_until=?, final_text=COALESCE(?,final_text), posted_url=COALESCE(?,posted_url), dismiss_reason=COALESCE(?,dismiss_reason) WHERE id=?"
      ).bind(st, now, snooze, b.final_text ?? null, b.posted_url ?? null, b.reason ?? null, b.id).run();
      if (!r.meta.changes) return json({ error: "not found" }, 404);
      await env.DB.prepare("INSERT INTO feedback (suggestion_id, action, final_text, reason, ts) VALUES (?,?,?,?,?)")
        .bind(b.id, b.action, b.final_text ?? null, b.reason ?? null, now).run();
      return json({ ok: true, status: st });
    }
    if (req.method === "POST" && (p === "/api/box/ingest" || p === "/api/ingest")) {
      await env.DB.prepare(
        `INSERT INTO suggestion (id, tweet_id, tweet_url, tweet_text, author_handle, author_tier, score, factors, pillar, angle, drafts, rationale, target, status, created_at, expires_at)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'queued',?,?)
         ON CONFLICT(tweet_id) DO UPDATE SET score=excluded.score, factors=excluded.factors, angle=excluded.angle, drafts=excluded.drafts, rationale=excluded.rationale, target=excluded.target`
      ).bind(b.id, b.tweet_id, b.tweet_url ?? null, b.tweet_text, b.author_handle, b.author_tier ?? null,
        b.score, JSON.stringify(b.factors ?? {}), b.pillar ?? null, b.angle ?? null,
        JSON.stringify(b.drafts ?? []), b.rationale ?? null, b.target ?? "reply", now, b.expires_at ?? null).run();
      return json({ ok: true });
    }
    if (req.method === "POST" && (p === "/api/box/spend" || p === "/api/spend")) {
      await env.DB.prepare("INSERT INTO spend_ledger (day, source, usd, ts) VALUES (?,?,?,?)")
        .bind(localDay(), b.source, b.usd, now).run();
      return json({ ok: true });
    }
    if (req.method === "POST" && p === "/api/box/forget") {
      if (!b.handle) return json({ error: "handle required" }, 400);
      const r = await env.DB.prepare("DELETE FROM suggestion WHERE author_handle = ?").bind(b.handle).run();
      return json({ ok: true, removed: r.meta.changes });
    }
    if (req.method === "POST" && p === "/api/box/weights") {
      await env.DB.prepare("INSERT INTO weights (key, value, updated_at) VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at")
        .bind(b.key, b.value, now).run();
      return json({ ok: true });
    }
    if (req.method === "POST" && p === "/api/box/run-log") {
      if (b.action === "start") {
        const r = await env.DB.prepare("INSERT INTO run_log (started_at) VALUES (?)").bind(now).run();
        return json({ id: r.meta.last_row_id });
      }
      await env.DB.prepare("UPDATE run_log SET finished_at=?, suggested=?, error=? WHERE id=?")
        .bind(now, b.suggested ?? null, b.error ?? null, b.id).run();
      return json({ ok: true });
    }
    if (req.method === "POST" && p === "/api/box/outcome") {
      await env.DB.prepare(
        "INSERT INTO outcome (suggestion_id, likes, replies, profile_clicks, measured_at) VALUES (?,?,?,?,?) ON CONFLICT(suggestion_id) DO UPDATE SET likes=excluded.likes, replies=excluded.replies, profile_clicks=excluded.profile_clicks, measured_at=excluded.measured_at"
      ).bind(b.suggestion_id, b.likes ?? null, b.replies ?? null, b.profile_clicks ?? null, now).run();
      return json({ ok: true });
    }
    return json({ error: "not found" }, 404);
  } catch {
    return json({ error: "internal error" }, 500);
  }
}
