"""Mark harvested texts that duplicate a frozen-corpus text or an earlier harvested text.

    python3 dedup.py rq_index.sqlite OUT.json

A harvested in-window text is a duplicate when its normalised word sequence equals another text's
(exact), or when at least THRESH of its sampled shingles occur in one single other text (near).
Different editions of the same work rarely pass this test; they stay counted, as in RQ's policy.
Resources are processed largest first, so within the harvest the larger resource keeps the text.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sqlite3
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fingerprint import fingerprint  # noqa: E402
from hlib import OUT, LO, HI, stats  # noqa: E402

THRESH = 0.8
MIN_SH = 5


def _fp(rec):
    st = stats(rec["raw"])
    n, ex, hs = fingerprint(rec["raw"])
    junk = st["words"] < 20 or st["alpha_ratio"] < 0.45  # RQ ingest_texts filter
    return rec["collection"], rec["filename"], st["words"], n, ex, hs, junk


def in_window(r):
    y = r.get("year")
    return (y is not None and LO <= y <= HI) or (y is None and r.get("dateless_in_window"))


def main(index, out):
    rq = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
    rq_exact = {}
    for doc, coll, ex in rq.execute("SELECT doc, collection, exact FROM docs WHERE nwords > 0"):
        rq_exact.setdefault(ex, coll)
    res = {}
    rejected = {r["id"] for r in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         "..", "data", "rejected.json")))["rejected"]}
    for d in sorted(glob.glob(str(OUT / "*" / "staging.jsonl"))):
        rid = os.path.basename(os.path.dirname(d))
        if rid in rejected:  # excluded from the catalogue after the harvest
            continue
        recs = [json.loads(l) for l in open(d, encoding="utf-8") if l.strip()]
        res[rid] = [r for r in recs if in_window(r)]
    order = sorted(res, key=lambda k: -sum(len(r["raw"]) for r in res[k]))
    new_exact: dict[int, str] = {}
    new_sh: dict[int, list[int]] = collections.defaultdict(list)
    new_docs: list[str] = []
    report = {}
    with Pool(8) as pool:
        for rid in order:
            fps = pool.map(_fp, res[rid], chunksize=8)
            dups, rep = [], {"texts": 0, "words": 0, "dup_texts": 0, "dup_words": 0, "against": collections.Counter()}
            for coll, fn, words, n, ex, hs, junk in fps:
                if junk:
                    rep["junk_texts"] = rep.get("junk_texts", 0) + 1
                    rep["junk_words"] = rep.get("junk_words", 0) + words
                    continue
                rep["texts"] += 1
                rep["words"] += words
                hit = None
                if n and ex in rq_exact:
                    hit = ("exact", "RQ:" + rq_exact[ex])
                elif n and ex in new_exact:
                    hit = ("exact", new_exact[ex])
                elif len(hs) >= MIN_SH:
                    cnt = collections.Counter()
                    for h in hs:
                        for (doc,) in rq.execute("SELECT doc FROM sh WHERE h=?", (h,)):
                            cnt[("rq", doc)] += 1
                        for j in new_sh.get(h, ()):
                            cnt[("new", j)] += 1
                    if cnt:
                        (side, doc), c = cnt.most_common(1)[0]
                        if c / len(hs) >= THRESH:
                            if side == "rq":
                                coll2 = rq.execute("SELECT collection FROM docs WHERE doc=?", (doc,)).fetchone()[0]
                                hit = ("near", "RQ:" + coll2)
                            else:
                                hit = ("near", new_docs[doc])
                if hit:
                    rep["dup_texts"] += 1
                    rep["dup_words"] += words
                    rep["against"][hit[1].split("/")[0]] += 1
                    dups.append({"filename": fn, "kind": hit[0], "against": hit[1], "words": words})
                else:
                    k = len(new_docs)
                    new_docs.append(f"{rid}/{fn}")
                    if n:
                        new_exact.setdefault(ex, f"{rid}/{fn}")
                    for h in hs:
                        new_sh[h].append(k)
            rep["against"] = dict(rep["against"])
            rep["unique_texts"] = rep["texts"] - rep["dup_texts"]
            rep["unique_words"] = rep["words"] - rep["dup_words"]
            rep["dups"] = dups
            report[rid] = rep
            print(rid, rep["texts"], rep["words"], "dup", rep["dup_texts"], rep["dup_words"], rep["against"], flush=True)
    json.dump(report, open(out, "w"), ensure_ascii=False, indent=1)
    T = sum(r["unique_texts"] for r in report.values())
    W = sum(r["unique_words"] for r in report.values())
    print("TOTAL unique", T, W)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
