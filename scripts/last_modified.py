#!/usr/bin/env python3
"""Refresh the "last_modified" date of catalogue entries.

For each entry whose URL points at a GitHub repository, fetches the repo's
last push date (gh API); for Zenodo records, fetches the record's "updated"
date (Zenodo REST API). Writes the result as an optional last_modified field
(ISO date) on the entry. Other URL types are left untouched.

Usage:
    python scripts/last_modified.py [--entries-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.request
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

GH_RE = re.compile(r"https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")
ZENODO_RE = re.compile(r"https?://(?:www\.)?zenodo\.org/(?:api/)?records/(\d+)")
USER_AGENT = "Mozilla/5.0 (compatible; renascor-link-checker/1.0)"


def gh_pushed_at(repo: str) -> str | None:
    try:
        raw = subprocess.run(
            ["gh", "api", f"repos/{repo}"],
            capture_output=True, text=True, timeout=45, check=True,
        ).stdout
        return json.loads(raw).get("pushed_at", "")[:10] or None
    except Exception:
        return None


def zenodo_updated(record_id: str) -> str | None:
    req = urllib.request.Request(
        f"https://zenodo.org/api/records/{record_id}",
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()).get("updated", "")[:10] or None
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries-dir", type=Path, default=REPO_ROOT / "data" / "entries")
    args = parser.parse_args()

    today = date.today().isoformat()
    checked, written = 0, 0
    for path in sorted(args.entries_dir.glob("*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        url = entry.get("url") or ""
        repo = GH_RE.match(url)
        zen = ZENODO_RE.match(url)
        if repo:
            lm = gh_pushed_at(repo.group(1))
        elif zen:
            lm = zenodo_updated(zen.group(1))
        else:
            continue
        checked += 1
        if not lm:
            print(f"  no date: {path.name} ({url})")
            continue
        if entry.get("last_modified") != lm:
            entry["last_modified"] = lm
            path.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
            written += 1
            print(f"  {lm}  {path.name}")
    print(f"checked {checked} entries (GitHub/Zenodo), wrote {written}, as of {today}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())