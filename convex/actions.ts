"use node";
import { internalAction } from "./_generated/server";
import { api } from "./_generated/api";
import { v } from "convex/values";

// Convex schedules + records; the box runs the LLM/browser cycle (Hermes) and calls back
// enqueue()/spend.record(). Self-hosted Convex + box are co-located behind the tunnel (G3).
// Env (Convex dashboard): HERMES_CYCLE_URL, HERMES_OUTCOME_URL, HERMES_TOKEN, SUPERMEMORY_API_KEY.

export const runDailyCycle = internalAction({
  args: {},
  handler: async (ctx) => {
    const settings = await ctx.runQuery(api.settings.get, {});
    if (settings.paused) return;
    const runId = await ctx.runMutation(api.runs.start, {});
    try {
      const url = process.env.HERMES_CYCLE_URL;
      if (!url) throw new Error("HERMES_CYCLE_URL not set");
      const res = await fetch(url, { method: "POST", headers: { authorization: `Bearer ${process.env.HERMES_TOKEN ?? ""}` } });
      const body = (await res.json().catch(() => ({}))) as { suggested?: number };
      await ctx.runMutation(api.runs.finish, { id: runId, suggested: body.suggested ?? 0 });
    } catch (e) {
      await ctx.runMutation(api.runs.finish, { id: runId, error: String(e) });
      // TODO(G5): Telegram alert on cycle failure.
    }
  },
});

export const measureOutcomes = internalAction({
  args: {},
  handler: async () => {
    const url = process.env.HERMES_OUTCOME_URL;
    if (url) await fetch(url, { method: "POST", headers: { authorization: `Bearer ${process.env.HERMES_TOKEN ?? ""}` } }).catch(() => {});
  },
});

// Mirror a dashboard action into Supermemory chorus:self → becomes profile.dynamic (docs/memory.md).
export const mirrorFeedback = internalAction({
  args: { handle: v.string(), action: v.string(), finalText: v.optional(v.string()), angle: v.optional(v.string()) },
  handler: async (_ctx, a) => {
    const key = process.env.SUPERMEMORY_API_KEY;
    if (!key) return;
    const Supermemory = (await import("supermemory")).default;
    const sm = new Supermemory({ apiKey: key });
    await sm.add({
      content: `${a.action} reply to @${a.handle}: "${a.finalText ?? ""}" (angle: ${a.angle ?? ""})`,
      containerTags: ["chorus:self"],
      metadata: { kind: "feedback", action: a.action, ts: Date.now() },
    });
  },
});
