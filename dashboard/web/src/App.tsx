import { useEffect, useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tweet, tweetLength } from "@/components/ui/tweet";
import { cn } from "@/lib/utils";
import { Copy, ExternalLink, Check, Pencil, Clock, X, RefreshCw, BarChart3, Activity, Pause, Play, OctagonX } from "lucide-react";

type Sug = {
  id: string; tweet_id?: string; tweet_url?: string; tweet_text: string;
  author_handle: string; author_tier?: string; score: number; pillar?: string;
  angle?: string; drafts: string; factors?: string; rationale?: string;
};
const api = (p: string) => fetch(p, { credentials: "same-origin" }).then((r) => r.json());
const parse = (x: any, f: any) => { try { return typeof x === "string" ? JSON.parse(x) : x ?? f; } catch { return f; } };

function Toast({ msg }: { msg: string }) {
  return <div className="fixed bottom-5 left-1/2 -translate-x-1/2 rounded-md border bg-card px-4 py-2 text-sm text-primary shadow-lg z-50">{msg}</div>;
}

const ME = "barundebnath";

export default function App() {
  const [status, setStatus] = useState("queued");
  const [items, setItems] = useState<Sug[]>([]);
  const [spend, setSpend] = useState(0);
  const [beat, setBeat] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [toast, setToast] = useState("");
  const [review, setReview] = useState<any>(null);
  const [cfg, setCfg] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [credits, setCredits] = useState<number | null>(null);
  const flash = (m: string) => { setToast(m); setTimeout(() => setToast(""), 1500); };

  const load = useCallback(async () => {
    setLoading(true); setErr("");
    try {
      const [sg, sp, st, cf] = await Promise.all([
        api(`/api/suggestions?status=${status}`), api(`/api/spend`).catch(() => ({ total: 0 })), api(`/api/status`).catch(() => ({ lastRun: null })),
        api(`/api/settings`).catch(() => ({ settings: null })),
      ]);
      setCfg(cf.settings || null);
      setItems(sg.suggestions || []); setSpend(Number(sp.total) || 0);
      setAlerts(st.alerts || []);
      setCredits(st.lastRun?.credits ?? null);
      const r = st.lastRun;
      setBeat(r?.started_at ? `${Math.round((Date.now() - r.started_at) / 3.6e6)}h ago · ${r.suggested ?? 0} suggested${r.error ? " · ERROR" : ""}` : "no cycle yet");
    } catch (e: any) { setErr(String(e)); } finally { setLoading(false); }
  }, [status]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (review === undefined) return; }, [review]);

  const act = async (s: Sug, action: string) => {
    const body: any = { action };
    if (action === "dismissed") body.reason = prompt("dismiss reason (optional):") || undefined;
    if (action === "posted_edited") { const t = prompt("paste what you actually posted:"); if (!t) return; body.final_text = t; }
    if (action === "posted" || action === "posted_edited") { const u = prompt("your reply URL (optional):"); if (u) body.posted_url = u; }
    try {
      await fetch(`/api/suggestions/${encodeURIComponent(s.id)}/action`, { method: "POST", credentials: "same-origin", headers: { "content-type": "application/json", "X-Chorus": "1" }, body: JSON.stringify(body) });
      setItems((x) => x.filter((i) => i.id !== s.id)); flash(action);
    } catch { flash("failed"); }
  };
  const setSetting = async (patch: any) => {
    try {
      const r = await fetch(`/api/settings`, {
        method: "POST", credentials: "same-origin",
        headers: { "content-type": "application/json", "X-Chorus": "1" },
        body: JSON.stringify(patch),
      }).then((x) => x.json());
      setCfg(r.settings); flash(Object.keys(patch)[0] + " updated");
    } catch { flash("failed"); }
  };
  const copy = (t: string) => { navigator.clipboard.writeText(t).then(() => flash("copied — post it yourself")); };
  const openReply = (s: Sug, d: string) => window.open(`https://x.com/intent/post?text=${encodeURIComponent(d)}${s.tweet_id ? `&in_reply_to=${encodeURIComponent(s.tweet_id)}` : ""}`, "_blank");
  const loadReview = async () => {
    if (review) { setReview(null); return; }
    const [r, i] = await Promise.all([
      api(`/api/review`).catch(() => ({})),
      api(`/api/insights`).catch(() => ({ insights: [], playbook: null })),
    ]);
    setReview({ ...r, ...i });
  };

  return (
    <div className="min-h-screen bg-black flex justify-center" style={{ color: "#e7e9ea" }}>
      {/* left rail — X nav */}
      <nav className="hidden md:flex flex-col items-start gap-1 w-[68px] xl:w-[255px] shrink-0 px-2 py-2 sticky top-0 h-screen">
        <div className="p-3 text-[26px] font-black leading-none" style={{ color: "#e7e9ea" }}>✳</div>
        {[["Queue", "queued"], ["Posted", "posted"], ["Dismissed", "dismissed"]].map(([label, key]) => (
          <button key={key} onClick={() => setStatus(key)}
            className="flex items-center gap-4 rounded-full px-3 xl:pr-6 py-3 hover:bg-[#181818] transition-colors"
            style={{ fontWeight: status === key ? 700 : 400, color: "#e7e9ea" }}>
            <span className="hidden xl:inline text-[20px] leading-none">{label}</span>
            <span className="xl:hidden text-[18px] leading-none">{String(label)[0]}</span>
          </button>
        ))}
      </nav>

      {/* center — the feed, exactly X's 600px column */}
      <main className="w-full max-w-[600px] shrink-0" style={{ borderLeft: "1px solid #2f3336", borderRight: "1px solid #2f3336" }}>
      <header className="sticky top-0 z-10 flex items-center gap-3 px-4 h-[53px] backdrop-blur"
              style={{ background: "rgba(0,0,0,0.65)", borderBottom: "1px solid #2f3336" }}>
        <h1 className="text-[20px] font-bold tracking-tight">Queue</h1>
        <span className="text-xs font-mono flex items-center gap-1" style={{ color: "#71767b" }}><Activity size={12} /> {beat}</span>
        <div className="ml-auto flex items-center gap-1">

          {cfg && (
            <>
              <Button variant="ghost" size="icon" title={cfg.paused ? "resume agent" : "pause agent (soft, resumable)"}
                onClick={() => setSetting({ paused: !cfg.paused })}>
                {cfg.paused ? <Play size={16} className="text-amber-400" /> : <Pause size={16} />}
              </Button>
              <Button variant="ghost" size="icon"
                title={cfg.killed ? "kill-switch is ON — nothing will run. Click to release." : "KILL: stop every paid call immediately"}
                onClick={() => {
                  if (!cfg.killed && !confirm("Kill-switch: halt every paid call immediately?\n(beats pause and any remaining budget)")) return;
                  setSetting({ killed: !cfg.killed });
                }}>
                <OctagonX size={16} className={cfg.killed ? "text-destructive" : ""} />
              </Button>
            </>
          )}
          <Button variant="ghost" size="icon" onClick={loadReview} title="review"><BarChart3 size={16} /></Button>
          <Button variant="ghost" size="icon" onClick={load} title="refresh"><RefreshCw size={16} /></Button>
        </div>
      </header>

      {alerts.length > 0 && (
        <div className="mt-3 rounded-md border border-destructive/50 px-3 py-2 text-xs font-mono text-destructive">
          {alerts.length} failed cycle(s) in the last 7d — latest: <b>{alerts[0].error}</b>
          {alerts[0].error === "no_credits" && " → top up twitterapi.io (100k credits = $1)"}
          {alerts[0].error === "no_candidates" && " → the read provider returned nothing; check keys/credit"}
        </div>
      )}
      {cfg && Boolean(cfg.killed || cfg.paused) && (
        <div className={cn("mt-3 rounded-md border px-3 py-2 text-xs font-mono",
          cfg.killed ? "border-destructive/50 text-destructive" : "border-amber-500/40 text-amber-400")}>
          {cfg.killed
            ? "KILL-SWITCH ON — no cycles, no spend. Nothing new will appear until released."
            : "PAUSED — cycles are stopped (resumable). Budget untouched."}
        </div>
      )}
      <div className="flex" style={{ borderBottom: "1px solid #2f3336" }}>
        {["queued", "posted", "dismissed"].map((t) => (
          <button
            key={t}
            onClick={() => setStatus(t)}
            className="relative flex-1 h-[53px] text-[15px] transition-colors hover:bg-[#181818] capitalize"
            style={{ color: status === t ? "#e7e9ea" : "#71767b", fontWeight: status === t ? 700 : 400 }}
          >
            {t}
            {status === t && (
              <span className="absolute bottom-0 left-1/2 -translate-x-1/2 h-1 rounded-full"
                    style={{ width: 56, background: "#1d9bf0" }} />
            )}
          </button>
        ))}
      </div>

      {review && <ReviewPanel r={review} />}

      {loading ? <p className="py-16 text-center text-[15px]" style={{ color: "#71767b" }}>Loading…</p>
        : err ? <p className="text-sm text-destructive font-mono py-16 text-center">{err}</p>
        : items.length === 0 ? <p className="py-16 text-center text-[15px]" style={{ color: "#71767b" }}>Nothing {status} yet.</p>
        : <div>
            {items.map((s) => {
              const drafts: string[] = parse(s.drafts, []);
              const url = s.tweet_url || (s.tweet_id ? `https://x.com/i/web/status/${s.tweet_id}` : null);
              const me = ME;
              return (
                <div key={s.id} className="transition-colors" style={{ borderBottom: "1px solid #2f3336" }}>
                  {/* meta strip — Chorus's own signal, kept outside the X-accurate render */}
                  <div className="flex items-center gap-2 text-[13px] px-4 pt-2" style={{ color: "#71767b" }}>
                    <span className="capitalize" style={{ color: "#1d9bf0" }}>{s.target || "reply"}</span>
                    <span>·</span><span className="font-mono">{s.score.toFixed(2)}</span>
                    {s.pillar && <><span>·</span><span>{s.pillar}</span></>}
                    {s.author_tier && <><span>·</span><span>tier {s.author_tier}</span></>}
                    {url && <a href={url} target="_blank" className="ml-auto inline-flex items-center gap-1 hover:underline" style={{ color: "#71767b" }}>on X <ExternalLink size={11} /></a>}
                  </div>

                  {/* THEIR tweet — exactly as it appears on X */}
                  <Tweet handle={s.author_handle} text={s.tweet_text} />

                  {s.angle && <p className="text-[13px] px-4 pt-1" style={{ color: "#71767b" }}>▸ {s.angle}</p>}

                  {/* YOUR drafts — rendered as the reply will actually look */}
                  {drafts.map((d, i) => (
                    <Tweet
                      key={i}
                      handle={me}
                      text={d}
                      replyingTo={s.author_handle}
                      gif={i === 0 ? s.gif : null}
                      isDraft
                      footer={
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" title="copy" onClick={() => copy(d)}><Copy size={14} /></Button>
                          <Button variant="ghost" size="icon" title="open reply on X" onClick={() => openReply(s, d)}><ExternalLink size={14} /></Button>
                        </div>
                      }
                    />
                  ))}

                  {/* thread continuation, if the take needed one */}
                  {parse(s.thread, []).length > 0 && (
                    <div className="border-l-2 border-[#2f3336] ml-6">
                      {parse(s.thread, []).map((t: string, i: number) => (
                        <Tweet key={i} handle={me} text={t} isDraft />
                      ))}
                    </div>
                  )}

                  {status === "queued" && (
                    <div className="flex gap-2 flex-wrap px-4 py-3">
                      <button onClick={() => act(s, "posted")}
                        className="rounded-full px-4 py-1.5 text-[14px] font-bold text-black hover:opacity-90"
                        style={{ background: "#1d9bf0", color: "#fff" }}>I posted this</button>
                      <button onClick={() => act(s, "posted_edited")}
                        className="rounded-full px-4 py-1.5 text-[14px] font-bold hover:bg-[#181818]"
                        style={{ border: "1px solid #536471", color: "#e7e9ea" }}>Posted edited</button>
                      <button onClick={() => act(s, "snoozed")}
                        className="rounded-full px-4 py-1.5 text-[14px] hover:bg-[#181818]"
                        style={{ border: "1px solid #536471", color: "#71767b" }}>Snooze</button>
                      <button onClick={() => act(s, "dismissed")}
                        className="rounded-full px-4 py-1.5 text-[14px] hover:bg-[#f4212e]/10"
                        style={{ border: "1px solid #67070f", color: "#f4212e" }}>Dismiss</button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>}
      </main>

      {/* right rail — where X puts trends, we put the things that can stop the agent */}
      <aside className="hidden lg:block w-[350px] shrink-0 px-6 py-3 sticky top-0 h-screen">
        <div className="rounded-2xl p-4" style={{ background: "#16181c" }}>
          <h2 className="text-[20px] font-black mb-3">Agent</h2>
          <Stat label="spend today" value={`$${spend.toFixed(2)}`} />
          {credits !== null && (
            <Stat label="provider credits" value={`${credits >= 1000 ? Math.round(credits / 1000) + "k" : credits}`}
                  sub={`~${Math.max(0, Math.floor(credits / 8600))}d runway`} danger={credits < 5000} />
          )}
          <Stat label="last cycle" value={beat} />
          {cfg && <Stat label="state" value={cfg.killed ? "KILLED" : cfg.paused ? "paused" : "running"} danger={Boolean(cfg.killed)} />}
        </div>
      </aside>

      {toast && <Toast msg={toast} />}
    </div>
  );
}

function Stat({ label, value, sub, danger }: { label: string; value: any; sub?: string; danger?: boolean }) {
  return (
    <div className="py-2" style={{ borderTop: "1px solid #2f3336" }}>
      <div className="text-[13px]" style={{ color: "#71767b" }}>{label}</div>
      <div className="text-[15px] font-bold" style={{ color: danger ? "#f4212e" : "#e7e9ea" }}>{value}</div>
      {sub && <div className="text-[12px] font-mono" style={{ color: "#71767b" }}>{sub}</div>}
    </div>
  );
}

function ReviewPanel({ r }: { r: any }) {
  const Row = ({ label, val, pct }: { label: string; val: string; pct: number }) => (
    <div className="grid grid-cols-[1fr_auto] items-center gap-2 text-xs font-mono">
      <div className="flex items-center gap-2"><span className="w-28 truncate text-muted-foreground text-right">{label}</span>
        <div className="h-2 flex-1 rounded-sm bg-secondary"><div className="h-2 rounded-sm bg-primary/70" style={{ width: `${pct}%` }} /></div></div>
      <span>{val}</span>
    </div>
  );
  const acc = (rows: any[]) => (rows || []).filter((x) => x.k != null && x.total > 0);
  return (
    <Card className="mb-4"><CardContent className="space-y-4">
      <div><h3 className="text-xs uppercase tracking-wide text-muted-foreground font-mono mb-2">acceptance by pillar</h3>
        {acc(r.byPillar).length ? acc(r.byPillar).map((x: any) => <Row key={x.k} label={x.k} val={`${Math.round(100 * x.posted / x.total)}% · ${x.posted}/${x.total}`} pct={100 * x.posted / x.total} />)
          : <p className="text-xs font-mono text-muted-foreground">no data yet — act on some suggestions</p>}</div>
      {(r.weights || []).length > 0 && <div><h3 className="text-xs uppercase tracking-wide text-muted-foreground font-mono mb-2">ranking weights</h3>
        {r.weights.map((w: any) => <Row key={w.k} label={w.k} val={Number(w.v).toFixed(2)} pct={Number(w.v) / Math.max(...r.weights.map((z: any) => z.v)) * 100} />)}</div>}
      <InsightList insights={r.insights} playbook={r.playbook} />
      {(r.reasons || []).length > 0 && <div><h3 className="text-xs uppercase tracking-wide text-muted-foreground font-mono mb-2">top dismiss reasons</h3>
        <ul className="text-xs text-muted-foreground space-y-1">{r.reasons.map((x: any) => <li key={x.k}>{x.k} <span className="text-muted-foreground/60">×{x.n}</span></li>)}</ul></div>}
    </CardContent></Card>
  );
}

function InsightList({ insights, playbook }: { insights?: any[]; playbook?: any }) {
  const list = insights || [];
  const claims = list.filter((i) => parse(i.payload, {})?.state !== "insufficient_data");
  const pending = list.length - claims.length;
  return (
    <div>
      <h3 className="text-xs uppercase tracking-wide text-muted-foreground font-mono mb-2">insights</h3>
      {claims.length === 0 ? (
        <p className="text-xs font-mono text-muted-foreground">
          not enough data yet{pending ? ` — ${pending} insight(s) waiting on samples` : ""}.
          Act on suggestions (posted / edited / dismissed) and these fill in.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {claims.map((i, n) => {
            const p = parse(i.payload, {});
            const headline =
              p.best ? `best: ${p.best}` :
              p.best_hour !== undefined ? `best hour: ${String(p.best_hour).padStart(2, "0")}:00` :
              p.dominant ? `${p.dominant} (${Math.round((p.share || 0) * 100)}%)` :
              p.verdict ? `${p.verdict} · ${p.engagement} eng` :
              p.ranked?.[0] ? `${p.ranked[0].key}` : "—";
            return (
              <li key={n} className="flex items-center gap-2 text-xs font-mono">
                <Badge className="border-border text-muted-foreground shrink-0">{i.kind}</Badge>
                <span className="flex-1 truncate">{headline}</span>
                <span className="text-muted-foreground shrink-0" title="confidence = n/(n+k)">
                  conf {Number(i.confidence).toFixed(2)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {playbook && (
        <div className="mt-3">
          <h3 className="text-xs uppercase tracking-wide text-muted-foreground font-mono mb-1">
            playbook · {playbook.phase}
          </h3>
          <pre className="text-[11px] leading-relaxed bg-secondary/50 rounded-md p-2 overflow-x-auto max-h-56">
            {JSON.stringify(parse(playbook.doc, {}), null, 1)}
          </pre>
        </div>
      )}
    </div>
  );
}
