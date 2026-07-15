import budget as B

def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # ---- cost model ----
    chk(B.estimate_cost_usd("llm_draft", 2) == 0.0006, "estimate scales with count")
    chk(B.estimate_cost_usd("enrich", 5) == 0.0, "free op costs 0")
    try:
        B.estimate_cost_usd("nope"); chk(False, "unknown op must raise")
    except KeyError:
        chk(True, "unknown op raises (never assume free)")

    # ---- ceiling ----
    t = B.BudgetTracker(spent=0.0, ceiling=0.01)
    chk(not t.would_exceed("llm_draft", 1), "cheap call under ceiling")
    chk(t.would_exceed("llm_draft", 100), "100 drafts exceed a $0.01 ceiling")
    t.check("llm_draft", 1)  # must not raise
    chk(True, "check passes under ceiling")
    try:
        t.check("llm_draft", 100); chk(False, "over-ceiling must raise")
    except B.BudgetExceeded as e:
        chk(e.reason == "ceiling", "over-ceiling raises BudgetExceeded")

    # ---- THE BUG FIX: ceiling binds mid-cycle from local spend alone ----
    t2 = B.BudgetTracker(spent=0.0, ceiling=0.001)
    t2.record("llm_draft", 3)  # 0.0009 incurred, never flushed to the Worker
    chk(t2.spent == 0.0009, "local spend counts immediately")
    try:
        t2.check("llm_draft", 1); chk(False, "must bind on unflushed local spend")
    except B.BudgetExceeded:
        chk(True, "ceiling binds mid-cycle even if ledger POST never happened")

    # ---- kill-switch beats everything ----
    k = B.BudgetTracker(spent=0.0, ceiling=99.0, killed=True)
    try:
        k.check("llm_draft"); chk(False, "kill-switch must raise")
    except B.Killed:
        chk(True, "kill-switch refuses even with budget available")
    kp = B.BudgetTracker(killed=True, paused=True)
    try:
        kp.check("llm_draft")
    except B.BudgetError as e:
        chk(e.reason == "kill_switch", "kill-switch takes precedence over paused")

    # ---- paused ----
    pz = B.BudgetTracker(ceiling=99.0, paused=True)
    try:
        pz.check("llm_draft"); chk(False, "paused must raise")
    except B.Paused:
        chk(True, "paused refuses paid calls")

    # ---- quiet hours ----
    chk(B.in_quiet_hours(23, "23-7"), "23 is inside wrapping window 23-7")
    chk(B.in_quiet_hours(3, "23-7"), "3 is inside wrapping window 23-7")
    chk(not B.in_quiet_hours(12, "23-7"), "midday outside wrapping window")
    chk(B.in_quiet_hours(10, "9-17"), "normal window")
    chk(not B.in_quiet_hours(18, "9-17"), "outside normal window")
    chk(not B.in_quiet_hours(3, None), "no config = never quiet")
    chk(not B.in_quiet_hours(3, "garbage"), "malformed config must not block agent")
    chk(not B.in_quiet_hours(3, "5-5"), "empty window never quiet")
    q = B.BudgetTracker(ceiling=99.0, quiet="23-7", hour_local=2)
    try:
        q.check("llm_draft"); chk(False, "quiet hours must raise")
    except B.QuietHours:
        chk(True, "quiet hours refuses paid calls")

    # ---- accounting ----
    a = B.BudgetTracker(spent=0.1, ceiling=0.65)
    a.record("llm_draft", 10)   # 0.003
    chk(a.spent == 0.103, "spent = remote + local")
    chk(a.remaining() == 0.547, "remaining subtracts both")
    chk(a.flush() == 0.003, "flush totals pending ledger")
    a.flushed()
    chk(a.spent == 0.103 and a.flush() == 0.0, "flushed folds local into remote, clears")
    chk(a.try_spend("embed", 1) == 0.00002, "try_spend checks then records")

    # ---- provider breaker ----
    cb = B.CircuitBreaker(threshold=3, cooldown_s=60, now=0)
    chk(cb.allows(0), "breaker starts closed")
    cb.on_failure(0); cb.on_failure(0)
    chk(cb.state == B.CLOSED and cb.allows(0), "below threshold stays closed")
    cb.on_failure(0)
    chk(cb.state == B.OPEN, "threshold opens breaker")
    chk(not cb.allows(1), "open breaker blocks calls")
    chk(not cb.allows(59), "still open before cooldown")
    chk(cb.allows(60) and cb.state == B.HALF_OPEN, "auto-resets to half_open after cooldown")
    cb.on_success(61)
    chk(cb.state == B.CLOSED and cb.failures == 0, "half_open success closes breaker")
    cb2 = B.CircuitBreaker(threshold=3, cooldown_s=10, now=0)
    for _ in range(3): cb2.on_failure(0)
    cb2.allows(10)  # -> half_open
    cb2.on_failure(10)
    chk(cb2.state == B.OPEN and cb2.opened_at == 10, "half_open failure re-opens immediately")

    # --- on_demand: scheduling is overridable, safety is not -------------------
    # The user pressed Fetch and the ranker skipped it. Quiet hours exist to stop AUTOMATIC
    # polling while they sleep; a human clicking the button is proof they are awake. The
    # button silently doing nothing is indistinguishable from a broken product.
    q = lambda **k: B.BudgetTracker(spent=0, ceiling=10, quiet="0-7", hour_local=3, **k)
    try:
        q().check("llm_draft"); chk(False, "cron inside quiet hours must be blocked")
    except B.QuietHours: chk(True, "cron inside quiet hours is blocked")
    try:
        q(on_demand=True).check("llm_draft"); chk(True, "on_demand overrides quiet hours")
    except B.QuietHours: chk(False, "on_demand must override quiet hours")
    # safety must NOT be overridable by a click
    for flag, exc, name in ((dict(killed=True), B.Killed, "killed"), (dict(paused=True), B.Paused, "paused")):
        try:
            B.BudgetTracker(spent=0, ceiling=10, on_demand=True, **flag).check("llm_draft")
            chk(False, f"on_demand must NOT override {name} (safety)")
        except exc: chk(True, f"on_demand does not override {name}")
    # nor the ceiling: on_demand is not a licence to overspend
    try:
        B.BudgetTracker(spent=9.999, ceiling=10, on_demand=True).check("llm_synth")
        chk(False, "on_demand must NOT override the ceiling")
    except B.BudgetExceeded: chk(True, "on_demand does not override the ceiling")

    print(f"BUDGET UNIT: {p} passed, {f} failed"); return f

import sys; sys.exit(run())
