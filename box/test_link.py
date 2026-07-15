"""link_context: give the drafter the page behind the URL, so it stops inventing specifics.

A tweet is ATTACKER-CONTROLLED text and this box runs internal services on localhost
(supermemory :6767, chorus-memory :8000) inside a cloud VPC (metadata at 169.254.169.254).
Fetching a URL out of a stranger's tweet without an SSRF guard would let anyone make the box
GET its own memory store or its cloud credentials -- and then feed the response to an LLM.
These tests exist so that guard can never be quietly removed.
"""
import ranker as R, generate as G

def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # --- SSRF: everything internal must be refused ---
    for url, why in [("http://127.0.0.1:6767/v3/documents", "our own supermemory"),
                     ("http://localhost:8000/v3/search", "our own memory shim"),
                     ("http://169.254.169.254/latest/meta-data/", "cloud metadata = creds"),
                     ("http://10.0.0.5/x", "RFC1918"),
                     ("http://192.168.1.1/", "LAN"),
                     ("http://[::1]:80/", "ipv6 loopback"),
                     ("file:///etc/passwd", "file scheme"),
                     ("ftp://example.com/x", "non-http scheme")]:
        chk(R._public_url(url) is False, f"SSRF must refuse {url} ({why})")
    chk(R._public_url("https://news.ycombinator.com/") is True, "public URL must be allowed")

    # --- no link => free and empty, never a fetch ---
    chk(R.link_context("just shipped a vector db, no url here") == "", "no URL -> empty")
    chk(R.link_context("") == "", "empty text -> empty")
    chk(R.link_context(None) == "", "None -> empty, no crash")

    # --- a tweet carrying an internal URL must not be fetched ---
    chk(R.link_context("look http://127.0.0.1:6767/v3/documents") == "",
        "SSRF via tweet text is refused")

    # --- the drafter's rule 1 must list <link> as legitimate, or it forbids its own data ---
    import inspect
    src = inspect.getsource(R.llm_draft)
    chk("or <link>" in src, "rule 1 names <link> as a real source")
    chk("link" in inspect.signature(R.llm_draft).parameters, "llm_draft takes link=")

    # --- the JUDGE must see the link too, else it scores fetched facts as invented ---
    chk("link" in inspect.signature(G.build_judge_prompt).parameters, "judge takes link=")
    jp = G.build_judge_prompt("t", "d", "v", link="the link says — Foo. Bar baz.")
    chk("<link>" in jp and "Bar baz" in jp, "judge prompt carries the link")
    chk("<link>" not in G.build_judge_prompt("t", "d", "v"), "no link -> no <link> block")

    # --- cache ---
    R._LINK_CACHE["https://x.test/a"] = "cached!"
    chk(R.link_context("see https://x.test/a") == "cached!", "cache is used (no refetch)")

    print(f"LINK UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
