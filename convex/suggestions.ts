import { query, mutation } from "./_generated/server";
import { internal } from "./_generated/api";
import { v } from "convex/values";

// Reactive: the dashboard subscribes → live updates, no polling (supersedes the D1 fetch loop).
export const listQueued = query({
  args: { status: v.optional(v.string()), limit: v.optional(v.number()) },
  handler: async (ctx, { status = "queued", limit = 50 }) => {
    const now = Date.now();
    const rows = await ctx.db
      .query("suggestions")
      .withIndex("by_status_score", (q) => q.eq("status", status))
      .order("desc")
      .take(Math.min(limit ?? 50, 200));
    // hide expired; include due-snoozed when viewing queued
    const dueSnoozed = status === "queued"
      ? (await ctx.db.query("suggestions").withIndex("by_status_score", (q) => q.eq("status", "snoozed")).collect())
          .filter((s) => s.snoozeUntil != null && s.snoozeUntil <= now)
      : [];
    return [...rows, ...dueSnoozed]
      .filter((s) => s.expiresAt == null || s.expiresAt > now)
      .sort((a, b) => b.score - a.score);
  },
});

// Box → queue (idempotent per tweet). Reaches self-hosted Convex behind the tunnel (G3).
export const enqueue = mutation({
  args: {
    tweetId: v.string(), tweetUrl: v.optional(v.string()), tweetText: v.string(),
    authorHandle: v.string(), authorTier: v.optional(v.string()), score: v.number(),
    factors: v.optional(v.any()), pillar: v.optional(v.string()), angle: v.optional(v.string()),
    drafts: v.array(v.string()), rationale: v.optional(v.string()), expiresAt: v.optional(v.number()),
  },
  handler: async (ctx, a) => {
    const existing = await ctx.db.query("suggestions").withIndex("by_tweet", (q) => q.eq("tweetId", a.tweetId)).first();
    if (existing) { // upsert: refresh scoring
      await ctx.db.patch(existing._id, { score: a.score, factors: a.factors, angle: a.angle, drafts: a.drafts, rationale: a.rationale });
      return existing._id;
    }
    return await ctx.db.insert("suggestions", { ...a, status: "queued", createdAt: Date.now() });
  },
});

const STATUS: Record<string, string> = { posted: "posted", posted_edited: "posted", dismissed: "dismissed", snoozed: "snoozed" };

export const act = mutation({
  args: { id: v.id("suggestions"), action: v.string(), finalText: v.optional(v.string()), reason: v.optional(v.string()), snoozeHours: v.optional(v.number()) },
  handler: async (ctx, { id, action, finalText, reason, snoozeHours }) => {
    const status = STATUS[action];
    if (!status) throw new Error(`bad action: ${action}`);
    const doc = await ctx.db.get(id);
    if (!doc) throw new Error("suggestion not found");
    const now = Date.now();
    await ctx.db.patch(id, {
      status, actedAt: now,
      ...(action === "snoozed" ? { snoozeUntil: now + (snoozeHours ?? 2) * 3600_000 } : {}),
      ...(finalText ? { finalText } : {}), ...(reason ? { dismissReason: reason } : {}),
    });
    await ctx.db.insert("feedback", { suggestionId: id, action, finalText, reason, ts: now });
    // Mirror into Supermemory chorus:self so it becomes profile.dynamic (docs/memory.md).
    await ctx.scheduler.runAfter(0, internal.actions.mirrorFeedback, {
      handle: doc.authorHandle, action, finalText, angle: doc.angle,
    });
    return { ok: true, status };
  },
});
