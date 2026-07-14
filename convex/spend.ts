import { query, mutation } from "./_generated/server";
import { v } from "convex/values";
const day = () => new Date(Date.now() + 330 * 60000).toISOString().slice(0, 10); // IST

export const today = query({ args: {}, handler: async (ctx) => {
  const rows = await ctx.db.query("spendLedger").withIndex("by_day", (q) => q.eq("day", day())).collect();
  return { day: day(), total: rows.reduce((s, r) => s + r.usd, 0) };
}});

export const record = mutation({ args: { source: v.string(), usd: v.number() },
  handler: async (ctx, { source, usd }) => { await ctx.db.insert("spendLedger", { day: day(), source, usd, ts: Date.now() }); } });
