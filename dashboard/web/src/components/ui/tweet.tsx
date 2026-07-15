import { cn } from "@/lib/utils";

/** X fidelity is sacred INSIDE the tweet body only — 15px/20px, wrap width, blue
 *  entities, "Replying to", avatar gutter. That is what you judge.
 *  Everything else is Chorus chrome and must NOT cosplay as X: no fake action rows,
 *  no fake verified badges, no fake timestamps. Inventing UI data is the same sin as
 *  inventing a stat in a draft — it makes a draft indistinguishable from a real tweet. */

export const X_BLUE = "var(--x-blue)";
export const DIM = "var(--muted-foreground)";
export const LINE = "var(--border)";

const URL_RE = /https?:\/\/\S+/g;
const CJK = /[ᄀ-ᇿ⺀-〾ぁ-㏿㐀-䶿一-鿿ꀀ-꓏가-힣豈-﫿︰-﹏＀-｠￠-￦]/;

/** X's real weighting: every URL counts as 23 regardless of length, CJK counts 2,
 *  everything else 1 (by codepoint, so emoji are 2 not 4). Naive .length lets a
 *  285-weighted draft look "fine" and it would be rejected at post time. */
export function tweetLength(s: string): number {
  if (!s) return 0;
  const urls = s.match(URL_RE) || [];
  const stripped = s.replace(URL_RE, "");
  let n = urls.length * 23;
  for (const ch of Array.from(stripped)) n += CJK.test(ch) ? 2 : 1;
  return n;
}

function Avatar({ handle, size = 40 }: { handle: string; size?: number }) {
  const letter = (handle || "?").replace(/^@/, "").charAt(0).toUpperCase();
  return (
    <div className="shrink-0 rounded-full grid place-items-center font-semibold select-none"
         style={{ width: size, height: size, fontSize: size * 0.4,
                  background: "linear-gradient(160deg, var(--secondary), var(--card))",
                  border: "1px solid var(--border)", color: "var(--muted-foreground)" }} aria-hidden>
      {letter}
    </div>
  );
}

export function TweetText({ text }: { text: string }) {
  const parts = (text || "").split(/(https?:\/\/\S+|@\w{1,15}|#\w+)/g);
  return (
    <div className="x-body whitespace-pre-wrap break-words" style={{ color: "var(--foreground)" }}>
      {parts.map((p, i) =>
        /^(https?:\/\/|@|#)/.test(p) ? <span key={i} style={{ color: X_BLUE }}>{p}</span> : <span key={i}>{p}</span>
      )}
    </div>
  );
}

/** age: real value or nothing. A wrong timestamp trains you to ignore the row. */
function age(ts?: number) {
  if (!ts) return null;
  const m = Math.max(0, Math.floor((Date.now() - ts) / 60000));
  return m < 60 ? `${m}m` : m < 1440 ? `${Math.floor(m / 60)}h` : `${Math.floor(m / 1440)}d`;
}

export function Tweet({
  handle, name, text, replyingTo, ts, connector, children,
}: {
  handle: string; name?: string; text: string; replyingTo?: string;
  ts?: number; connector?: boolean; children?: React.ReactNode;
}) {
  const a = age(ts);
  return (
    <div className="flex gap-3 px-4 pt-3.5">
      <div className="flex flex-col items-center shrink-0">
        <Avatar handle={handle} />
        {/* X's thread connector: a rail from this avatar to the next. X does NOT indent. */}
        {connector && <div className="w-0.5 grow mt-1" style={{ background: "var(--border)" }} />}
      </div>
      <div className="min-w-0 flex-1 pb-3.5">
        <div className="x-body flex items-center gap-1">
          <span className="font-bold truncate" style={{ color: "var(--foreground)" }}>{name || handle.replace(/^@/, "")}</span>
          <span className="truncate" style={{ color: DIM }}>@{handle.replace(/^@/, "")}</span>
          {a && <><span style={{ color: DIM }}>·</span><span style={{ color: DIM }}>{a}</span></>}
        </div>
        {replyingTo && (
          <div className="x-body mb-0.5" style={{ color: DIM }}>
            Replying to <span style={{ color: X_BLUE }}>@{replyingTo.replace(/^@/, "")}</span>
          </div>
        )}
        <TweetText text={text} />
        {children}
      </div>
    </div>
  );
}

/** Chorus chrome: an instruction, never mistakable for rendered media. */
export function GifChip({ q }: { q: string }) {
  return (
    <a href={`https://giphy.com/search/${encodeURIComponent(q)}`} target="_blank" rel="noreferrer"
       className="mono mt-2 inline-flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-[12px] no-underline transition-colors hover:bg-[var(--secondary)]"
       style={{ border: `1px dashed var(--border)`, color: "var(--muted-foreground)" }}>
      <span style={{ color: "var(--muted-foreground)" }}>GIF</span>
      <span style={{ color: X_BLUE }}>{q}</span>
    </a>
  );
}

export function Counter({ text }: { text: string }) {
  const n = tweetLength(text);
  const color = n > 280 ? "var(--destructive)" : n >= 260 ? "var(--warning)" : "var(--muted-foreground)";
  return <span className="mono text-[12px] tabular-nums" style={{ color }}>{n}/280</span>;
}

export { cn };
