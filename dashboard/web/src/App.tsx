import { useEffect, useState, useCallback, useRef } from "react";
import { Tweet, GifChip, Counter, X_BLUE, DIM, LINE } from "@/components/ui/tweet";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { MediaGrid } from "@/components/ui/media";
import { Toaster, toast } from "sonner";
import { cn } from "@/lib/utils";
import { RefreshCw, Pause, Play, OctagonX, Activity, Download, Zap } from "lucide-react";

const ME = "barundebnath";
const REASONS = ["bad take", "bad tweet", "too late", "off-voice"];

type Sug = {
  id: string; tweet_id?: string; tweet_url?: string; tweet_text: string;
  author_handle: string; author_tier?: string; score: number; pillar?: string;
  angle?: string; drafts: string; factors?: string; target?: string;
  gif?: string | null; thread?: string; media?: string; created_at?: number;
};

const api = (p: string) => fetch(p, { credentials: "same-origin" }).then((r) => r.json());
const parse = (x: any, f: any) => { try { return typeof x === "string" ? JSON.parse(x) : x ?? f; } catch { return f; } };
const post = async (p: string, body: any) => {
  // fetch() does NOT reject on 4xx/5xx. Without this check a failed action still
  // removed the card and toasted success — you would think you had acted when you hadn't.
  const r = await fetch(p, { method: "POST", credentials: "same-origin",
                             headers: { "content-type": "application/json", "X-Chorus": "1" },
                             body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${p} -> ${r.status}`);
  return r.json();
};

export default function App() {
  const [status, setStatus] = useState("queued");
  const [items, setItems] = useState<Sug[]>([]);
  const [counts, setCounts] = useState<any>({});
  const [spend, setSpend] = useState(0);
  const [credits, setCredits] = useState<number | null>(null);
  // measured from run_log balances, not a magic constant that was ~50x optimistic
  const [burn, setBurn] = useState<number | null>(null);
  // vendor identity is CONFIG, not code — see /api/status
  const [provider, setProvider] = useState<{ name: string; url?: string } | null>(null);
  const [beat, setBeat] = useState("");
  const [alerts, setAlerts] = useState<any[]>([]);
  const [cfg, setCfg] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [cursor, setCursor] = useState(0);          // j/k focus
  const [pick, setPick] = useState<Record<string, number>>({});  // per-suggestion draft index
  const [editing, setEditing] = useState<string | null>(null);
  const [dismissing, setDismissing] = useState<string | null>(null);
  const [help, setHelp] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [fetchState, setFetchState] = useState<null | "queued" | "running">(null);
  const undoRef = useRef<any>(null);
  const seenFast = useRef<Set<string>>(new Set());
  const [notify, setNotify] = useState<boolean>(
    typeof Notification !== "undefined" && Notification.permission === "granted");

  const [insights, setInsights] = useState<any>(null);

  const load = useCallback(async () => {
    setLoading(true);
    if (status === "insights") {
      const [rv, ins] = await Promise.all([
        api(`/api/review`).catch(() => ({})),
        api(`/api/insights`).catch(() => ({ insights: [], playbook: null })),
      ]);
      setInsights({ ...rv, ...ins }); setLoading(false); return;
    }
    const [sg, sp, st, cf] = await Promise.all([
      api(`/api/suggestions?status=${status === "posts" ? "queued&target=post" : status}`),
      api(`/api/spend`).catch(() => ({ total: 0 })),
      api(`/api/status`).catch(() => ({})),
      api(`/api/settings`).catch(() => ({ settings: null })),
    ]);
    setItems(sg.suggestions || []); setCounts(sg.counts || {});
    setSpend(Number(sp.total) || 0); setCfg(cf.settings || null);
    setAlerts(st.alerts || []); setCredits(st.lastRun?.credits ?? null); setBurn(st.creditsPerDay ?? null); setProvider(st.provider ?? null);
    const r = st.lastRun;
    setBeat(r?.started_at ? `${Math.round((Date.now() - r.started_at) / 3.6e6)}h ago · ${r.suggested ?? 0}` : "no cycle yet");
    setCursor(0); setLoading(false);
  }, [status]);
  useEffect(() => { load(); }, [load]);

  /** The fast lane's whole value is a ~25min window; an alert in /var/log is worthless.
   *  Telegram needs a token only the user can mint, so use the browser: zero credentials,
   *  works whenever this tab is open. Poll is cheap (the Worker reads D1, no provider). */
  useEffect(() => {
    if (status !== "queued") return;
    const tick = async () => {
      try {
        const d = await api(`/api/suggestions?status=queued`);
        const fast = (d.suggestions || []).filter(
          (x: Sug) => parse(x.factors, {})?.fast_lane && !seenFast.current.has(x.id));
        for (const f of fast) {
          seenFast.current.add(f.id);
          const age = parse(f.factors, {})?.age_min;
          if (notify && typeof Notification !== "undefined" && Notification.permission === "granted") {
            new Notification(`⚡ reply now — @${f.author_handle}`, {
              body: `${age}m old · ${(f.tweet_text || "").slice(0, 90)}`,
              tag: f.id, requireInteraction: true,
            });
          }
          toast(`⚡ @${f.author_handle} · ${age}m old — reply now`, { duration: 20000 });
        }
        if (fast.length) load();
      } catch { /* a poll failure must never break the page */ }
    };
    const iv = setInterval(tick, 60000);   // the box polls every 10m; 1m keeps latency low
    return () => clearInterval(iv);
  }, [status, notify, load]);

  const flash = (msg: string, undo?: () => void) => {
    undoRef.current = undo ?? null;
    toast(msg, undo ? { action: { label: "Undo (z)", onClick: () => undo() }, duration: 6000 } : { duration: 2000 });
  };

  const act = async (s: Sug, action: string, extra: any = {}) => {
    const idx = pick[s.id] ?? 0;
    const at = items.findIndex((i) => i.id === s.id);
    setItems((x) => x.filter((i) => i.id !== s.id));           // optimistic
    setCursor((c) => Math.min(c, Math.max(0, items.length - 2)));
    try {
      await post(`/api/suggestions/${encodeURIComponent(s.id)}/action`, { action, draft_index: idx, ...extra });
    } catch (e) {
      // roll the card back where it was and say so — silently losing an action is worse
      setItems((x) => { const n = [...x]; n.splice(Math.max(0, at), 0, s); return n; });
      toast.error(`${action.replace("_", " ")} failed — still queued`);
      return;
    }
    flash(action.replace("_", " "), async () => {
      try {
        await post(`/api/suggestions/${encodeURIComponent(s.id)}/action`, { action: "queued" });
        setItems((x) => [s, ...x]); toast.dismiss();
      } catch { toast.error("undo failed"); }
    });
  };

  const draftsOf = (s: Sug) => parse(s.drafts, []) as string[];
  /** Stable per-suggestion rotation so the "hero" slot is not always index 0. */
  const heroOffset = (s: Sug) => {
    const n = draftsOf(s).length || 1;
    let h = 0;
    for (const c of s.id) h = ((h << 5) - h + c.charCodeAt(0)) | 0;
    return Math.abs(h) % n;
  };
  /** display order -> the ORIGINAL draft index, which is what we record. */
  const orderOf = (s: Sug) => {
    const n = draftsOf(s).length;
    const off = heroOffset(s);
    return Array.from({ length: n }, (_, i) => (i + off) % n);
  };
  const selected = (s: Sug) => draftsOf(s)[pick[s.id] ?? heroOffset(s)] ?? "";
  const intent = (s: Sug, text: string) =>
    // a post is standalone: never attach in_reply_to, even if a source ref exists
    `https://x.com/intent/post?text=${encodeURIComponent(text)}` +
    (s.target !== "post" && s.tweet_id ? `&in_reply_to=${encodeURIComponent(s.tweet_id)}` : "");
  const postOnX = (s: Sug) => {
    const t = selected(s);
    window.open(s.target === "retweet" && s.tweet_id
      ? `https://x.com/intent/retweet?tweet_id=${s.tweet_id}` : intent(s, t), "_blank");
    act(s, "posted", { posted_url: null });
  };

  // ---- keyboard triage loop ----
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (editing || dismissing) return;
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      const s = items[cursor];
      if (e.key === "?") { setHelp((v) => !v); return; }
      if (e.key === "z" && undoRef.current) { undoRef.current(); undoRef.current = null; return; }
      if (!s) return;
      if (e.key === "j") setCursor((c) => Math.min(c + 1, items.length - 1));
      else if (e.key === "k") setCursor((c) => Math.max(c - 1, 0));
      else if (["1", "2", "3"].includes(e.key)) {
        const ord = orderOf(s);                       // display position -> true index
        const i = Number(e.key) - 1;
        if (i < ord.length) setPick((p) => ({ ...p, [s.id]: ord[i] }));
      }
      else if (e.key === "p") postOnX(s);
      else if (e.key === "e") setEditing(s.id);
      else if (e.key === "s") act(s, "snoozed");
      else if (e.key === "x") setDismissing(s.id);
      else if (e.key === "c") navigator.clipboard.writeText(selected(s)).then(() => flash("copied"));
      else if (e.key === "o" && (s.tweet_url || s.tweet_id))
        window.open(s.tweet_url || `https://x.com/i/web/status/${s.tweet_id}`, "_blank");
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [items, cursor, pick, editing, dismissing]);

  /** The Worker holds no provider key by design, so it cannot fetch: it raises a flag and
   *  the box (which owns the keys) claims it within ~1m and runs a real cycle.
   *
   *  This used to fire-and-forget then blind-reload after 90s -- against a 5-minute cron, so
   *  it reliably reloaded BEFORE anything had happened, found nothing, and looked broken.
   *  Now we watch run_log via /api/status and report what actually occurred: claimed ->
   *  running -> N new. If the box never picks it up we say THAT, rather than silently
   *  showing a stale queue. */
  const fetchNow = async () => {
    setFetching(true);
    const baseline = await api(`/api/status`).then((r: any) => r?.lastRun?.started_at ?? 0).catch(() => 0);
    try {
      await post(`/api/fetch`, {});
    } catch { toast.error("Could not queue a fetch"); setFetching(false); return; }
    setFetchState("queued");

    const started = Date.now();
    const DEADLINE = 4 * 60000;     // box claims every ~1m; 4m means it is genuinely not running
    let sawRun = false;
    const tick = async () => {
      if (Date.now() - started > DEADLINE) {
        setFetching(false); setFetchState(null);
        toast.error(sawRun ? "The box started a cycle but never finished it — check /var/log/chorus.log"
                           : "The box never picked this up. Is the fetch_watch cron alive?",
                    { duration: 8000 });
        return;
      }
      const st: any = await api(`/api/status`).catch(() => null);
      const run = st?.lastRun;
      if (run?.started_at && run.started_at > baseline) {
        sawRun = true;
        if (run.finished_at) {                       // a full cycle completed
          setFetching(false); setFetchState(null);
          await load();
          if (run.error) toast.error(`Cycle failed: ${String(run.error).slice(0, 80)}`, { duration: 8000 });
          else toast.success(run.suggested ? `${run.suggested} new suggestion${run.suggested === 1 ? "" : "s"}`
                                           : "Cycle ran — nothing new cleared the bar", { duration: 5000 });
          return;
        }
        setFetchState("running");                    // claimed, still working
      }
      setTimeout(tick, 2500);
    };
    setTimeout(tick, 2000);
  };

  const setSetting = async (patch: any) => {
    const r = await post(`/api/settings`, patch).catch(() => null);
    if (r?.settings) { setCfg(r.settings); flash(Object.keys(patch)[0] + " updated"); }
  };

  const blocked =
    cfg?.killed ? { tone: "var(--destructive)", title: "Kill-switch on — nothing runs", cta: "Release", act: () => setSetting({ killed: 0 }) }
    : cfg?.paused ? { tone: "var(--warning)", title: "Paused — cycles stopped (resumable)", cta: "Resume", act: () => setSetting({ paused: 0 }) }
    // key off the CURRENT balance, not a historical error row
    : credits !== null && credits <= 0
      // The vendor name/URL arrive from /api/status at RUNTIME. Hardcoding them compiled the
      // name of a third-party X scraper into a bundle committed to a PUBLIC repo — the exact
      // exposure a suggest-only, zero-ban-risk design exists to avoid.
      ? { tone: "var(--destructive)", title: "Provider credits exhausted",
          cta: provider ? `Top up ${provider.name} (100k = $1)` : "Top up your read provider",
          href: provider?.url }
    : null;

  return (
    <TooltipProvider delayDuration={300}>
    <div className="min-h-screen flex justify-center" style={{ background: "var(--background)", color: "var(--foreground)" }}>
      {/* mirror of the right rail: balances the composition so the FEED is centred */}
      <div className="hidden lg:block w-[350px] shrink-0" aria-hidden />

      <main className="w-full max-w-[600px]" style={{ borderLeft: `1px solid var(--border)`, borderRight: `1px solid var(--border)`, background: "linear-gradient(180deg, color-mix(in oklch, var(--primary) 3%, transparent), transparent 260px)" }}>
        <header className="sticky top-0 z-10 flex items-center gap-3 px-4 h-[53px] backdrop-blur"
                style={{ background: "color-mix(in oklch, var(--background) 78%, transparent)", borderBottom: `1px solid var(--border)` }}>
          <span className="text-[17px] leading-none" style={{ color: "var(--muted-foreground)" }}>✳</span>
          <h1 className="text-[19px] font-semibold tracking-[-0.02em]">Queue</h1>
          <span className="mono text-[11px] flex items-center gap-1.5 tracking-tight" style={{ color: "var(--muted-foreground)" }}>
            <Activity size={11} /> {beat}
          </span>
          <div className="ml-auto flex items-center gap-1">
            <button onClick={() => setSetting({ paused: cfg?.paused ? 0 : 1 })} title="pause / resume"
                    className="p-2 rounded-full hover:bg-secondary">
              {cfg?.paused ? <Play size={16} style={{ color: "var(--warning)" }} /> : <Pause size={16} style={{ color: DIM }} />}
            </button>
            <button onClick={() => { if (cfg?.killed || confirm("Kill-switch: halt every paid call now?")) setSetting({ killed: cfg?.killed ? 0 : 1 }); }}
                    title="kill-switch" className="p-2 rounded-full hover:bg-secondary">
              <OctagonX size={16} style={{ color: cfg?.killed ? "var(--destructive)" : DIM }} />
            </button>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={async () => {
                    if (typeof Notification === "undefined") return toast.error("no notification support");
                    const p = await Notification.requestPermission();
                    setNotify(p === "granted");
                    toast(p === "granted" ? "⚡ alerts armed — keep this tab open" : "notifications blocked");
                  }}
                  className="p-2 rounded-full hover:bg-secondary">
                  <Zap size={16} style={{ color: notify ? "var(--primary)" : "var(--muted-foreground)" }} />
                </button>
              </TooltipTrigger>
              <TooltipContent>
                {notify ? "⚡ alerts on — you'll be pinged inside the ~25min window" : "arm ⚡ reply-now alerts"}
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <button onClick={load} className="p-2 rounded-full hover:bg-secondary">
                  <RefreshCw size={16} style={{ color: DIM }} />
                </button>
              </TooltipTrigger>
              <TooltipContent>re-read the queue from the database. Does NOT fetch new tweets — use "Fetch new" for that.</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <button onClick={fetchNow} disabled={fetching}
                  className="ml-1.5 rounded-full px-3 py-1.5 text-[12.5px] font-medium disabled:opacity-40
                             flex items-center gap-1.5 transition-colors hover:bg-[var(--secondary)]"
                  style={{ border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>
                  <Download size={12.5} className={fetching ? "animate-pulse" : undefined} />
                  {fetchState === "running" ? "Box is fetching…"
                    : fetchState === "queued" ? "Waiting for box…"
                    : "Fetch new"}
                </button>
              </TooltipTrigger>
              <TooltipContent>pull new tweets + replies from X now. The box claims this within ~1 min and runs a real cycle.</TooltipContent>
            </Tooltip>
          </div>
        </header>

        <Tabs value={status} onValueChange={setStatus}>
          <TabsList>
            {["queued", "posts", "posted", "dismissed", "insights"].map((t) => (
              <TabsTrigger key={t} value={t}>
                {t}{counts[t] ? <span className="mono ml-1.5 text-[11px] tabular-nums opacity-50">{counts[t]}</span> : null}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {blocked && <Blocked {...blocked} />}

        {loading ? <p className="py-16 text-center text-[15px]" style={{ color: DIM }}>Loading…</p>
          : status === "insights" ? <Insights data={insights} />
          : items.length === 0 && !blocked ? <Empty beat={beat} onRefresh={load} />
          : items.map((s, i) => (
              <Card key={s.id} i={i} s={s} focused={i === cursor} onFocus={() => setCursor(i)}
                    order={orderOf(s)}
                    pick={pick[s.id] ?? heroOffset(s)} setPick={(n: number) => setPick((p) => ({ ...p, [s.id]: n }))}
                    editing={editing === s.id} setEditing={(v: boolean) => setEditing(v ? s.id : null)}
                    dismissing={dismissing === s.id} setDismissing={(v: boolean) => setDismissing(v ? s.id : null)}
                    act={act} postOnX={postOnX} />
            ))}
        <div className="h-24" />
      </main>

      <aside className="hidden lg:block w-[350px] shrink-0 px-6 py-3 sticky top-0 h-screen">
        <div className="rounded-2xl p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <h2 className="text-[12px] font-medium uppercase tracking-[0.14em] mb-3" style={{ color: "var(--muted-foreground)" }}>Agent</h2>
          <Stat label="spend today" value={`$${spend.toFixed(2)}`} />
          {credits !== null && (
            <Stat label="provider credits" danger={credits < 5000}
                  value={credits >= 1000 ? `${Math.round(credits / 1000)}k` : String(credits)}
                  sub={burn ? `~${Math.max(0, Math.floor(credits / burn))}d runway · ${(burn / 1000).toFixed(1)}k/day`
                             : "runway: measuring…"} />
          )}
          <Stat label="queued · acted today" value={`${counts.queued ?? 0} · ${(counts.posted ?? 0) + (counts.dismissed ?? 0)}`} />
          <Stat label="state" danger={Boolean(cfg?.killed)}
                value={cfg?.killed ? "KILLED" : cfg?.paused ? "paused" : "running"} />
          <button onClick={() => setHelp(true)}
            className="mono mt-4 w-full rounded-lg py-2 text-[11px] transition-colors hover:bg-[var(--secondary)]"
            style={{ border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>
            shortcuts  ?
          </button>
        </div>
      </aside>

      <Dialog open={help} onOpenChange={setHelp}><DialogContent><Help /></DialogContent></Dialog>
      <Toaster theme="dark" position="bottom-center"
        toastOptions={{ style: { background: "var(--card)", border: `1px solid ${LINE}`, color: "var(--foreground)", borderRadius: 9999 } }} />
    </div>
    </TooltipProvider>
  );
}

function scoreColor(n: number) { return n >= 0.8 ? "var(--primary)" : n >= 0.6 ? "var(--foreground)" : DIM; }

function Card({ s, i, focused, onFocus, order, pick, setPick, editing, setEditing, dismissing, setDismissing, act, postOnX }: any) {
  const drafts: string[] = parse(s.drafts, []);
  const thread: string[] = parse(s.thread, []);
  const longform: string = s.longform || "";   // Premium Plus single post; depth without separable beats
  // What this card actually publishes. Mirrors post_gen.classify_shape so the UI and the
  // generator cannot disagree about what a suggestion IS.
  const shape: "post" | "thread" | "longform" =
    longform ? "longform" : thread.length > 0 ? "thread" : "post";
  const url = s.tweet_url || (s.tweet_id ? `https://x.com/i/web/status/${s.tweet_id}` : null);
  const body = drafts[pick] ?? "";
  const [text, setText] = useState(body);
  const [reason, setReason] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { if (focused) ref.current?.scrollIntoView({ block: "nearest" }); }, [focused]);
  useEffect(() => { setText(body); }, [body]);
  const isRT = s.target === "retweet";
  const isPost = s.target === "post";

  return (
    <div ref={ref} onClick={onFocus}
         style={{
           // Separation must track HIERARCHY. A card is a compound object (target tweet +
           // your draft + actions) whose parts are already hairline-separated; bounding the
           // whole card with that same hairline made the stream undifferentiated -- the next
           // card's meta row read as this card's footer. A gutter of page background makes
           // each card a distinct slab without floating it (X stays flush; the unit here is
           // bigger than a tweet, so it needs more).
           borderBottom: `8px solid var(--background)`,
           // The focus ring is the single most important affordance in a j/k triage tool and
           // it was painted in --muted-foreground, the dimmest colour in the palette. It is
           // the "you are here", so it gets the accent.
           boxShadow: focused ? "inset 3px 0 0 var(--primary)" : undefined,
           animationDelay: `${Math.min(i, 6) * 28}ms`,
         }}
         className={cn("rise transition-colors bg-[var(--card)]",
                       focused ? "" : "opacity-[0.94] hover:opacity-100")}>
      {/* Chorus chrome — an instrument, deliberately not X */}
      <div className="mono flex items-center gap-2 px-4 pt-3 text-[11px] tracking-tight" style={{ color: "var(--muted-foreground)" }}>
        {parse(s.factors, {})?.fast_lane ? (
          <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-semibold"
                style={{ background: "var(--primary)", color: "var(--primary-foreground)" }}>
            ⚡ {parse(s.factors, {})?.age_min}m
          </span>
        ) : null}
        <span className="tabular-nums" style={{ color: scoreColor(s.score) }}>{s.score.toFixed(2)}</span>
        <span>·</span>
        <span className="uppercase tracking-[0.08em]" style={{ color: "var(--muted-foreground)" }}>{s.target || "reply"}</span>
        {shape !== "post" && (
          <>
            <span>·</span>
            {/* the shape is the single most consequential fact about a suggestion and it was
                nowhere in the meta row: "POST" reads identically for a one-liner and a
                5-tweet thread. */}
            <span className="uppercase tracking-[0.08em] font-semibold" style={{ color: "var(--primary)" }}>
              {shape === "thread" ? `thread ${thread.length}` : "long"}
            </span>
          </>
        )}
        {s.pillar && <><span>·</span><span>{s.pillar}</span></>}
        {/* author_tier ranks the person you are REPLYING to. An original post has no such
            person, so "tier B" there is noise pretending to be signal. */}
        {s.author_tier && !isPost && <><span>·</span><span>tier {s.author_tier}</span></>}
        {url && <a href={url} target="_blank" className="ml-auto hover:underline" style={{ color: DIM }}>on X (o)</a>}
      </div>
      {/* the angle is WHY this was picked — the fastest "is it worth it?" signal */}
      {s.angle && (
        <p className="px-4 pt-1.5 pb-0.5 text-[13.5px] leading-[19px]" style={{ color: "var(--muted-foreground)" }}>
          <span style={{ color: "var(--muted-foreground)" }}>— </span>{s.angle}
        </p>
      )}

      {isPost ? (
        // An original post has no parent tweet. Show WHERE the idea came from, plainly.
        <a href={url || "#"} target="_blank" rel="noreferrer"
           className="mx-4 my-2 flex items-start gap-2.5 rounded-xl px-3 py-2.5 text-[13px] no-underline transition-colors hover:bg-[var(--secondary)]"
           style={{ border: `1px solid var(--border)`, background: "var(--card)" }}>
          <span className="mono shrink-0 text-[10px] uppercase tracking-[0.1em] pt-0.5" style={{ color: "var(--muted-foreground)" }}>
            {String(s.author_handle || "idea")}
          </span>
          <span className="min-w-0" style={{ color: "var(--foreground)" }}>
            {String(s.tweet_text || "").replace(/^\[[^\]]+\]\s*/, "")}
          </span>
        </a>
      ) : (
        <Tweet handle={s.author_handle} text={s.tweet_text} ts={s.created_at}>
          <MediaGrid media={parse(s.media, [])} />
        </Tweet>
      )}

      {!isRT && (
        <div style={{ borderTop: `1px solid ${LINE}` }}>
          {editing ? (
            <div className="px-4 py-3">
              <textarea value={text} onChange={(e) => setText(e.target.value)} autoFocus rows={4}
                className="w-full bg-transparent outline-none resize-none"
                style={{ fontSize: 15, lineHeight: "20px", color: "var(--foreground)" }} />
              <div className="flex items-center gap-2 mt-2">
                <Counter text={text} />
                <button onClick={() => { act(s, "posted_edited", { final_text: text }); setEditing(false); }}
                  className="ml-auto rounded-full px-4 py-1.5 text-[14px] font-bold" style={{ background: X_BLUE, color: "#fff" }}>Save</button>
                <button onClick={() => setEditing(false)}
                  className="rounded-full px-4 py-1.5 text-[14px]" style={{ border: `1px solid var(--border)`, color: DIM }}>Cancel</button>
              </div>
            </div>
          ) : (
            <>
              {/* ONE card renders ONE artifact: exactly what pressing Post publishes.
                  It used to stack the standalone fallback draft AND the thread AND the
                  longform, numbered {i+2}/{len+1} as if the fallback were thread tweet 1 --
                  so a 3-tweet thread read as "4", with its first segment shown twice. In a
                  suggest-only tool the ONE thing the card owes you is an unambiguous answer
                  to "what am I about to post". The fallback is an alternative, not a part of
                  it, so it lives in the picker below with the other drafts. */}
              {shape === "longform" ? (
                <Tweet handle={ME} text={longform} replyingTo={isPost ? undefined : s.author_handle}
                       ts={Date.now()}>
                  {s.gif && <GifChip q={s.gif} />}
                  <div className="mt-2"><Counter text={longform} limit={25000} /></div>
                </Tweet>
              ) : shape === "thread" ? (
                thread.map((t, i) => (
                  <Tweet key={i} handle={ME} text={t}
                         replyingTo={i === 0 && !isPost ? s.author_handle : undefined}
                         ts={Date.now()} connector={i < thread.length - 1}>
                    {i === 0 && s.gif && <GifChip q={s.gif} />}
                    <div className="mt-2 flex items-center gap-2">
                      <Counter text={t} />
                      <span className="text-[13px] font-mono" style={{ color: DIM }}>{i + 1}/{thread.length}</span>
                    </div>
                  </Tweet>
                ))
              ) : (
                <Tweet handle={ME} text={body} replyingTo={isPost ? undefined : s.author_handle}
                       ts={Date.now()}>
                  {s.gif && <GifChip q={s.gif} />}
                  <div className="mt-2"><Counter text={body} /></div>
                </Tweet>
              )}
              {/* draft picker — one full render, the rest collapsed. 3 stacked fake tweets
                  triples scroll and makes the real target tweet visually equal to drafts. */}
              {(drafts.length > 1 || shape !== "post") && (
                <div className="px-4 pb-2">
                  {(order || drafts.map((_: any, k: number) => k)).map((real: number, posn: number) =>
                    (real === pick && shape === "post") ? null : (
                    <button key={real} onClick={() => setPick(real)}
                      className="block w-full text-left text-[12.5px] py-1.5 pl-[52px] pr-2 truncate transition-colors hover:text-[var(--foreground)]"
                      style={{ color: "var(--muted-foreground)" }}>
                      <span className="mono mr-1.5 opacity-60">{posn + 1}</span>{(drafts[real] || "").slice(0, 80)}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {dismissing ? (
        <div className="px-4 py-3 flex flex-wrap items-center gap-2" style={{ borderTop: `1px solid ${LINE}` }}>
          {REASONS.map((r) => (
            <button key={r} onClick={() => { act(s, "dismissed", { reason: r }); setDismissing(false); }}
              className="rounded-full px-3 py-1 text-[13px] hover:bg-secondary"
              style={{ border: `1px solid var(--border)`, color: "var(--foreground)" }}>{r}</button>
          ))}
          <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="other…" autoFocus
            onKeyDown={(e) => { if (e.key === "Enter") { act(s, "dismissed", { reason }); setDismissing(false); } }}
            className="bg-transparent outline-none text-[13px] flex-1 min-w-[80px]" style={{ color: "var(--foreground)" }} />
          <button onClick={() => setDismissing(false)} className="text-[13px]" style={{ color: DIM }}>cancel</button>
        </div>
      ) : !editing && (
        <div className="px-4 py-3.5 flex flex-wrap gap-2" style={{ borderTop: `1px solid ${LINE}` }}>
          <button onClick={() => postOnX(s)}
                  className="rounded-full px-4 py-1.5 text-[13.5px] font-semibold transition-transform active:scale-[.97]"
                  style={{ background: "var(--x-blue)", color: "#fff" }}>   {/* X-native action: the one sanctioned use */}
            {isRT ? "Retweet on X"
              : shape === "thread" ? `Post thread (${thread.length})`
              : shape === "longform" ? "Post long"
              : isPost ? "Post this" : "Post on X"} <span className="opacity-60">(p)</span>
          </button>
          {!isRT && <button onClick={() => setEditing(true)} className="rounded-full px-4 py-1.5 text-[13.5px] font-medium transition-colors hover:bg-[var(--secondary)]"
                    style={{ border: `1px solid var(--border)`, color: "var(--foreground)" }}>Edit (e)</button>}
          <button onClick={() => act(s, "snoozed")} className="rounded-full px-4 py-1.5 text-[13.5px] transition-colors hover:bg-[var(--secondary)]"
                  style={{ border: `1px solid var(--border)`, color: "var(--muted-foreground)" }}>Snooze (s)</button>
          <button onClick={() => setDismissing(true)} className="rounded-full px-4 py-1.5 text-[13.5px] transition-colors hover:bg-destructive/10"
                  style={{ border: "1px solid var(--border)", color: "var(--destructive)" }}>Dismiss (x)</button>
        </div>
      )}
    </div>
  );
}

function Blocked({ tone, title, cta, act, href }: any) {
  return (
    <div className="px-4 py-6 text-center" style={{ borderBottom: `1px solid ${LINE}` }}>
      <OctagonX size={28} className="mx-auto mb-2" style={{ color: tone }} />
      <p className="text-[15px] font-bold" style={{ color: tone }}>{title}</p>
      {href ? <a href={href} target="_blank" className="text-[14px] underline" style={{ color: X_BLUE }}>{cta}</a>
            : <button onClick={act} className="mt-2 rounded-full px-4 py-1.5 text-[14px] font-bold"
                      style={{ background: X_BLUE, color: "#fff" }}>{cta}</button>}
    </div>
  );
}

function Empty({ beat, onRefresh }: any) {
  return (
    <div className="py-20 text-center">
      <div className="text-[28px] mb-2">✳</div>
      <p className="text-[15px] font-bold">Queue clear</p>
      <p className="text-[13px] font-mono mt-1" style={{ color: DIM }}>last cycle {beat} · next ~02:30</p>
      <button onClick={onRefresh} className="mt-3 rounded-full px-4 py-1.5 text-[14px] font-bold"
              style={{ border: `1px solid var(--border)`, color: "var(--foreground)" }}>Refresh</button>
    </div>
  );
}

function Stat({ label, value, sub, danger }: any) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-2.5" style={{ borderTop: `1px solid var(--border)` }}>
      <div className="text-[12.5px]" style={{ color: "var(--muted-foreground)" }}>{label}</div>
      <div className="text-right">
        <div className="mono text-[13px] tabular-nums" style={{ color: danger ? "var(--destructive)" : "var(--foreground)" }}>{value}</div>
        {sub && <div className="mono text-[10.5px]" style={{ color: "var(--muted-foreground)" }}>{sub}</div>}
      </div>
    </div>
  );
}

function Help() {
  const K = [["j / k", "next / prev suggestion"], ["1 2 3", "pick draft variant"], ["p", "post on X (marks posted)"],
             ["e", "edit then post"], ["s", "snooze"], ["x", "dismiss"], ["c", "copy draft"], ["o", "open target on X"],
             ["z", "undo last action"], ["?", "this help"]];
  return (
    <>
      <DialogTitle className="text-[12px] font-medium uppercase tracking-[0.14em] mb-4" style={{ color: "var(--muted-foreground)" }}>Shortcuts</DialogTitle>
      <div>
        {K.map(([k, d]) => (
          <div key={k} className="flex items-center justify-between py-1.5 text-[13px]">
            <span className="mono rounded-md px-1.5 py-0.5 text-[11px]"
                  style={{ background: "var(--secondary)", border: "1px solid var(--border)", color: "var(--foreground)" }}>{k}</span>
            <span style={{ color: "var(--muted-foreground)" }}>{d}</span>
          </div>
        ))}
      </div>
    </>
  );
}

/** The insights engine was invisible after the rewrite. It lives here now — its own tab,
 *  so it never shoves suggestion #1 below the fold (the opposite of triage). */
function Insights({ data }: { data: any }) {
  if (!data) return <p className="py-16 text-center text-[15px]" style={{ color: DIM }}>Loading…</p>;
  const list: any[] = data.insights || [];
  const claims = list.filter((i) => parse(i.payload, {})?.state !== "insufficient_data");
  const waiting = list.length - claims.length;
  const pb = data.playbook ? parse(data.playbook.doc, {}) : null;
  const Row = ({ label, val, pct }: any) => (
    <div className="flex items-center gap-2 text-[13px] font-mono py-0.5">
      <span className="w-24 truncate text-right" style={{ color: DIM }}>{label}</span>
      <div className="h-1.5 flex-1 rounded-sm" style={{ background: "var(--border)" }}>
        <div className="h-1.5 rounded-sm" style={{ width: `${pct}%`, background: X_BLUE }} />
      </div>
      <span style={{ color: DIM }}>{val}</span>
    </div>
  );
  return (
    <div className="px-4 py-4 space-y-6">
      <section>
        <h3 className="text-[15px] font-bold mb-2">What's working</h3>
        {claims.length === 0 ? (
          <p className="text-[13px]" style={{ color: DIM }}>
            Not enough data yet{waiting ? ` — ${waiting} insight(s) waiting on samples` : ""}.
            Act on suggestions (post / edit / dismiss) and these fill in.
          </p>
        ) : claims.map((i, n) => {
          const p = parse(i.payload, {});
          const head = p.best ? `best: ${p.best}`
            : p.best_hour !== undefined ? `best hour: ${String(p.best_hour).padStart(2, "0")}:00`
            : p.dominant ? `${p.dominant} (${Math.round((p.share || 0) * 100)}%)`
            : p.verdict ? `${p.verdict} · ${p.engagement} eng`
            : p.ranked?.[0] ? `${p.ranked[0].key}` : "—";
          return (
            <div key={n} className="flex items-center gap-2 text-[13px] font-mono py-1">
              <span className="rounded px-1.5 py-0.5" style={{ border: `1px solid ${LINE}`, color: DIM }}>{i.kind}</span>
              <span className="flex-1 truncate">{head}</span>
              <span title="confidence = n/(n+k); never 1.0 on small samples" style={{ color: DIM }}>
                conf {Number(i.confidence).toFixed(2)}
              </span>
            </div>
          );
        })}
      </section>

      {(data.byPillar || []).filter((x: any) => x.k && x.total).length > 0 && (
        <section>
          <h3 className="text-[15px] font-bold mb-2">Acceptance by pillar</h3>
          {data.byPillar.filter((x: any) => x.k && x.total).map((x: any) => (
            <Row key={x.k} label={x.k} val={`${Math.round(100 * x.posted / x.total)}% · ${x.posted}/${x.total}`}
                 pct={100 * x.posted / x.total} />
          ))}
        </section>
      )}

      {(data.weights || []).length > 0 && (
        <section>
          <h3 className="text-[15px] font-bold mb-2">Ranking weights</h3>
          {data.weights.map((w: any) => (
            <Row key={w.k} label={w.k} val={Number(w.v).toFixed(2)}
                 pct={(Number(w.v) / Math.max(...data.weights.map((z: any) => z.v))) * 100} />
          ))}
        </section>
      )}

      {pb && (
        <section>
          <h3 className="text-[15px] font-bold mb-2">Playbook · {data.playbook.phase}</h3>
          {["keep_long", "keep_short", "dont_keep"].map((k) => (pb[k] || []).length > 0 && (
            <div key={k} className="mb-2">
              <div className="text-[13px] font-mono mb-1" style={{ color: DIM }}>{k.replace("_", " ")}</div>
              {(pb[k] || []).slice(0, 3).map((r: any, i: number) => (
                <div key={i} className="text-[13px] pl-3 py-0.5">
                  {r.rule}
                  <span className="font-mono" style={{ color: DIM }}> — {r.evidence} (conf {r.confidence})</span>
                </div>
              ))}
            </div>
          ))}
        </section>
      )}

      {(data.reasons || []).length > 0 && (
        <section>
          <h3 className="text-[15px] font-bold mb-2">Top dismiss reasons</h3>
          {data.reasons.map((x: any) => (
            <div key={x.k} className="text-[13px]" style={{ color: DIM }}>{x.k} ×{x.n}</div>
          ))}
        </section>
      )}
    </div>
  );
}
