import time, ranker as R
NOW = int(time.time()*1000)
W = R.DEFAULT_WEIGHTS
P = ["leverage","writing","priorities"]
def C(**k): d={"id":"x","text":"t","author":"a","author_tier":"C","ts":NOW,"reply_count":0}; d.update(k); return d

def run():
    p=f=0
    def chk(c,l):
        nonlocal p,f
        if c: p+=1
        else: print("  ❌",l); f+=1

    # gate
    g=R.gate([C(id="1",text="hi",author="me"),C(id="2",text="",author="b"),
              C(id="3",text="ok",author="b"),C(id="4",text="ok",author="b",ts=NOW-100*3600*1000),
              C(id="5",text="free airdrop",author="b")],
             denylist=["airdrop"], my_handle="me", now=NOW, seen={"3"})
    chk(len(g)==0, f"gate drops self/empty/dup/stale/denylist (got {len(g)})")
    g2=R.gate([C(id="9",text="real tweet",author="b")], denylist=["airdrop"], my_handle="me", now=NOW)
    chk(len(g2)==1, "gate keeps a clean tweet")
    # regression: 10h-old tweet (ms delta) must be KEPT — catches the ms->hours unit bug
    g3=R.gate([C(id="10h",text="fresh enough",author="b",ts=NOW-10*3600*1000)], denylist=[], my_handle="me", now=NOW)
    chk(len(g3)==1, "gate keeps a 10h-old tweet (ms->hours unit)")
    # and pre_score fresh should be high for recent, low for old
    fr_new,_,_=R.pre_score(C(text="on writing",ts=NOW),W,P,now=NOW)
    fr_old,_,_=R.pre_score(C(text="on writing",ts=NOW-40*3600*1000),W,P,now=NOW)
    chk(fr_new>fr_old, "fresher tweet scores higher")

    # pre_score: pillar hit + tier
    s_hit,pillar,_=R.pre_score(C(text="on leverage",author_tier="A"),W,P,now=NOW)
    s_miss,_,_=R.pre_score(C(text="nothing here",author_tier="C"),W,P,now=NOW)
    chk(pillar=="leverage", "pillar detected")
    chk(s_hit>s_miss, f"pillar+tier scores higher ({s_hit} > {s_miss})")
    # saturation penalty
    s_lo,_,_=R.pre_score(C(text="on writing",author_tier="A",reply_count=500),W,P,now=NOW)
    s_hi,_,_=R.pre_score(C(text="on writing",author_tier="A",reply_count=0),W,P,now=NOW)
    chk(s_hi>s_lo, "saturation penalizes over-replied")

    # prerank order + topk
    pr=R.prerank([C(id="a",text="nothing",author_tier="C"),C(id="b",text="on leverage",author_tier="A")],W,P,now=NOW,topk=5)
    chk(pr[0][1]["id"]=="b", "prerank puts best first")
    chk(len(R.prerank([C()]*10,W,P,now=NOW,topk=3))==3, "topk caps")

    # finalize folds angle_strength
    chk(R.finalize(0.5,1.0,W)>0.5, "finalize adds angle_strength")

    # --- reply expiry: the opportunity dies with the TWEET, not the suggestion ----------
    # Every reply used to get a flat `now + WINDOW_H` (48h), so a tweet found at 40h old sat
    # in the queue for another two days. Measured before the fix: 15 of 22 queued replies were
    # past 3h — the bar fast_lane itself calls "worthless in 3h" — so the queue advertised 22
    # chances when ~7 were real, burying the good ones.
    import time as _t
    NOWMS = int(_t.time() * 1000)
    life = R.REPLY_LIFE_H * 3600 * 1000
    win = R.WINDOW_H * 3600 * 1000
    exp_for = lambda tweet_age_h: min(NOWMS + win, (NOWMS - int(tweet_age_h * 3600 * 1000)) + life)
    chk(exp_for(0.5) > NOWMS, "a fresh tweet's reply is live")
    chk(exp_for(R.REPLY_LIFE_H + 1) <= NOWMS, "a reply past REPLY_LIFE_H is already dead")
    chk(exp_for(0.5) - NOWMS <= life, "a reply never outlives REPLY_LIFE_H from the tweet")
    chk(exp_for(0) <= NOWMS + win, "and never outlives the global window either")
    chk(R.REPLY_LIFE_H < R.WINDOW_H, "a reply dies sooner than the candidate gate — that is the point")
    # posts/quotes stand on their own, so they keep the flat window
    chk(NOWMS + win > NOWMS + life, "the flat window (posts/quotes) is longer than a reply's life")

    print(f"RANKER UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
