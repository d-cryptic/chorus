"""rank_tune had NEVER run: "need both accepted and dismissed feedback".

The user posts the good suggestions and ignores the rest — they do not click Dismiss. Real
tally: 10 posted, 0 dismissed. So the learning loop starved while the rejection signal sat
right there in the queue as `expired`. An ignored suggestion IS a soft no.

But expiry is only evidence if the user was PRESENT. If they were away for a day, everything
expires and that says nothing about their taste — counting it would teach the ranker that
whatever it suggested on a busy Tuesday is bad.
"""
import datetime
import rank_tune as R

DAY = 86400000
T = 1784000000000
d = lambda ts: datetime.date.fromtimestamp(ts / 1000).isoformat()


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    fb = [{"action": "posted", "ts": T},
          {"action": "dismissed", "ts": T - DAY},
          {"action": "expired", "ts": T},          # same day as a post
          {"action": "expired", "ts": T - 40 * DAY}]  # a day with no activity
    act = R.active_days(fb)
    chk(d(T) in act, "a day with a post is active")
    chk(d(T - DAY) in act, "a day with a dismiss is active")
    chk(d(T - 40 * DAY) not in act, "a day with only expiries is NOT active")
    chk(R.active_days([]) == set(), "no feedback -> no active days")
    chk(R.active_days([{"action": "expired", "ts": T}]) == set(),
        "expiries alone never make a day active (that would be circular)")

    # weights: a considered no outranks a shrug; a shrug you never saw is not evidence
    chk(R.negative_weight("dismissed", True) == 1.0, "explicit dismiss = full weight")
    chk(R.negative_weight("expired", True) == 0.35, "expiry while present = partial weight")
    chk(R.negative_weight("expired", False) == 0.0, "expiry while absent = ignored")
    chk(R.negative_weight("posted", True) == 0.0, "a post is not a rejection")
    chk(R.negative_weight("snoozed", True) == 0.0, "unknown action contributes nothing")
    chk(R.negative_weight("expired", True) < R.negative_weight("dismissed", True),
        "a shrug must never outweigh a considered no")

    print(f"RANK TUNE UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
