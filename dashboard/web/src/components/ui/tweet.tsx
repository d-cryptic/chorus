import { MessageCircle, Repeat2, Heart, BarChart2, Bookmark, Share, BadgeCheck } from "lucide-react";
import { cn } from "@/lib/utils";

/** X/Twitter-accurate rendering so a draft can be judged as it will actually appear:
 *  15px/20px text, 3px avatar gutter, real action-row spacing, X's exact greys, and the
 *  same 280-char budget. If it looks wrong here, it looks wrong on X. */

export const X_BLUE = "#1d9bf0";
const DIM = "#71767b";      // X secondary text
const LINE = "#2f3336";     // X divider
const HOVER_BLUE = "#1d9bf0";

/** X counts codepoints, not UTF-16 units — emoji must cost 2, not 4. */
export function tweetLength(s: string): number {
  return Array.from(s || "").length;
}

function Avatar({ handle, size = 40 }: { handle: string; size?: number }) {
  const letter = (handle || "?").replace(/^@/, "").charAt(0).toUpperCase();
  return (
    <div
      className="shrink-0 rounded-full grid place-items-center font-semibold text-white select-none"
      style={{ width: size, height: size, fontSize: size * 0.42, background: "#536471" }}
      aria-hidden
    >
      {letter}
    </div>
  );
}

function Action({ icon: Icon, count, color }: { icon: any; count?: string; color: string }) {
  return (
    <div className="group flex items-center gap-1 cursor-default" style={{ color: DIM }}>
      <div className="rounded-full p-1.5 transition-colors" style={{ lineHeight: 0 }}>
        <Icon size={17} strokeWidth={1.75} className="transition-colors" style={{ color: "inherit" }} />
      </div>
      {count !== undefined && <span className="text-[13px] leading-none">{count}</span>}
      <span className="sr-only">{color}</span>
    </div>
  );
}

/** Renders body text the way X does: links/@mentions/#tags in blue, newlines preserved. */
export function TweetText({ text }: { text: string }) {
  const parts = (text || "").split(/(https?:\/\/\S+|@\w{1,15}|#\w+)/g);
  return (
    <div
      className="whitespace-pre-wrap break-words"
      style={{ fontSize: 15, lineHeight: "20px", color: "#e7e9ea" }}
    >
      {parts.map((p, i) =>
        /^(https?:\/\/|@|#)/.test(p)
          ? <span key={i} style={{ color: X_BLUE }}>{p}</span>
          : <span key={i}>{p}</span>
      )}
    </div>
  );
}

export function Tweet({
  handle, name, text, replyingTo, gif, isDraft, footer,
}: {
  handle: string; name?: string; text: string;
  replyingTo?: string; gif?: string | null; isDraft?: boolean; footer?: React.ReactNode;
}) {
  const n = tweetLength(text);
  const over = n > 280;
  return (
    <article
      className={cn("flex gap-3 px-4 py-3 transition-colors",
        isDraft ? "hover:bg-[#080808]" : "hover:bg-[#080808]")}
      style={{
        borderBottom: `1px solid ${LINE}`,
        // a draft is YOURS: mark it with X's blue accent rail, not a grey box
        boxShadow: isDraft ? `inset 2px 0 0 ${X_BLUE}` : undefined,
      }}
    >
      <Avatar handle={handle} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1 text-[15px] leading-5">
          <span className="font-bold truncate" style={{ color: "#e7e9ea" }}>
            {name || handle.replace(/^@/, "")}
          </span>
          <BadgeCheck size={16} style={{ color: X_BLUE }} className="shrink-0" />
          <span className="truncate" style={{ color: DIM }}>
            @{handle.replace(/^@/, "")}
          </span>
          <span style={{ color: DIM }}>·</span>
          <span style={{ color: DIM }}>{isDraft ? "now" : "1h"}</span>
        </div>

        {replyingTo && (
          <div className="text-[15px] leading-5 mb-0.5" style={{ color: DIM }}>
            Replying to <span style={{ color: X_BLUE }}>@{replyingTo.replace(/^@/, "")}</span>
          </div>
        )}

        <TweetText text={text} />

        {gif && (
          <a
            href={`https://giphy.com/search/${encodeURIComponent(gif)}`}
            target="_blank" rel="noreferrer"
            className="mt-3 flex items-center gap-2 rounded-2xl px-3 py-2 text-[13px] no-underline"
            style={{ border: `1px solid ${LINE}`, color: DIM }}
          >
            <span className="rounded px-1 py-0.5 text-[10px] font-bold"
                  style={{ background: DIM, color: "#000" }}>GIF</span>
            <span style={{ color: X_BLUE }}>{gif}</span>
            <span>— pick one on Giphy</span>
          </a>
        )}

        <div className="mt-3 flex items-center justify-between" style={{ maxWidth: 425 }}>
          <Action icon={MessageCircle} count="" color={HOVER_BLUE} />
          <Action icon={Repeat2} count="" color="#00ba7c" />
          <Action icon={Heart} count="" color="#f91880" />
          <Action icon={BarChart2} count="" color={HOVER_BLUE} />
          <div className="flex items-center gap-1">
            <Action icon={Bookmark} color={HOVER_BLUE} />
            <Action icon={Share} color={HOVER_BLUE} />
          </div>
        </div>

        {isDraft && (
          <div className="mt-2 flex items-center gap-3">
            <span className="text-[13px] font-mono" style={{ color: over ? "#f4212e" : DIM }}>
              {n}/280{over ? " — too long for one tweet" : ""}
            </span>
            {footer}
          </div>
        )}
      </div>
    </article>
  );
}
