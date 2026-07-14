import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

// FE1 — outcome-track (on the box) calls this after measuring a posted reply's metrics.
export const set = mutation({
  args: { suggestionId: v.id("suggestions"), likes: v.optional(v.number()), replies: v.optional(v.number()), profileClicks: v.optional(v.number()) },
  handler: async (ctx, a) => {
    const existing = await ctx.db.query("outcome").withIndex("by_suggestion", (q) => q.eq("suggestionId", a.suggestionId)).first();
    if (existing) await ctx.db.patch(existing._id, { ...a, measuredAt: Date.now() });
    else await ctx.db.insert("outcome", { ...a, measuredAt: Date.now() });
  },
});

// posted suggestions still missing an outcome row → work list for outcome-track.
export const needingMeasurement = query({
  args: {},
  handler: async (ctx) => {
    const posted = await ctx.db.query("suggestions").withIndex("by_status_score", (q) => q.eq("status", "posted")).collect();
    const out: typeof posted = [];
    for (const s of posted) {
      const oc = await ctx.db.query("outcome").withIndex("by_suggestion", (q) => q.eq("suggestionId", s._id)).first();
      if (!oc) out.push(s);
    }
    return out;
  },
});
