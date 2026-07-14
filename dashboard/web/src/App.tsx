import { useEffect, useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Copy, ExternalLink, Check, Pencil, Clock, X, RefreshCw, BarChart3, Activity } from "lucide-react";

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

export default function App() {
  const [status, setStatus] = useState("queued");
  const [items, setItems] = useState<Sug[]>([]);
  const [spend, setSpend] = useState(0);
  const [beat, setBeat] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [toast, setToast] = useState("");
  const [review, setReview] = useState<any>(null);
  const flash = (m: string) => { setToast(m); setTimeout(() => setToast(""), 1500); };

  const load = useCallback(async () => {
    setLoading(true); setErr("");
    try {
      const [sg, sp, st] = await Promise.all([
        api(`/api/suggestions?status=${status}`), api(`/api/spend`).catch(() => ({ total: 0 })), api(`/api/status`).catch(() => ({ lastRun: null })),
      ]);
      setItems(sg.suggestions || []); setSpend(Number(sp.total) || 0);
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
  const copy = (t: string) => { navigator.clipboard.writeText(t).then(() => flash("copied — post it yourself")); };
  const openReply = (s: Sug, d: string) => window.open(`https://x.com/intent/post?text=${encodeURIComponent(d)}${s.tweet_id ? `&in_reply_to=${encodeURIComponent(s.tweet_id)}` : ""}`, "_blank");
  const loadReview = async () => setReview(review ? null : await api(`/api/review`).catch(() => ({})));

  return (
    <div className="min-h-screen mx-auto max-w-3xl px-4 pb-24">
      <header className="sticky top-0 z-10 flex flex-wrap items-center gap-3 py-4 bg-background/90 backdrop-blur border-b">
        <div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-primary" /><h1 className="text-base font-semibold tracking-tight">Chorus</h1></div>
        <span className="text-xs text-muted-foreground font-mono flex items-center gap-1"><Activity size={12} /> {beat}</span>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs font-mono text-muted-foreground">spend <span className="text-primary">${spend.toFixed(2)}</span></span>
          <Button variant="ghost" size="icon" onClick={loadReview} title="review"><BarChart3 size={16} /></Button>
          <Button variant="ghost" size="icon" onClick={load} title="refresh"><RefreshCw size={16} /></Button>
        </div>
      </header>

      <div className="flex gap-1.5 py-4">
        {["queued", "posted", "dismissed"].map((s) => (
          <Button key={s} size="sm" variant={status === s ? "secondary" : "ghost"} onClick={() => setStatus(s)} className="capitalize">{s}</Button>
        ))}
      </div>

      {review && <ReviewPanel r={review} />}

      {loading ? <p className="text-sm text-muted-foreground font-mono py-16 text-center">loading…</p>
        : err ? <p className="text-sm text-destructive font-mono py-16 text-center">{err}</p>
        : items.length === 0 ? <p className="text-sm text-muted-foreground font-mono py-16 text-center">nothing {status}.</p>
        : <div className="space-y-3">
            {items.map((s) => {
              const drafts: string[] = parse(s.drafts, []);
              const url = s.tweet_url || (s.tweet_id ? `https://x.com/i/web/status/${s.tweet_id}` : null);
              return (
                <Card key={s.id} className="overflow-hidden">
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground flex-wrap">
                      <Badge className="border-primary/40 text-primary bg-primary/10 font-semibold">{s.score.toFixed(2)}</Badge>
                      <span className="text-foreground">@{s.author_handle}</span>
                      {s.author_tier && <Badge className="border-border text-muted-foreground">tier {s.author_tier}</Badge>}
                      {s.pillar && <Badge className="border-border text-muted-foreground">{s.pillar}</Badge>}
                      {url && <a href={url} target="_blank" className="ml-auto inline-flex items-center gap-1 hover:text-foreground">view <ExternalLink size={11} /></a>}
                    </div>
                    <p className="text-sm leading-relaxed">{s.tweet_text}</p>
                    {s.angle && <p className="text-xs font-mono text-amber-300/90">▸ {s.angle}</p>}
                    <div className="space-y-2">
                      {drafts.map((d, i) => (
                        <div key={i} className="flex items-start gap-2 rounded-md bg-secondary/50 p-2.5">
                          <p className="text-sm flex-1 leading-relaxed">{d}</p>
                          <div className="flex gap-1 shrink-0">
                            <Button variant="ghost" size="icon" title="copy" onClick={() => copy(d)}><Copy size={14} /></Button>
                            <Button variant="ghost" size="icon" title="open reply" onClick={() => openReply(s, d)}><ExternalLink size={14} /></Button>
                          </div>
                        </div>
                      ))}
                    </div>
                    {status === "queued" && (
                      <div className="flex gap-1.5 pt-1 flex-wrap">
                        <Button size="sm" onClick={() => act(s, "posted")}><Check size={14} /> posted</Button>
                        <Button size="sm" variant="outline" onClick={() => act(s, "posted_edited")}><Pencil size={14} /> edited</Button>
                        <Button size="sm" variant="ghost" onClick={() => act(s, "snoozed")}><Clock size={14} /> snooze</Button>
                        <Button size="sm" variant="destructive" onClick={() => act(s, "dismissed")}><X size={14} /> dismiss</Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>}
      {toast && <Toast msg={toast} />}
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
      {(r.reasons || []).length > 0 && <div><h3 className="text-xs uppercase tracking-wide text-muted-foreground font-mono mb-2">top dismiss reasons</h3>
        <ul className="text-xs text-muted-foreground space-y-1">{r.reasons.map((x: any) => <li key={x.k}>{x.k} <span className="text-muted-foreground/60">×{x.n}</span></li>)}</ul></div>}
    </CardContent></Card>
  );
}
