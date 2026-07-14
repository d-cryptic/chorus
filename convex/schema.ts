import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

// Convex = reactive operational state + durable orchestration (M1). Semantic/identity memory
// lives in Supermemory, not here. See ../docs/data-architecture.md. Mirrors ../dashboard/schema.sql.
export default defineSchema({
  suggestions: defineTable({
    tweetId: v.string(),
    tweetUrl: v.optional(v.string()),
    tweetText: v.string(),
    authorHandle: v.string(),
    authorTier: v.optional(v.string()),
    score: v.number(),
    factors: v.optional(v.any()),
    pillar: v.optional(v.string()),
    angle: v.optional(v.string()),
    drafts: v.array(v.string()),
    rationale: v.optional(v.string()),
    status: v.string(), // queued | posted | dismissed | snoozed | expired
    createdAt: v.number(),
    expiresAt: v.optional(v.number()),
    snoozeUntil: v.optional(v.number()),
    actedAt: v.optional(v.number()),
    finalText: v.optional(v.string()),
    dismissReason: v.optional(v.string()),
  })
    .index("by_status_score", ["status", "score"])
    .index("by_tweet", ["tweetId"]),

  feedback: defineTable({
    suggestionId: v.id("suggestions"),
    action: v.string(),
    finalText: v.optional(v.string()),
    reason: v.optional(v.string()),
    ts: v.number(),
  }).index("by_suggestion", ["suggestionId"]),

  spendLedger: defineTable({
    day: v.string(), source: v.string(), usd: v.number(), ts: v.number(),
  }).index("by_day", ["day"]),

  // FE1 — how a posted reply performed → reward for rank-tune.
  outcome: defineTable({
    suggestionId: v.id("suggestions"),
    likes: v.optional(v.number()),
    replies: v.optional(v.number()),
    profileClicks: v.optional(v.number()),
    measuredAt: v.number(),
  }).index("by_suggestion", ["suggestionId"]),

  // G1 — rank-tune writes; opportunity-rank reads at run start.
  weights: defineTable({ key: v.string(), value: v.number(), updatedAt: v.number() })
    .index("by_key", ["key"]),

  // FE4 — singleton operational settings (query .first()).
  settings: defineTable({
    paused: v.boolean(),
    dailyCeilingUsd: v.number(),
    quietHours: v.optional(v.string()),
    denylist: v.optional(v.array(v.string())),
  }),

  // G5 — one row per cycle → dashboard heartbeat.
  runLog: defineTable({
    startedAt: v.number(),
    finishedAt: v.optional(v.number()),
    suggested: v.optional(v.number()),
    error: v.optional(v.string()),
  }),
});
