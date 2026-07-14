import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

export const latest = query({ args: {}, handler: async (ctx) =>
  await ctx.db.query("runLog").order("desc").first() });

export const start = mutation({ args: {}, handler: async (ctx) =>
  await ctx.db.insert("runLog", { startedAt: Date.now() }) });

export const finish = mutation({
  args: { id: v.id("runLog"), suggested: v.optional(v.number()), error: v.optional(v.string()) },
  handler: async (ctx, { id, suggested, error }) =>
    await ctx.db.patch(id, { finishedAt: Date.now(), suggested, error }),
});
