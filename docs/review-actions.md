# Chorus — review actions (Fable design review, 2026-07-13)

Detailed summary: Triaged findings from the Fable adversarial review. Status legend: ✅ fixed
this pass · 🔜 planned (captured, not yet built) · ❓ needs your decision. The five that matter
most: gate has real holes (F1 workers.dev bypass, F2 fail-open) ✅; two-level subdomains break
free TLS (F3) ❓; no box→queue write path (F4) ✅ via ingest token; ranker LLM-before-prune blows
budget (F5) ✅; feedback→ranking loop doesn't close (G1) ✅ partial. Nothing here weakens the
suggest-only, single-user, low-cost thesis.

## Fixes
| id | issue | status |
|---|---|---|
| F1 | `workers.dev` route bypasses Access → API exposed | ✅ `workers_dev=false` + runbook 404-check |
| F2 | Worker email check is fail-open + header-spoofable | ✅ fail-closed + **full Access-JWT verify (jose)** + ingest token |
| F3 | 2-level subdomains not covered by free Universal SSL → TLS breaks (or +$10/mo ACM) | ❓ flatten vs ACM — decision |
| F4 | no codified box→queue write path (D1 not reachable by daemon) | ✅ `POST /api/ingest` + `POST /api/spend` w/ bearer `INGEST_TOKEN` |
| F5 | opportunity-rank runs LLM+profile per candidate before pruning → budget fiction | ✅ two-stage: cheap pre-score → top-K → LLM; profile once/run |
| F6 | budget numbers contradict 3–7× ($0.20–0.65 vs ceiling 1.50) | ✅ ceiling 0.65, soft/hard split |
| F7 | runbook gate-proof `curl -L` masks the 302 it tells you to expect | ✅ dropped `-L` |
| F8 | dup / expiry / snooze | ✅ UNIQUE(tweet_id) + snooze + expiry filter + **[triggers] cron wired** |
| F9 | assorted correctness | ✅ sshd drop-in + cloudflared pin + **Doppler pull (built + render-tested)** |

## Gaps
| id | issue | status |
|---|---|---|
| G1 | feedback→ranking loop | ✅ M0 path complete: posted-edited capture + `rank-tune` + `weights` via `/api/box/*`; the box→Supermemory mirror is a box-cron (build with the ranker) |
| G2 | D1 vs Convex both declared canonical | ✅ declared **M0=D1 (shipped), M1=Convex** everywhere |
| G3 | Convex (`*.convex.cloud`) is outside Cloudflare Access | ✅ decision: **self-host Convex behind the tunnel** (Auth section in data-architecture) |
| G4 | onboarding / cold-start unhandled | ✅ `onboard-self` skill + day-0 mode note |
| G5 | zero observability | ✅ run_log + header heartbeat + **healthcheck cron** + Telegram alert (morning-digest) |
| G6 | backups/recovery unstated | ✅ `docs/backups.md` (export/versioning/rebuild drill); 🔜 wire the box cron |
| G7 | X-read ToS posture one-word deep | ✅ honest paragraph + `x-read-lane` candidate-source wording |
| G8 | third-party personal data retention/deletion | ✅ `docs/data-policy.md` + `forget-target` note |
| G9 | provisioning secrets | ✅ cloud-init env + **working Doppler runtime-pull option** (secrets out of state) |
| G10 | Hermes itself unvalidated | ✅ "M0.5 validate Hermes" runbook gate |

## Features (thesis-aligned)
| id | feature | status |
|---|---|---|
| FE1 | outcome tracking | ✅ `outcome-track` skill + `outcome` table + `/api/box/outcome` (adapter=X read adapter, deploy-gated) |
| FE2 | one-tap X intent-URL "open reply" + view-tweet link | ✅ in dashboard |
| FE3 | "posted (edited)" paste-back capture | ✅ (closes G1) |
| FE4 | dashboard pause/kill + quiet hours + ceiling via `settings` | ✅ table + read path; 🔜 header toggle UI |
| FE5 | weekly review pane | ✅ `/api/review` + `review.html` |
| FE6 | morning Telegram digest | ✅ `box/digest.py` (format unit-tested) + `/api/box/digest` |

## Cuts (agreed)
- ✅ Strike PRD-09 experiments/themes + PRD-11 media-render rows from `data-architecture.md` — nakama ambitions, out-of-scope for Chorus.
- ✅ Delete the apify/LinkedIn/IG port ("HIGH ban risk" has no place in a zero-ban-risk product).
- ✅ Drop the "Convex vector search" mention — one brain (Supermemory).
- ❓ Wildcard Access app — removed only if we flatten hostnames (F3 decision).

## Fable review #2 (2026-07-13) — security + flows + priorities
**Security fixes applied:** ✅ secret-scan.sh self-match fixed · ✅ gitleaks tightened (path-scoped) ·
✅ `nakama-tfstate` bucket name scrubbed · ✅ README claim made accurate. **Accepted, documented:**
the CF *account id* remains in early git history — an identifier, not a credential (R2 keys are
env-only); we did not rewrite public history. **Biggest exposure:** all runtime secrets aggregate in
TF state + user_data → mitigated by `use_doppler=true` (built; recommended in README).

**Flow reality (Fable was right):** the CF/D1 shell is real+tested; the AGENT that fills it is not
built. Fixed the concrete M0 blocker (box could only POST → now `/api/box/*` GET+POST, tested). **Now built + tested: the ranker** (`box/ranker.py` — gate→pre-score→LLM→ingest, 10 unit + live e2e;
caught an ms→hours bug). Now built: feedback mirror ✅, **X read adapter ✅** (real schema, mapping unit-tested; live fetch = deploy-gated), onboard-self ✅. Cron IS the cycle runner (box/crontab.example).

**v1 build order (Fable):** 1) deploy + prove gate · 2) M0.5 validate Hermes (can it do authed POSTs?
if not, pivot the ranker to a plain Python script) · 3) box read/write endpoints ✅ DONE · 4) **the ranker** ✅ BUILT+TESTED (`box/ranker.py`) · 5) Telegram digest ✅ (box/digest.py) · 6) M0 feedback mirror ✅ (box/mirror_feedback.py) · 7) secrets hardening ✅.
**Frozen for v1:** the entire Convex M1 migration, cross-platform enrich fan-out, embeddings.

## Decisions 2026-07-13 (user)
- **Supermemory: self-hosted local** (OSS on the box) — `SUPERMEMORY_BASE_URL`, key optional. No cloud key.
- **the private X read adapter: reads only** (suggest-only never posts) — key + target usernames; no X login.
- **Research layer swappable** — `box/research.py`, `RESEARCH_PROVIDER=linkup` (default) or `firecrawl`.
- **Notify swappable** — `box/notify.py` (`NOTIFY_PROVIDER` telegram|whatsapp|console). Telegram default; WhatsApp via Hermes gateway/bridge later. Deferred for v1.
- **Adapters LIVE-VERIFIED** — the private X read adapter (20 real tweets mapped) + Linkup (real search) both work against live APIs.
- **R2 state bucket `chorus-tfstate` created** (private) on account 1c63a2…d833; needs R2 S3 keys (dashboard) or use local state.
- **R2 state: create a new private bucket**; CF account id from the emulated .env's CF token.
