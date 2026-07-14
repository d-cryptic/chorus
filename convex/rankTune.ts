import { internalMutation } from "./_generated/server";

// G1 — the learning loop, running IN Convex over feedback (+ outcomes). Weekly cron.
// Nudges each factor weight toward factors that discriminate accepted from dismissed.
const FACTORS = ["angle", "pillar", "author", "upside", "fresh", "rel", "saturation", "risk"] as const;
const DEFAULTS: Record<string, number> = {
  angle: 0.24, pillar: 0.22, author: 0.18, upside: 0.16, fresh: 0.12, rel: 0.08, saturation: 0.15, risk: 0.2,
};

export const run = internalMutation({
  args: {},
  handler: async (ctx) => {
    const now = Date.now();
    const since = now - 14 * 24 * 3600_000;
    const fb = (await ctx.db.query("feedback").collect()).filter((f) => f.ts >= since);
    if (fb.length < 5) return { skipped: "insufficient feedback" };

    const pos: Record<string, number> = {}, neg: Record<string, number> = {};
    let nPos = 0, nNeg = 0;
    for (const k of FACTORS) { pos[k] = 0; neg[k] = 0; }
    for (const f of fb) {
      const s = await ctx.db.get(f.suggestionId);
      if (!s || !s.factors) continue;
      // outcome-weighted (FE1): a posted reply that flopped counts less.
      const oc = await ctx.db.query("outcome").withIndex("by_suggestion", (q) => q.eq("suggestionId", f.suggestionId)).first();
      const w = oc ? Math.min(2, 0.5 + ((oc.likes ?? 0) + 2 * (oc.replies ?? 0)) / 10) : 1;
      const positive = f.action === "posted" || f.action === "posted_edited";
      if (positive) { nPos += w; for (const k of FACTORS) pos[k] += Number(s.factors[k] ?? 0) * w; }
      else { nNeg += 1; for (const k of FACTORS) neg[k] += Number(s.factors[k] ?? 0); }
    }
    if (!nPos || !nNeg) return { skipped: "need both accepted and dismissed" };

    for (const k of FACTORS) {
      const discriminative = pos[k] / nPos - neg[k] / nNeg; // >0 ⇒ predicts acceptance
      const cur = await ctx.db.query("weights").withIndex("by_key", (q) => q.eq("key", k)).first();
      const base = cur?.value ?? DEFAULTS[k];
      const next = Math.max(0.01, Math.min(0.5, base + 0.05 * discriminative));
      if (cur) await ctx.db.patch(cur._id, { value: next, updatedAt: now });
      else await ctx.db.insert("weights", { key: k, value: next, updatedAt: now });
    }
    return { tuned: FACTORS.length, from: fb.length };
  },
});
