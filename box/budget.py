#!/usr/bin/env python3
"""
import osChorus budget guard — cost ceiling, kill-switch, autonomy, provider breaker.

Summary: ports the v0 nakama BudgetTracker semantics. The rule that matters is
`would_exceed` is checked BEFORE every paid call (v0: "no silent skip/shallow —
hard-stop + alert over silent degrade"), spend is recorded as it is INCURRED (not
estimated after the run), and a breach pauses + checkpoints + alerts. Also carries a
global kill-switch independent of budget, and a SEPARATE provider-reliability circuit
breaker (closed -> open -> cooldown, then dead-letter) that wraps any provider call.
Pure + unit-testable: no network here, callers own I/O.

v0 mapping: BudgetTracker (packages/core/src/budget.ts), flags:scraping_kill,
scraping-deep-dive breaker/DLQ, agentic-infra autonomy levels.
"""
from __future__ import annotations
import os

# ---- cost model -------------------------------------------------------------
# USD per unit. Deliberately conservative: over-estimating pauses early (safe),
# under-estimating overspends (unsafe). Tune from the spend_ledger, not vibes.
RATES = {
    "candidate_read": 0.00015,  # one fetched tweet from the read adapter
    "llm_draft": 0.0003,        # one drafting call (deepseek-chat class)
    "llm_judge": 0.0002,        # one quality-judge call
    "llm_synth": 0.0020,        # one insight/playbook synthesis call (bigger prompt)
    "embed": 0.00002,           # one embedded text
    "research": 0.0010,         # one web-research search
    "enrich": 0.0,              # GitHub/HN/Reddit public APIs — free
}


class BudgetError(Exception):
    """Base: a paid call was refused. Carries a machine-readable reason."""

    reason = "budget"


class Killed(BudgetError):
    reason = "kill_switch"


class Paused(BudgetError):
    reason = "paused"


class QuietHours(BudgetError):
    reason = "quiet_hours"


class BudgetExceeded(BudgetError):
    reason = "ceiling"


_LLM_OPS = {"llm_draft", "llm_judge", "llm_synth"}


def _drafting_is_subscription() -> bool:
    """True when drafting routes through a $0-marginal SUBSCRIPTION (grok/codex via Hermes or a
    logged-in CLI). Then LLM calls cost no real money, so they must not consume the ceiling that
    exists to cap REAL spend (twitterapi reads). Phantom LLM estimates eating the read budget is
    exactly what blocked fetches with the whole account on free subscriptions."""
    p = os.environ.get("CHORUS_DRAFT_PROVIDER", "")
    return p.startswith("hermes:") or p.startswith("cli:")


def estimate_cost_usd(op: str, count: int = 1) -> float:
    """Cost of `count` units of `op`. Unknown ops are NOT free — refuse to guess.

    LLM ops (draft/judge/synth) are $0 when drafting is on a subscription: the real cost is the
    subscription flat fee, not per-call, so counting per-call estimates against the ceiling
    phantom-blocks real reads. Reads/research/embeds still cost real money and are always counted."""
    if op not in RATES:
        raise KeyError(f"no rate for op {op!r}; add it to RATES (never assume free)")
    if op in _LLM_OPS and _drafting_is_subscription():
        return 0.0
    return round(RATES[op] * max(0, count), 6)


def in_quiet_hours(hour_local: int, quiet: str | None) -> bool:
    """quiet is 'HH-HH' local, e.g. '23-7' (wraps midnight). Empty/None = never quiet."""
    if not quiet:
        return False
    try:
        start_s, end_s = quiet.split("-", 1)
        start, end = int(start_s), int(end_s)
    except (ValueError, AttributeError):
        return False  # malformed config must not silently block the whole agent
    if start == end:
        return False
    if start < end:
        return start <= hour_local < end
    return hour_local >= start or hour_local < end  # wraps midnight


class BudgetTracker:
    """Gate every paid call. `check()` BEFORE spending; `record()` when incurred.

    spent_remote = today's ledger total from the Worker at cycle start.
    spent_local  = what this process has incurred since (not yet necessarily flushed),
    so the ceiling binds mid-cycle even if the ledger POST is failing.
    """

    def __init__(self, spent: float = 0.0, ceiling: float = 0.65, *,
                 paused: bool = False, killed: bool = False,
                 quiet: str | None = None, hour_local: int | None = None,
                 on_demand: bool = False):
        self.spent_remote = float(spent)
        self.ceiling = float(ceiling)
        self.paused = bool(paused)
        self.killed = bool(killed)
        self.quiet = quiet
        self.hour_local = hour_local
        self.on_demand = on_demand
        self.spent_local = 0.0
        self.ledger: list[tuple[str, int, float]] = []  # (op, count, usd) not yet flushed

    @property
    def spent(self) -> float:
        return round(self.spent_remote + self.spent_local, 6)

    def remaining(self) -> float:
        return round(max(0.0, self.ceiling - self.spent), 6)

    def would_exceed(self, op: str, count: int = 1) -> bool:
        return self.spent + estimate_cost_usd(op, count) > self.ceiling

    def check(self, op: str, count: int = 1) -> float:
        """Raise if this paid call must not happen. Returns its estimated cost.

        Order matters: kill-switch is absolute and beats everything else.
        """
        if self.killed:
            raise Killed("global kill-switch is on")
        if self.paused:
            raise Paused("agent is paused via settings")
        # Quiet hours stop AUTOMATIC polling while the user is asleep. A human pressing
        # Fetch is proof they are awake, so an explicit request overrides it -- otherwise the
        # button silently does nothing during the very window a night owl would use it, which
        # is indistinguishable from "the product is broken".
        # Kill/pause above are NOT overridable: those are safety, not scheduling.
        if (self.hour_local is not None and not self.on_demand
                and in_quiet_hours(self.hour_local, self.quiet)):
            raise QuietHours(f"within quiet hours {self.quiet}")
        usd = estimate_cost_usd(op, count)
        if self.spent + usd > self.ceiling:
            raise BudgetExceeded(
                f"{op}x{count} (${usd}) would exceed ceiling ${self.ceiling} "
                f"(spent ${self.spent})")
        return usd

    def record(self, op: str, count: int = 1) -> float:
        """Book the spend as incurred. Call AFTER the paid call succeeds/attempts."""
        usd = estimate_cost_usd(op, count)
        self.spent_local = round(self.spent_local + usd, 6)
        self.ledger.append((op, count, usd))
        return usd

    def try_spend(self, op: str, count: int = 1) -> float:
        """check() + record() — for callers that don't need them separated."""
        self.check(op, count)
        return self.record(op, count)

    def flush(self) -> float:
        """Total pending spend; caller POSTs it and calls `flushed()` on success."""
        return round(sum(u for _, _, u in self.ledger), 6)

    def flushed(self) -> None:
        self.spent_remote = self.spent
        self.spent_local = 0.0
        self.ledger.clear()


# ---- provider reliability breaker (distinct from the budget ceiling) ---------

CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"


class CircuitBreaker:
    """Reliability breaker for a flaky provider. NOT the budget breaker.

    closed -> (failures >= threshold) -> open -> (cooldown elapsed) -> half_open
    half_open: one trial; success closes, failure re-opens. Callers route to a
    fallback provider (or dead-letter) while open, per the v0 routing matrix.
    """

    def __init__(self, threshold: int = 3, cooldown_s: float = 60.0, *, now: float = 0.0):
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self.failures = 0
        self.state = CLOSED
        self.opened_at = 0.0
        self._now = now

    def _tick(self, now: float | None) -> float:
        if now is not None:
            self._now = now
        return self._now

    def allows(self, now: float | None = None) -> bool:
        t = self._tick(now)
        if self.state == OPEN and t - self.opened_at >= self.cooldown_s:
            self.state = HALF_OPEN  # auto-reset after cool-down
        return self.state in (CLOSED, HALF_OPEN)

    def on_success(self, now: float | None = None) -> None:
        self._tick(now)
        self.failures = 0
        self.state = CLOSED

    def on_failure(self, now: float | None = None) -> None:
        t = self._tick(now)
        self.failures += 1
        if self.state == HALF_OPEN or self.failures >= self.threshold:
            self.state = OPEN
            self.opened_at = t
