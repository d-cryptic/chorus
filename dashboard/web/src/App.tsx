import { useEffect, useState, useCallback, useRef } from "react";
import { Tweet, GifChip, Counter, tweetLength, X_BLUE, DIM, LINE } from "@/components/ui/tweet";
import { cn } from "@/lib/utils";
import { RefreshCw, Pause, Play, OctagonX, Activity } from "lucide-react";

const ME = "barundebnath";
const REASONS = ["bad take", "bad tweet", "too late", "off-voice"];

type Sug = {
  id: string; tweet_id?: string; tweet_url?: string; tweet_text: string;
  author_handle: string; author_tier?: string; score: number; pillar?: string;
  angle?: string; drafts: string; factors?: string; target?: string;
  gif?: string | null; thread?: string; created_at?: number;
};

const api = (p: string) => fetch(p, { credentials: "same-origin" }).then((r) => r.json());
const parse = (x: any, f: any) => { try { return typeof x === "string" ? JSON.parse(x) : x ?? f; } catch { return f; } };
const post = (p: string, body: any) =>
  fetch(p, { method: "POST", credentials: "same-origin",
             headers: { "content-type": "application/json", "X-Chorus": "1" },
             body: JSON.stringify(body) }).then((r) => r.json());

export default function App() {
  const [status, setStatus] = useState("queued");
  const [items, setItems] = useState<Sug[]>([]);
  const [counts, setCounts] = useState<any>({});
  const [spend, setSpend] = useState(0);
  const [credits, setCredits] = useState<number | null>(null);
  const [beat, setBeat] = useState("");
  const [alerts, setAlerts] = useState<any[]>([]);
  const [cfg, setCfg] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [cursor, setCursor] = useState(0);          // j/k focus
  const [pick, setPick] = useState<Record<string, number>>({});  // per-suggestion draft index
  const [editing, setEditing] = useState<string | null>(null);
  const [dismissing, setDismissing] = useState<string | null>(null);
  const [toast, setToast] = useState<any>(null);
  const [help, setHelp] = useState(false);
  const undoRef = useRef<any>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [sg, sp, st, cf] = await Promise.all([
      api(`/api/suggestions?status=${status}`),
      api(`/api/spend`).catch(() => ({ total: 0 })),
      api(`/api/status`).catch(() => ({})),
      api(`/api/settings`).catch(() => ({ settings: null })),
    ]);
    setItems(sg.suggestions || []); setCounts(sg.counts || {});
    setSpend(Number(sp.total) || 0); setCfg(cf.settings || null);
    setAlerts(st.alerts || []); setCredits(st.lastRun?.credits ?? null);
    const r = st.lastRun;
    setBeat(r?.started_at ? `${Math.round((Date.now() - r.started_at) / 3.6e6)}h ago · ${r.suggested ?? 0}` : "no cycle yet");
    setCursor(0); setLoading(false);
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const flash = (msg: string, undo?: () => void) => {
    setToast({ msg, undo }); undoRef.current = undo;
    setTimeout(() => setToast((t: any) => (t?.msg === msg ? null : t)), 6000);
  };

  const act = async (s: Sug, action: string, extra: any = {}) => {
    const idx = pick[s.id] ?? 0;
    setItems((x) => x.filter((i) => i.id !== s.id));           // optimistic
    setCursor((c) => Math.min(c, Math.max(0, items.length - 2)));
    const body = { action, draft_index: idx, ...extra };
    post(`/api/suggestions/${encodeURIComponent(s.id)}/action`, body).catch(() => {});
    flash(action.replace("_", " "), async () => {
      await post(`/api/suggestions/${encodeURIComponent(s.id)}/action`, { action: "queued" }).catch(() => {});
      setItems((x) => [s, ...x]); setToast(null);
    });
  };

  const draftsOf = (s: Sug) => parse(s.drafts, []) as string[];
  const selected = (s: Sug) => draftsOf(s)[pick[s.id] ?? 0] ?? "";
  const intent = (s: Sug, text: string) =>
    `https://x.com/intent/post?text=${encodeURIComponent(text)}${s.tweet_id ? `&in_reply_to=${encodeURIComponent(s.tweet_id)}` : ""}`;
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
        const i = Number(e.key) - 1;
        if (i < draftsOf(s).length) setPick((p) => ({ ...p, [s.id]: i }));
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

  const setSetting = async (patch: any) => {
    const r = await post(`/api/settings`, patch).catch(() => null);
    if (r?.settings) { setCfg(r.settings); flash(Object.keys(patch)[0] + " updated"); }
  };

  const blocked =
    cfg?.killed ? { tone: "#f4212e", title: "Kill-switch on — nothing runs", cta: "Release", act: () => setSetting({ killed: 0 }) }
    : cfg?.paused ? { tone: "#ffd400", title: "Paused — cycles stopped (resumable)", cta: "Resume", act: () => setSetting({ paused: 0 }) }
    : alerts[0]?.error === "no_credits" ? { tone: "#f4212e", title: "Provider credits exhausted", cta: "Top up twitterapi.io (100k = $1)", href: "https://twitterapi.io" }
    : null;

  return (
    <div className="min-h-screen flex justify-center" style={{ background: "#000", color: "#e7e9ea" }}>
      <main className="w-full max-w-[600px]" style={{ borderLeft: `1px solid ${LINE}`, borderRight: `1px solid ${LINE}` }}>
        <header className="sticky top-0 z-10 flex items-center gap-3 px-4 h-[53px] backdrop-blur"
                style={{ background: "rgba(0,0,0,.65)", borderBottom: `1px solid ${LINE}` }}>
          <span className="text-[20px] font-black leading-none">✳</span>
          <h1 className="text-[20px] font-bold">Queue</h1>
          <span className="text-[13px] font-mono flex items-center gap-1" style={{ color: DIM }}>
            <Activity size={12} /> {beat}
          </span>
          <div className="ml-auto flex items-center gap-1">
            <button onClick={() => setSetting({ paused: cfg?.paused ? 0 : 1 })} title="pause / resume"
                    className="p-2 rounded-full hover:bg-[#181818]">
              {cfg?.paused ? <Play size={16} style={{ color: "#ffd400" }} /> : <Pause size={16} style={{ color: DIM }} />}
            </button>
            <button onClick={() => { if (cfg?.killed || confirm("Kill-switch: halt every paid call now?")) setSetting({ killed: cfg?.killed ? 0 : 1 }); }}
                    title="kill-switch" className="p-2 rounded-full hover:bg-[#181818]">
              <OctagonX size={16} style={{ color: cfg?.killed ? "#f4212e" : DIM }} />
            </button>
            <button onClick={load} title="refresh" className="p-2 rounded-full hover:bg-[#181818]">
              <RefreshCw size={16} style={{ color: DIM }} />
            </button>
          </div>
        </header>

        <div className="flex" style={{ borderBottom: `1px solid ${LINE}` }}>
          {["queued", "posted", "dismissed"].map((t) => (
            <button key={t} onClick={() => setStatus(t)}
              className="relative flex-1 h-[53px] text-[15px] capitalize transition-colors hover:bg-[#181818]"
              style={{ color: status === t ? "#e7e9ea" : DIM, fontWeight: status === t ? 700 : 400 }}>
              {t}{counts[t] ? ` ${counts[t]}` : ""}
              {status === t && <span className="absolute bottom-0 left-1/2 -translate-x-1/2 h-1 rounded-full"
                                     style={{ width: 56, background: X_BLUE }} />}
            </button>
          ))}
        </div>

        {blocked && <Blocked {...blocked} />}

        {loading ? <p className="py-16 text-center text-[15px]" style={{ color: DIM }}>Loading…</p>
          : items.length === 0 && !blocked ? <Empty beat={beat} onRefresh={load} />
          : items.map((s, i) => (
              <Card key={s.id} s={s} focused={i === cursor} onFocus={() => setCursor(i)}
                    pick={pick[s.id] ?? 0} setPick={(n) => setPick((p) => ({ ...p, [s.id]: n }))}
                    editing={editing === s.id} setEditing={(v) => setEditing(v ? s.id : null)}
                    dismissing={dismissing === s.id} setDismissing={(v) => setDismissing(v ? s.id : null)}
                    act={act} postOnX={postOnX} />
            ))}
        <div className="h-24" />
      </main>

      <aside className="hidden lg:block w-[350px] shrink-0 px-6 py-3 sticky top-0 h-screen">
        <div className="rounded-2xl p-4" style={{ background: "#16181c" }}>
          <h2 className="text-[20px] font-black mb-2">Agent</h2>
          <Stat label="spend today" value={`$${spend.toFixed(2)}`} />
          {credits !== null && (
            <Stat label="provider credits" danger={credits < 5000}
                  value={credits >= 1000 ? `${Math.round(credits / 1000)}k` : String(credits)}
                  sub={`~${Math.max(0, Math.floor(credits / 8600))}d runway`} />
          )}
          <Stat label="queued · acted today" value={`${counts.queued ?? 0} · ${(counts.posted ?? 0) + (counts.dismissed ?? 0)}`} />
          <Stat label="state" danger={Boolean(cfg?.killed)}
                value={cfg?.killed ? "KILLED" : cfg?.paused ? "paused" : "running"} />
          <button onClick={() => setHelp(true)} className="mt-3 text-[13px] font-mono hover:underline" style={{ color: DIM }}>
            keyboard shortcuts (?)
          </button>
        </div>
      </aside>

      {help && <Help onClose={() => setHelp(false)} />}
      {toast && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 rounded-full px-4 py-2 text-[14px] z-50 flex items-center gap-3"
             style={{ background: X_BLUE, color: "#fff" }}>
          <span>{toast.msg}</span>
          {toast.undo && <button onClick={() => { toast.undo(); }} className="font-bold underline">Undo (z)</button>}
        </div>
      )}
    </div>
  );
}

function scoreColor(n: number) { return n >= 0.8 ? "#00ba7c" : n >= 0.6 ? "#e7e9ea" : DIM; }

function Card({ s, focused, onFocus, pick, setPick, editing, setEditing, dismissing, setDismissing, act, postOnX }: any) {
  const drafts: string[] = parse(s.drafts, []);
  const thread: string[] = parse(s.thread, []);
  const url = s.tweet_url || (s.tweet_id ? `https://x.com/i/web/status/${s.tweet_id}` : null);
  const body = drafts[pick] ?? "";
  const [text, setText] = useState(body);
  const [reason, setReason] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { if (focused) ref.current?.scrollIntoView({ block: "nearest" }); }, [focused]);
  useEffect(() => { setText(body); }, [body]);
  const isRT = s.target === "retweet";

  return (
    <div ref={ref} onClick={onFocus}
         style={{ borderBottom: `1px solid ${LINE}`, boxShadow: focused ? `inset 3px 0 0 ${X_BLUE}` : undefined }}
         className={cn("transition-colors", focused ? "bg-[#080808]" : "hover:bg-[#050505]")}>
      {/* Chorus chrome — an instrument, deliberately not X */}
      <div className="flex items-center gap-2 px-4 pt-2 text-[13px] font-mono" style={{ color: DIM }}>
        <span style={{ color: scoreColor(s.score) }}>{s.score.toFixed(2)}</span>
        <span>·</span><span style={{ color: X_BLUE }}>{s.target || "reply"}</span>
        {s.pillar && <><span>·</span><span>{s.pillar}</span></>}
        {s.author_tier && <><span>·</span><span>tier {s.author_tier}</span></>}
        {url && <a href={url} target="_blank" className="ml-auto hover:underline" style={{ color: DIM }}>on X (o)</a>}
      </div>
      {/* the angle is WHY this was picked — the fastest "is it worth it?" signal */}
      {s.angle && (
        <p className="px-4 pt-1 text-[13px]" style={{ color: "#e7e9ea" }}>
          <span style={{ color: X_BLUE }}>▸ </span>{s.angle}
        </p>
      )}

      <Tweet handle={s.author_handle} text={s.tweet_text} ts={s.created_at} />

      {!isRT && (
        <div style={{ borderTop: `1px solid ${LINE}` }}>
          {editing ? (
            <div className="px-4 py-3">
              <textarea value={text} onChange={(e) => setText(e.target.value)} autoFocus rows={4}
                className="w-full bg-transparent outline-none resize-none"
                style={{ fontSize: 15, lineHeight: "20px", color: "#e7e9ea" }} />
              <div className="flex items-center gap-2 mt-2">
                <Counter text={text} />
                <button onClick={() => { act(s, "posted_edited", { final_text: text }); setEditing(false); }}
                  className="ml-auto rounded-full px-4 py-1.5 text-[14px] font-bold" style={{ background: X_BLUE, color: "#fff" }}>Save</button>
                <button onClick={() => setEditing(false)}
                  className="rounded-full px-4 py-1.5 text-[14px]" style={{ border: `1px solid #536471`, color: DIM }}>Cancel</button>
              </div>
            </div>
          ) : (
            <>
              <Tweet handle={ME} text={body} replyingTo={s.author_handle} ts={Date.now()}
                     connector={thread.length > 0}>
                {s.gif && <GifChip q={s.gif} />}
                <div className="mt-2"><Counter text={body} /></div>
              </Tweet>
              {thread.map((t, i) => (
                <Tweet key={i} handle={ME} text={t} ts={Date.now()} connector={i < thread.length - 1}>
                  <div className="mt-2 flex items-center gap-2">
                    <Counter text={t} />
                    <span className="text-[13px] font-mono" style={{ color: DIM }}>{i + 2}/{thread.length + 1}</span>
                  </div>
                </Tweet>
              ))}
              {/* draft picker — one full render, the rest collapsed. 3 stacked fake tweets
                  triples scroll and makes the real target tweet visually equal to drafts. */}
              {drafts.length > 1 && (
                <div className="px-4 pb-2">
                  {drafts.map((d, i) => i === pick ? null : (
                    <button key={i} onClick={() => setPick(i)}
                      className="block w-full text-left text-[13px] py-1 truncate hover:underline" style={{ color: DIM }}>
                      <span className="font-mono">{i + 1}·</span> {d.slice(0, 80)}
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
              className="rounded-full px-3 py-1 text-[13px] hover:bg-[#181818]"
              style={{ border: `1px solid #536471`, color: "#e7e9ea" }}>{r}</button>
          ))}
          <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="other…" autoFocus
            onKeyDown={(e) => { if (e.key === "Enter") { act(s, "dismissed", { reason }); setDismissing(false); } }}
            className="bg-transparent outline-none text-[13px] flex-1 min-w-[80px]" style={{ color: "#e7e9ea" }} />
          <button onClick={() => setDismissing(false)} className="text-[13px]" style={{ color: DIM }}>cancel</button>
        </div>
      ) : !editing && (
        <div className="px-4 py-3 flex flex-wrap gap-2" style={{ borderTop: `1px solid ${LINE}` }}>
          <button onClick={() => postOnX(s)} className="rounded-full px-4 py-1.5 text-[14px] font-bold"
                  style={{ background: X_BLUE, color: "#fff" }}>
            {isRT ? "Retweet on X" : "Post on X"} <span className="opacity-60">(p)</span>
          </button>
          {!isRT && <button onClick={() => setEditing(true)} className="rounded-full px-4 py-1.5 text-[14px] font-bold hover:bg-[#181818]"
                    style={{ border: `1px solid #536471`, color: "#e7e9ea" }}>Edit (e)</button>}
          <button onClick={() => act(s, "snoozed")} className="rounded-full px-4 py-1.5 text-[14px] hover:bg-[#181818]"
                  style={{ border: `1px solid #536471`, color: DIM }}>Snooze (s)</button>
          <button onClick={() => setDismissing(true)} className="rounded-full px-4 py-1.5 text-[14px]"
                  style={{ border: "1px solid #67070f", color: "#f4212e" }}>Dismiss (x)</button>
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
              style={{ border: `1px solid #536471`, color: "#e7e9ea" }}>Refresh</button>
    </div>
  );
}

function Stat({ label, value, sub, danger }: any) {
  return (
    <div className="py-2" style={{ borderTop: `1px solid ${LINE}` }}>
      <div className="text-[13px]" style={{ color: DIM }}>{label}</div>
      <div className="text-[15px] font-bold" style={{ color: danger ? "#f4212e" : "#e7e9ea" }}>{value}</div>
      {sub && <div className="text-[12px] font-mono" style={{ color: DIM }}>{sub}</div>}
    </div>
  );
}

function Help({ onClose }: any) {
  const K = [["j / k", "next / prev suggestion"], ["1 2 3", "pick draft variant"], ["p", "post on X (marks posted)"],
             ["e", "edit then post"], ["s", "snooze"], ["x", "dismiss"], ["c", "copy draft"], ["o", "open target on X"],
             ["z", "undo last action"], ["?", "this help"]];
  return (
    <div onClick={onClose} className="fixed inset-0 z-50 grid place-items-center" style={{ background: "rgba(0,0,0,.7)" }}>
      <div className="rounded-2xl p-6 w-[340px]" style={{ background: "#16181c", border: `1px solid ${LINE}` }}>
        <h3 className="text-[20px] font-black mb-3">Shortcuts</h3>
        {K.map(([k, d]) => (
          <div key={k} className="flex justify-between py-1 text-[14px]">
            <span className="font-mono" style={{ color: X_BLUE }}>{k}</span>
            <span style={{ color: DIM }}>{d}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
