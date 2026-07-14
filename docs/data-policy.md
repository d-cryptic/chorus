# Chorus — data policy (retention & deletion)

Detailed summary: Chorus builds ~150 dossiers on real people (public posts, cross-platform
edges, voice models) plus your own profile. Public-source only; per-kind TTL; one-command
target deletion; GDPR cascade spans Convex/D1 + Supermemory. Enriching non-public sources is
prohibited. Solo scale is not an exemption.

## Sources
Public data only (X public tweets, GitHub, Reddit, YouTube, HN, public web). Never authenticated
private data, never others' DMs, never others' private likes (private since 2024 anyway).

## Retention (TTL by kind)
| kind | store | TTL |
|---|---|---|
| your profile / voice (`chorus:self`) | Supermemory | indefinite (yours) |
| target person record / posts | Supermemory | 180d since last interaction, then purge |
| target voice model | Supermemory | refreshed on drift; purged with the person |
| suggestions / feedback | queue store | 90d, then archive/delete |
| research briefs | Supermemory | 365d |

## Deletion
- `forget-target <handle>` — `box/forget_target.py <handle>` deletes the Supermemory container
  tag `chorus:target:<handle>` + their queue rows (via `/api/box/forget`). One command.
- **GDPR "delete me" cascade** — a single op that removes your Convex/D1 rows AND calls
  Supermemory `forget`/document-delete for `chorus:*`. Neither store owns it alone.
- On request from a profiled person: `forget-target` + add to a do-not-enrich list.

## Rules
- **Chorus NEVER uses account-level sessions** — not X, not Telegram, not anything. Only **bot
  tokens** (separate identities) + **read API keys**. No userbot / MTProto, no X session cookies,
  no logging in "as you". The most it ever holds is a bot token + read keys; your personal logins
  stay yours. (This is why it can't join/leave your groups, post as you, or read your DMs.)
- Enrich only public sources. No credential-based access to any platform for reads.
- No outreach/DM automation. Suggest-only; you act.
