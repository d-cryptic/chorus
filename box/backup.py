#!/usr/bin/env python3
"""Nightly backup: export D1 (queue store) locally + optionally to R2. Run daily.
Requires wrangler + the chorus D1. Keeps 14 days. Env: R2 handled by wrangler config."""
import os, subprocess, datetime, glob, sys
OUT = os.environ.get("CHORUS_BACKUP_DIR", "/var/backups/chorus"); os.makedirs(OUT, exist_ok=True)
day = datetime.date.today().isoformat(); f = f"{OUT}/chorus-{day}.sql"
try:
    subprocess.run(["npx", "wrangler", "d1", "export", "chorus", "--remote", "--output", f],
                   cwd=os.environ.get("CHORUS_DASHBOARD_DIR", "."), check=True)
    print("exported", f)
    for old in sorted(glob.glob(f"{OUT}/chorus-*.sql"))[:-14]:
        os.remove(old); print("pruned", old)
except Exception as e:
    print("backup failed:", repr(e)[:80]); sys.exit(1)
