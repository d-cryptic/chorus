#!/usr/bin/env python3
"""Swappable notify layer. NOTIFY_PROVIDER = telegram | discord | whatsapp | console (default console).
- telegram : Telegram bot sendMessage (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) — simplest, free.
- whatsapp : POST {text} to WHATSAPP_WEBHOOK_URL — route via a Hermes WhatsApp connector or a
             WhatsApp bridge. (WhatsApp Business API needs Meta approval; unofficial bridges carry
             ban risk — hence Telegram is the v1 default.)
- console  : print (dev / v1-with-Telegram-deferred).
- discord  : webhook POST to DISCORD_WEBHOOK_URL (zero bot for one-way push).
Swap by env only; digest.py just calls notify.send(text).
"""
import os, json, urllib.request

def _post(url, body, headers=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    r.add_header("user-agent", "chorus-box/1.0")
    r.add_header("content-type", "application/json")
    for k, v in (headers or {}).items():
        r.add_header(k, v)
    with urllib.request.urlopen(r, timeout=20) as resp:
        return resp.read()

def _telegram(text):
    bot, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    _post(f"https://api.telegram.org/bot{bot}/sendMessage", {"chat_id": chat, "text": text})

def _whatsapp(text):
    url = os.environ["WHATSAPP_WEBHOOK_URL"]  # Hermes gateway or bridge endpoint
    hdr = {"authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}"} if os.environ.get("WHATSAPP_TOKEN") else {}
    _post(url, {"text": text}, hdr)

def _discord(text):
    _post(os.environ["DISCORD_WEBHOOK_URL"], {"content": text})   # webhook: zero bot needed for push

def _console(text):
    print(text)

PROVIDERS = {"telegram": _telegram, "discord": _discord, "whatsapp": _whatsapp, "console": _console}

def send(text):
    name = os.environ.get("NOTIFY_PROVIDER", "console").lower()
    PROVIDERS.get(name, _console)(text)
