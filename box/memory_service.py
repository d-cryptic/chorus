#!/usr/bin/env python3
"""Chorus memory service — a tiny Supermemory-API-compatible store (self-hosted).

Summary: Implements the /v3/documents surface Chorus writes to (POST store, GET list,
DELETE by containerTags) plus a keyword /v3/search, backed by SQLite. Stdlib only (no
deps, no docker), binds 127.0.0.1 so it is never exposed. Drop-in for upstream
github.com/supermemoryai/supermemory: point SUPERMEMORY_BASE_URL at whichever you run.
SUGGEST-ONLY project: this only stores/reads the user's own memory, never posts anywhere.

Env: MEMORY_DB (default /opt/chorus/memory.db), MEMORY_PORT (8000),
     MEMORY_TOKEN (optional bearer; empty = open on localhost).
"""
from __future__ import annotations
import os, json, sqlite3, time, hashlib
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DB = os.environ.get("MEMORY_DB", "/opt/chorus/memory.db")
PORT = int(os.environ.get("MEMORY_PORT", "8000"))
TOKEN = os.environ.get("MEMORY_TOKEN", "")


def _db() -> sqlite3.Connection:
    c = sqlite3.connect(DB, timeout=10)
    c.execute("""CREATE TABLE IF NOT EXISTS documents(
        id TEXT PRIMARY KEY, content TEXT NOT NULL, tags TEXT NOT NULL,
        metadata TEXT, created_at INTEGER NOT NULL)""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_docs_created ON documents(created_at)")
    return c


def _has_tags(row_tags: str, want: list[str]) -> bool:
    rt = set(json.loads(row_tags or "[]"))
    return all(w in rt for w in want)


class Handler(BaseHTTPRequestHandler):
    def _auth(self) -> bool:
        return not TOKEN or self.headers.get("authorization", "") == f"Bearer {TOKEN}"

    def _send(self, code: int, obj: dict) -> None:
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _tags(self) -> list[str]:
        q = parse_qs(urlparse(self.path).query)
        out: list[str] = []
        for raw in q.get("containerTags", []):
            out += [x for x in raw.split(",") if x]
        return out

    def _body(self) -> dict:
        ln = int(self.headers.get("content-length", "0") or 0)
        return json.loads(self.rfile.read(ln) or "{}") if ln else {}

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            return self._send(200, {"status": "ok", "service": "chorus-memory"})
        if not self._auth():
            return self._send(401, {"error": "unauthorized"})
        if path == "/v3/documents":
            want = self._tags()
            with closing(_db()) as c:   # never leak an fd on a locked/failed db
                rows = c.execute("SELECT id,content,tags,metadata,created_at FROM documents "
                                 "ORDER BY created_at DESC").fetchall()
            # Filter FIRST, cap AFTER. Capping first meant a tag-scoped list could return
            # nothing once the table grew past the cap, even with matching rows present.
            docs = [{"id": r[0], "content": r[1], "containerTags": json.loads(r[2]),
                     "metadata": json.loads(r[3] or "{}"), "createdAt": r[4]}
                    for r in rows if not want or _has_tags(r[2], want)][:1000]
            return self._send(200, {"documents": docs, "count": len(docs)})
        return self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._auth():
            return self._send(401, {"error": "unauthorized"})
        path = urlparse(self.path).path
        body = self._body()
        if path == "/v3/documents":
            content = (body.get("content") or "").strip()
            if not content:
                return self._send(400, {"error": "content required"})
            tags = body.get("containerTags") or []
            meta = body.get("metadata") or {}
            did = body.get("id") or hashlib.sha256(
                (content + json.dumps(tags, sort_keys=True)).encode()).hexdigest()[:24]
            with closing(_db()) as c:
                c.execute("INSERT OR REPLACE INTO documents(id,content,tags,metadata,created_at) "
                          "VALUES(?,?,?,?,?)",
                          (did, content, json.dumps(tags), json.dumps(meta), int(time.time() * 1000)))
                c.commit()
            return self._send(200, {"id": did, "status": "stored"})
        if path == "/v3/search":
            q = (body.get("q") or body.get("query") or "").lower()
            want = body.get("containerTags") or []
            with closing(_db()) as c:
                rows = c.execute("SELECT id,content,tags,metadata,created_at FROM documents "
                                 "ORDER BY created_at DESC").fetchall()
            res = [{"id": r[0], "content": r[1], "containerTags": json.loads(r[2]),
                    "metadata": json.loads(r[3] or "{}"), "createdAt": r[4]}
                   for r in rows
                   if (not want or _has_tags(r[2], want)) and (not q or q in r[1].lower())][:50]
            return self._send(200, {"results": res, "count": len(res)})
        return self._send(404, {"error": "not found"})

    def do_DELETE(self) -> None:
        if not self._auth():
            return self._send(401, {"error": "unauthorized"})
        if urlparse(self.path).path == "/v3/documents":
            want = self._tags()
            if not want:
                return self._send(400, {"error": "containerTags required for delete"})
            with closing(_db()) as c:
                ids = [r[0] for r in c.execute("SELECT id,tags FROM documents").fetchall()
                       if _has_tags(r[1], want)]
                for i in ids:
                    c.execute("DELETE FROM documents WHERE id=?", (i,))
                c.commit()
            return self._send(200, {"deleted": len(ids)})
        return self._send(404, {"error": "not found"})

    def log_message(self, *a) -> None:  # quiet
        pass


def main() -> None:
    print(f"chorus-memory on 127.0.0.1:{PORT} db={DB} auth={'on' if TOKEN else 'off'}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
