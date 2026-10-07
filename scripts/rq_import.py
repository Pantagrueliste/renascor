#!/usr/bin/env python3
"""Import RQ Open Corpus collections into Renascor entries.

Reads the frozen RQ corpus metadata database (SQLite), groups its
collections into canonical edition projects via scripts/rq_families.json
(one entry per documented project, all languages merged), and writes one
JSON entry per canonical project into data/entries/.

Collections that match no documented project (micro-collections from the
retired RQ corpus assembly, platforms without a distinct project site,
unidentifiable origins) are NOT imported. They are listed, with their
statistics, in a pending report for later discovery and review.

Usage:
    python scripts/rq_import.py --db sqlite.db [--families FILE]
                                [--out-dir DIR] [--report FILE]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FAMILIES_PATH = REPO_ROOT / "scripts" / "rq_families.json"

STATS_NOTE = (
    "Corpus statistics (text, word and language counts, period) derived "
    "from the RQ Open Corpus snapshot v2026.06 (in-core, deduplicated texts)."
)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def canonical_for(collection: str, groups: list[dict]) -> dict | None:
    for g in groups:
        for pattern in g.get("match", []):
            if re.search(pattern, collection):
                return g
    return None


def aggregate(db_path: Path, collections: list[str]) -> dict:
    """Aggregate in-core, deduplicated texts over a set of RQ collections."""
    con = sqlite3.connect(db_path)
    placeholders = ",".join("?" * len(collections))
    rows = con.execute(
        f"SELECT lang_display, year, wordcount, fmt_detected, origin FROM texts "
        f"WHERE in_core=1 AND is_dup=0 AND collection IN ({placeholders})",
        collections,
    ).fetchall()
    con.close()
    langs, fmts, origins, years, words = set(), set(), [], [], 0
    for lang, year, wordcount, fmt, origin in rows:
        if lang:
            langs.add(lang)
        if year:
            years.append(int(year))
        if isinstance(wordcount, int):
            words += wordcount
        if fmt:
            fmts.add(fmt)
        if origin:
            origins.append(origin)
    return {"langs": langs, "fmts": fmts, "origins": origins,
            "period": (min(years), max(years)) if years else None,
            "words": words, "texts": len(rows)}


def build_entry(group: dict, stats: dict, existing: dict | None, today: str) -> dict:
    entry = dict(existing) if existing else {}
    if not existing:
        entry["title"] = group["title"]
        entry["url"] = group["url"]
        entry["status"] = "active"
        entry["provenance"] = "submitted"
        entry["date_added"] = today
        if group.get("institution"):
            entry["institution"] = group["institution"]
        if group.get("notes"):
            entry["notes"] = group["notes"]
        if group.get("status"):
            entry["status"] = group["status"]
    entry["languages"] = sorted(
        set(entry.get("languages") or []) | {code for code in stats["langs"] if code}
    )
    entry["encoding"] = "tei" if "tei" in stats["fmts"] else entry.get("encoding", "other")
    if stats["words"]:
        entry["words"] = stats["words"]
    entry["texts"] = stats["texts"]
    if stats["period"]:
        lo, hi = stats["period"]
        entry["period"] = f"{lo}-{hi}"
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--families", type=Path, default=FAMILIES_PATH)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "data" / "entries")
    parser.add_argument("--report", type=Path,
                        default=REPO_ROOT / "data" / "rq_pending.csv")
    args = parser.parse_args()
    today = date.today().isoformat()

    groups = json.loads(args.families.read_text(encoding="utf-8"))["groups"]
    con = sqlite3.connect(args.db)
    collections = [r[0] for r in con.execute(
        "SELECT DISTINCT collection FROM texts WHERE in_core=1 AND is_dup=0 ORDER BY collection"
    )]
    con.close()

    assigned: dict[str, list[str]] = {}
    pending: list[str] = []
    for c in collections:
        g = canonical_for(c, groups)
        if g:
            assigned.setdefault(g["slug"], []).append(c)
        else:
            pending.append(c)

    # Existing entries for update-in-place.
    written, updated, skipped = [], [], []
    for g in groups:
        slug = g.get("slug")
        members = assigned.get(slug)
        if not members:
            continue
        stats = aggregate(args.db, members)
        out_path = args.out_dir / f"{slug}.json"
        existing = None
        if out_path.exists():
            try:
                existing = json.loads(out_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = None
        if not g.get("url"):
            skipped.append(slug)
            continue
        entry = build_entry(g, stats, existing, today)
        out_path.write_text(
            json.dumps(entry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (written if not existing else updated).append(slug)

    with args.report.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["collection", "texts", "words", "languages", "period", "origin_sample"])
        con = sqlite3.connect(args.db)
        for c in pending:
            r = con.execute(
                "SELECT COUNT(*), COALESCE(SUM(wordcount),0), "
                "GROUP_CONCAT(DISTINCT lang_display), MIN(year), MAX(year), "
                "COALESCE(MIN(origin),'') FROM texts "
                "WHERE in_core=1 AND is_dup=0 AND collection=?", (c,)
            ).fetchone()
            period = f"{r[3]}-{r[4]}" if r[3] is not None else ""
            w.writerow([c, r[0], r[1], r[2], period, r[5][:120]])
        con.close()

    print(f"Mapped {sum(len(v) for v in assigned.values())} of {len(collections)} "
          f"collections into {len(written) + len(updated)} canonical projects "
          f"({len(updated)} updated, {len(written)} new, {len(skipped)} skipped without URL).")
    print(f"Pending (not imported): {len(pending)} collections -> {args.report}")
    for slug in written:
        print(f"  new:      {slug}")
    for slug in updated:
        print(f"  updated:  {slug}")
    for slug in skipped:
        print(f"  skipped (no URL): {slug}")
    return 0


if __name__ == "__main__":
    sys.exit(main())