"""Build the Renascor Corpus snapshot v2026.10 = frozen v2026.06 + the October 2026 catalogue harvest.

The frozen database is copied, never modified. Harvested texts are ingested with RQ's own ingest_texts
(same word counter, language normaliser, 1450-1700 window and junk filter). Duplicates follow the RQ
policy: exact normalised-text duplicates, and near-duplicates of the same upstream files (the same
resource, or a corpus collection that took its texts from that resource), get is_dup=1.

    python3 build_snapshot.py dedup_final.json OUT.sqlite
"""
import glob
import json
import os
import shutil
import sys

import os as _os
RQ = _os.environ.get("RQ_ROOT", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "RQ"))
sys.path.insert(0, RQ + "/scripts/overnight")
from ingest_lib import ingest_texts  # noqa: E402

FROZEN = RQ + "/data/backups/corpus_master.2026-06-26.FROZEN.sqlite"
HARVEST = RQ + "/data/raw/renascor_2026-10"
# Corpus collections that hold the same upstream files as a harvested resource.
SAME_SOURCE = {
    "textgrid-repository": ("RQ:TextGrid_German",),
    "openedges": ("RQ:OpenEDGeS",),
    "poeti-d-italia-in-lingua-latina": ("RQ:CorpusCorp",),
}


def is_policy_dup(rid, d):
    a = d["against"]
    return (d["kind"] == "exact" or a.split("/")[0] == rid
            or any(a.startswith(p) for p in SAME_SOURCE.get(rid, ())))


def main(dedup_path, out):
    if os.path.exists(out):
        raise SystemExit(f"{out} exists")
    dedup = json.load(open(dedup_path))
    shutil.copyfile(FROZEN, out)
    summary = {}
    for p in sorted(glob.glob(HARVEST + "/*/staging.jsonl")):
        rid = os.path.basename(os.path.dirname(p))
        dups = {d["filename"] for d in dedup.get(rid, {}).get("dups", []) if is_policy_dup(rid, d)}
        recs = []
        for line in open(p, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            r["collection"] = f"Renascor_{rid}"
            r["is_dup"] = 1 if r["filename"] in dups else 0
            r.setdefault("era", "renaissance")
            recs.append(r)
        rep = ingest_texts(recs, out, rebuild_viz=False)
        summary[rid] = {"inserted": rep["inserted_rows"], "in_core": rep["in_core_added"],
                        "in_core_words": rep["in_core_words_added"], "junk": len(rep["skipped_junk"]),
                        "skipped_dup": len(rep["skipped_dup"]), "policy_dups": len(dups)}
        print(rid, summary[rid], flush=True)
    json.dump(summary, open(out + ".ingest.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
