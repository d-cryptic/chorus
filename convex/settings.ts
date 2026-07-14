import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

const DEFAULTS = { paused: false, dailyCeilingUsd: 0.65, quietHours: undefined, denylist: [] as string[] };

export const get = query({
  args: {},
  handler: async (ctx) => (await ctx.db.query("settings").first()) ?? DEFAULTS,
});

// FE4 — toggled from the dashboard header; the daily cycle reads this before doing anything.
export const update = mutation({
  args: { paused: v.optional(v.boolean()), dailyCeilingUsd: v.optional(v.number()), quietHours: v.optional(v.string()), denylist: v.optional(v.array(v.string())) },
  handler: async (ctx, patch) => {
    const row = await ctx.db.query("settings").first();
    if (!row) return await ctx.db.insert("settings", { ...DEFAULTS, ...patch });
    await ctx.db.patch(row._id, patch);
  },
});
