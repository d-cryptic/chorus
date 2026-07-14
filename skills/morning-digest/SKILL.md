---
name: morning-digest
description: Daily Telegram digest — top suggestions + spend + cycle health.
---

# morning-digest

## Purpose
One daily Telegram message (FE6) that doubles as the heartbeat (G5). A silent empty queue is the
default failure mode; this is how you notice the cycle died, X read adapter returned junk, or
budget-guard denied everything.

## Steps
1. Read via box endpoints: top queued (`GET /api/suggestions` needs the dashboard; box uses its own read or the DB), `GET /api/box/spend`, `GET /api/status`. (v1: box reads what it needs through /api/box/*.)
2. Format compactly: `score · @author · one-line angle`; `spend $x / $ceiling`; `last cycle Nh ago`.
3. Send via Hermes `messaging` to `TELEGRAM_CHAT_ID`. If the last cycle errored or produced 0,
   send an ALERT instead of the normal digest.

## Schedule
Daily 08:00 IST, after the cycle. Pin the bot to `TELEGRAM_CHAT_ID` — ignore all other senders.
