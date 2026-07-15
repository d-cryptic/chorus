#!/usr/bin/env python3
"""Interactive Telegram bot — act on suggestions from your phone. Long-polls getUpdates, sends
queued suggestions with inline buttons (posted / snooze / dismiss) + an 'open reply' intent URL.
Button taps -> POST /api/box/action. Pinned to TELEGRAM_CHAT_ID (ignores everyone else).
Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, INGEST_URL, INGEST_TOKEN. (Telegram deferred for v1.)
"""
import os, json, time, urllib.request, urllib.parse

BOT = os.environ["TELEGRAM_BOT_TOKEN"]; CHAT = str(os.environ["TELEGRAM_CHAT_ID"])
API = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/"); TOK = os.environ.get("INGEST_TOKEN", "")
TG = f"https://api.telegram.org/bot{BOT}"

def tg(method, **params):
    r = urllib.request.Request(f"{TG}/{method}", data=json.dumps(params).encode(), method="POST")
    r.add_header("user-agent", "chorus-box/1.0")
    r.add_header("content-type", "application/json")
    return json.loads(urllib.request.urlopen(r, timeout=45).read())

def box(method, path, body=None):
    r = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None, method=method)
    r.add_header("user-agent", "chorus-box/1.0")
    r.add_header("content-type", "application/json")
    if TOK: r.add_header("authorization", "Bearer " + TOK)
    return json.loads(urllib.request.urlopen(r, timeout=20).read())

def kb(sid, tweet_id, draft):
    intent = f"https://x.com/intent/post?text={urllib.parse.quote(draft)}" + (f"&in_reply_to={tweet_id}" if tweet_id else "")
    return {"inline_keyboard": [
        [{"text": "open reply ↗", "url": intent}],
        [{"text": "✓ posted", "callback_data": f"posted|{sid}"},
         {"text": "⏱ snooze", "callback_data": f"snoozed|{sid}"},
         {"text": "✕ dismiss", "callback_data": f"dismissed|{sid}"}]]}

def send_queue():
    q = box("GET", "/api/box/queue?limit=5").get("queue", [])
    if not q:
        tg("sendMessage", chat_id=CHAT, text="nothing queued 🎉"); return
    for s in q:
        drafts = json.loads(s["drafts"]) if isinstance(s.get("drafts"), str) else (s.get("drafts") or [])
        d0 = drafts[0] if drafts else ""
        txt = f"[{s['score']}] @{s['author_handle']}\n{(s.get('tweet_text') or '')[:120]}\n\n💬 {d0}"
        tg("sendMessage", chat_id=CHAT, text=txt, reply_markup=kb(s["id"], s.get("tweet_id"), d0))

def loop():
    off = 0
    tg("sendMessage", chat_id=CHAT, text="Chorus bot up. Send /queue for suggestions.")
    while True:
        try:
            r = tg("getUpdates", offset=off, timeout=30)
        except Exception:
            time.sleep(3); continue
        for u in r.get("result", []):
            off = u["update_id"] + 1
            msg, cb = u.get("message"), u.get("callback_query")
            if msg and str(msg["chat"]["id"]) == CHAT and (msg.get("text", "") or "").startswith("/queue"):
                send_queue()
            elif cb and str(cb["message"]["chat"]["id"]) == CHAT:
                action, sid = cb["data"].split("|", 1)
                try:
                    box("POST", "/api/box/action", {"id": sid, "action": action})
                except Exception:
                    pass
                tg("answerCallbackQuery", callback_query_id=cb["id"], text=action)
                tg("editMessageReplyMarkup", chat_id=CHAT, message_id=cb["message"]["message_id"],
                   reply_markup={"inline_keyboard": [[{"text": f"— {action} —", "callback_data": "noop"}]]})

if __name__ == "__main__":
    loop()
