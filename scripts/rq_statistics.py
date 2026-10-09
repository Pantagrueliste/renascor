#!/usr/bin/env python3
"""Refresh catalogue sizes without changing the frozen RQ corpus.

Count every retained in-core row, including is_dup=1. Optionally recover
additional texts from checksum-locked staging JSONL files. These remain
harvested-subset counts: texts excluded before staging cannot be reconstructed
from a metadata database. Keep the frozen, deduplicated counts separately.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "v2026.06"
SOURCE = "https://github.com/Pantagrueliste/rq-open-corpus/releases/tag/v2026.06-frozen"


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_database(db: Path) -> tuple[dict, dict]:
    stats, seen = {}, {}
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        for coll, fn, lang, year, words, in_core, is_dup in con.execute(
            "SELECT collection, filename, lang_display, year, wordcount, in_core, is_dup FROM texts"
        ):
            seen.setdefault(coll, set()).add(fn)
            if in_core != 1:
                continue
            s = stats.setdefault(coll, {"texts": 0, "words": 0, "corpus_texts": 0,
                                       "corpus_words": 0, "languages": set(), "years": set(),
                                       "restored_texts": 0, "restored_words": 0})
            s["texts"] += 1
            s["words"] += words or 0
            if is_dup == 0:
                s["corpus_texts"] += 1
                s["corpus_words"] += words or 0
            if lang:
                s["languages"].add(lang)
            if year:
                s["years"].add(int(year))
    finally:
        con.close()
    return stats, seen


def recover_staging(stats: dict, seen: dict, rq_root: Path, extract_text=None,
                    normalize_language=None) -> list[dict]:
    """Recover missing source IDs, never count a saved copy of an ID twice.

    Scope follows the stage's date rule. Unlike the training-corpus ingest,
    catalogue sizes include short nonempty texts (e.g. emblem mottos).
    Frozen row counts are used wherever that source ID is already present.
    """
    if extract_text is None or normalize_language is None:
        sys.path.insert(0, str(rq_root / "src"))
        from rqfootprint.corpus.langnorm import normalise
        from rqfootprint.textstats import stats as text_stats
        extract_text = extract_text or text_stats
        normalize_language = normalize_language or normalise

    manifest = json.loads((rq_root / "rebuild/rq_open_corpus_2026-06-12.json").read_text())
    audits = []
    for stage in manifest["stages"]:
        command = stage.get("command", [])
        if "scripts/ingest_from_staging.py" not in command:
            continue
        coll = command[command.index("--collection") + 1]
        if coll not in stats:
            continue
        rel = command[command.index("--staging") + 1]
        path = rq_root / rel
        lock_rel = stage.get("retrieval", {}).get("checksum")
        if not path.is_file() or not lock_rel or not (rq_root / lock_rel).is_file():
            continue
        with (rq_root / lock_rel).open() as fh:
            locks = list(csv.DictReader(fh, delimiter="\t"))
        locked = next((r for r in locks if r.get("path") == rel), None)
        if not locked or locked.get("status") != "ok":
            continue
        actual = checksum(path)
        if actual != locked["sha256"]:
            raise ValueError(f"Staging checksum mismatch: {rel}")
        audit = {"collection": coll, "path": rel, "sha256": actual,
                 "restored_texts": 0, "restored_words": 0}
        s = stats[coll]
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                record = json.loads(line)
                fn = record["filename"]
                if fn in seen[coll]:
                    continue
                seen[coll].add(fn)
                year = record.get("year")
                if year is not None:
                    if not 1450 <= int(year) <= 1700:
                        continue
                elif "--no-dateless-in-window" in command and not record.get("dateless_in_window"):
                    continue
                st = extract_text(record.get("raw") or "")
                if not st["words"] or st["alpha_ratio"] < 0.45:
                    continue
                s["texts"] += 1
                s["words"] += st["words"]
                s["restored_texts"] += 1
                s["restored_words"] += st["words"]
                s["languages"].add(normalize_language(record.get("language"))[1])
                if year:
                    s["years"].add(int(year))
                audit["restored_texts"] += 1
                audit["restored_words"] += st["words"]
        audits.append(audit)
    return audits


def project_collections(stats: dict, families: dict) -> dict:
    projects = {}
    for coll in sorted(stats):
        if coll in families.get("exclude", {}):
            continue
        group = next((g for g in families["groups"]
                      if any(re.search(p, coll) for p in g.get("match", []))), None)
        if group and (coll in group.get("drop", []) or group.get("merge_stats") is False):
            continue
        slug = group["slug"] if group else re.sub(r"[^a-z0-9]+", "-", coll.lower()).strip("-")
        projects.setdefault(slug, []).append(coll)
    return projects


def aggregate_collections(stats: dict, members: list[str]) -> dict:
    selected = [stats[c] for c in members]
    out = {k: sum(s[k] for s in selected) for k in
           ("words", "texts", "corpus_words", "corpus_texts", "restored_words", "restored_texts")}
    out["langs"] = set().union(*(set(s["languages"]) for s in selected))
    years = set().union(*(set(s["years"]) for s in selected))
    out["period"] = (min(years), max(years)) if years else None
    return out


def refresh_entries(entries_dir: Path, stats: dict, families: dict, licenses: dict) -> dict:
    projects = project_collections(stats, families)
    changed, refreshed, increased = 0, 0, 0
    updates = []
    for path in sorted(entries_dir.glob("*.json")):
        entry = json.loads(path.read_text())
        before = dict(entry)
        members = projects.get(path.stem)
        if members and (re.search(r"(?:Renascor Corpus|RQ Open Corpus) snapshot ", entry.get("notes", ""))
                        or entry.get("corpus_statistics")):
            s = aggregate_collections(stats, members)
            # Refuse to silently mix the June snapshot with a later recount.
            previous = entry.get("corpus_statistics", entry)
            if (previous.get("words"), previous.get("texts")) != (s["corpus_words"], s["corpus_texts"]):
                raise ValueError(f"{path.stem}: frozen counts do not match the catalogue; use its exact snapshot")
            # A newer source census takes precedence over the frozen harvested subset.
            if not entry.get("resource_statistics"):
                increased += s["words"] > s["corpus_words"] or s["texts"] > s["corpus_texts"]
                entry.update(words=s["words"], texts=s["texts"], languages=sorted(s["langs"]),
                             corpus_statistics={"snapshot": SNAPSHOT, "words": s["corpus_words"],
                                                "texts": s["corpus_texts"]},
                             count_basis=("rq-retained-rows-and-staging" if s["restored_texts"]
                                          else "rq-retained-rows"))
                if s["period"]:
                    entry["period"] = "{}-{}".format(*s["period"])
                entry["notes"] = re.sub(
                    r"(?:Renascor Corpus|RQ Open Corpus) snapshot v2026\.06 \([^)]*\)",
                    "Renascor Corpus snapshot v2026.06 (in-core, including retained duplicates; harvested subset)",
                    entry.get("notes", ""))
                refreshed += 1
        verified = licenses.get(path.stem)
        if verified:
            entry.update({k: v for k, v in verified.items() if k in
                          ("license", "license_url", "license_note")})
        else:
            entry.setdefault("license", "Not stated")
        if entry != before:
            updates.append((path, entry))
            changed += 1
    for path, entry in updates:
        path.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n")
    return {"changed": changed, "counts_refreshed": refreshed, "larger_resources": increased}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--rq-root", type=Path, help="Recover checksum-locked source staging from this RQ checkout")
    parser.add_argument("--families", type=Path, default=ROOT / "scripts/rq_families.json")
    parser.add_argument("--entries-dir", type=Path, default=ROOT / "data/entries")
    parser.add_argument("--out", type=Path, default=ROOT / "data/rq_statistics.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats, seen = read_database(args.db)
    audits = recover_staging(stats, seen, args.rq_root) if args.rq_root else []
    for s in stats.values():
        s["languages"] = sorted(s["languages"])
        s["years"] = sorted(s["years"])
    payload = {"snapshot": SNAPSHOT, "source": SOURCE, "database_sha256": checksum(args.db),
               "scope": [1450, 1700],
               "coverage": "Harvested subsets. Pre-harvest exclusions and unstaged pre-ingest exclusions remain unknown.",
               "collections": dict(sorted(stats.items())), "staging": audits}
    if not args.dry_run:
        families = json.loads(args.families.read_text())
        licenses = json.loads((ROOT / "scripts/rq_licenses_verified.json").read_text())["entries"]
        print(json.dumps(refresh_entries(args.entries_dir, stats, families, licenses)))
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"Recovered {sum(a['restored_texts'] for a in audits):,} texts / "
          f"{sum(a['restored_words'] for a in audits):,} words from {len(audits)} locked staging files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
