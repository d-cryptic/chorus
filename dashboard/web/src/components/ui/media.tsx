import { cn } from "@/lib/utils";

type M = { type?: string; url?: string; page?: string };

/** X renders media in a 16px-rounded frame with a hairline border, 1-4 up.
 *  Real media matters for judgement: an image-led tweet reads completely
 *  differently, and we were showing text only. */
export function MediaGrid({ media }: { media: M[] }) {
  const items = (media || []).filter((m) => m.url).slice(0, 4);
  if (!items.length) return null;
  return (
    <div
      className={cn(
        "mt-3 grid gap-0.5 overflow-hidden rounded-2xl border border-[#2f3336]",
        items.length === 1 ? "grid-cols-1" : "grid-cols-2"
      )}
      style={{ maxHeight: 290 }}
    >
      {items.map((m, i) => (
        <a key={i} href={m.page || m.url} target="_blank" rel="noreferrer"
           className={cn("relative block bg-[#16181c]", items.length === 3 && i === 0 && "row-span-2")}>
          <img
            src={m.url}
            alt=""
            loading="lazy"
            referrerPolicy="no-referrer"
            className="h-full w-full object-cover"
            style={{ maxHeight: items.length === 1 ? 290 : 145 }}
          />
          {m.type && m.type !== "photo" && (
            <span className="absolute bottom-1.5 left-1.5 rounded px-1 py-0.5 text-[10px] font-bold uppercase"
                  style={{ background: "rgba(0,0,0,.75)", color: "#fff" }}>
              {m.type === "animated_gif" ? "GIF" : m.type}
            </span>
          )}
        </a>
      ))}
    </div>
  );
}
