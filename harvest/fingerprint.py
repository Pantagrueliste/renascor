"""Shingle fingerprints for near-duplicate detection between harvested texts and the frozen RQ corpus.

Text -> RQ primary text (extract_primary_text) -> normalised words (lowercase, no diacritics,
letters only, u/v and i/j merged) -> 5-word shingles -> crc32 -> keep hashes with h % MOD == 0.
Also an exact hash of the whole normalised word sequence.

    python3 fingerprint.py index-rq OUT.sqlite     # index the frozen corpus (resolvable texts)
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sqlite3
import sys
import unicodedata
import zlib
from multiprocessing import Pool

import os as _os
RQ = _os.environ.get("RQ_ROOT", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "RQ"))
sys.path.insert(0, RQ + "/src")
from rqfootprint.textstats import extract_primary_text  # noqa: E402

FROZEN = RQ + "/data/backups/corpus_master.2026-06-26.FROZEN.sqlite"
MOD = 32
K = 5
_NONLET = re.compile(r"[^a-z]+")


def words(raw: str) -> list[str]:
    text, _ = extract_primary_text(raw)
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.replace("v", "u").replace("j", "i").replace("ſ", "s")
    return [w for w in _NONLET.sub(" ", t).split() if w]


def fingerprint(raw: str) -> tuple[int, int, list[int]]:
    """(number of words, exact hash of the word sequence, sampled shingle hashes)."""
    ws = words(raw)
    exact = zlib.crc32(" ".join(ws).encode()) if ws else 0
    hs = set()
    for i in range(len(ws) - K + 1):
        h = zlib.crc32(" ".join(ws[i:i + K]).encode())
        if h % MOD == 0:
            hs.add(h)
    return len(ws), exact, sorted(hs)


def _key(f: str) -> str:
    return os.path.basename(f or "").split(".")[0].lower()


def _work(task):
    doc, coll, fn, src = task
    try:
        if src[0] == "file":
            raw = open(src[1], encoding="utf-8", errors="replace").read()
        else:
            raw = src[1]
        n, ex, hs = fingerprint(raw)
        return doc, coll, fn, src[0] == "file" and src[1] or "stage", n, ex, hs
    except Exception as e:  # noqa: BLE001
        return doc, coll, fn, f"error {e}", 0, 0, []


def tasks():
    con = sqlite3.connect(f"file:{FROZEN}?mode=ro", uri=True)
    rows = con.execute("SELECT collection, filename, path FROM texts WHERE in_core=1 AND is_dup=0").fetchall()
    want = {(c, f) for c, f, _ in rows}
    wantf = collections.defaultdict(set)
    for c, f, _ in rows:
        wantf[f].add(c)
    done = set()
    # staging records first (exact (collection, filename) or filename match)
    for p in glob.glob(RQ + "/data/raw/**/*.jsonl", recursive=True):
        if "renascor_2026-10" in p:
            continue
        for line in open(p, encoding="utf-8", errors="replace"):
            try:
                r = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(r, dict) or "filename" not in r or not r.get("raw"):
                continue
            fn = r["filename"]
            cs = [r.get("collection")] if (r.get("collection"), fn) in want else sorted(wantf.get(fn, ()))
            for c in cs:
                if (c, fn) not in done:
                    done.add((c, fn))
                    yield (c, fn, ("stage", r["raw"]))
    files = collections.defaultdict(list)
    for root, _, fs in os.walk(RQ + "/data/raw"):
        if "renascor_2026-10" in root:
            continue
        for f in fs:
            if not f.endswith((".jpg", ".gif", ".png", ".pdf", ".zip", ".gz", ".jsonl", ".tsv")):
                files[_key(f)].append(os.path.join(root, f))
    for c, f, p in rows:
        if (c, f) in done:
            continue
        cands = files.get(_key(f)) or files.get(_key(p)) or []
        # prefer the candidate whose path ends like the recorded path
        best = [x for x in cands if p and x.endswith(p)] or cands[:1]
        for x in best[:1]:
            done.add((c, f))
            yield (c, f, ("file", x))


def schema(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS docs(doc INTEGER PRIMARY KEY, side TEXT, collection TEXT, filename TEXT,
        src TEXT, nwords INTEGER, exact INTEGER, nsh INTEGER);
    CREATE TABLE IF NOT EXISTS sh(h INTEGER, doc INTEGER);
    """)


def index_rq(out):
    con = sqlite3.connect(out)
    schema(con)
    ts = [(i, c, f, s) for i, (c, f, s) in enumerate(tasks())]
    print("tasks", len(ts), flush=True)
    with Pool(8) as pool:
        for k, (doc, c, f, src, n, ex, hs) in enumerate(pool.imap_unordered(_work, ts, chunksize=16)):
            con.execute("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?)", (doc, "rq", c, f, src, n, ex, len(hs)))
            con.executemany("INSERT INTO sh VALUES (?,?)", [(h, doc) for h in hs])
            if k % 5000 == 0:
                con.commit()
                print(k, flush=True)
    con.commit()
    con.execute("CREATE INDEX IF NOT EXISTS sh_h ON sh(h)")
    con.execute("CREATE INDEX IF NOT EXISTS docs_exact ON docs(exact)")
    con.commit()
    print("done", con.execute("SELECT COUNT(*), SUM(nwords) FROM docs").fetchone())


if __name__ == "__main__":
    if sys.argv[1] == "index-rq":
        index_rq(sys.argv[2])


DIRS = {
    "OpenEDGeS": ["openedges"], "CKCC_Epistolarium": ["ckcc"], "NOSCEMUS": ["noscemus"],
    "LiberLiber": ["liberliber"], "CorpusCorp": ["corpuscorp"], "OSTA": ["osta"],
    "Estilometria_SigloOro": ["estilometria"], "SPXVI_Polish16c": ["spxvi"], "EMLAP": ["emlap"],
    "ReF_ENHG": ["ref", "ref_dl"], "DiBiLit_German": ["dibilit"], "IMPACTes_OriginalImprint": ["impactes"],
    "DTAE_16c": ["dtae", "dtae_dumps"], "CroALa": ["croala"],
}
TEXT_EXT = (".xml", ".txt", ".vrt", ".html", ".htm", ".tei", ".md")


def _work_file(task):
    doc, coll, path = task
    try:
        raw = open(path, encoding="utf-8", errors="replace").read()
        n, ex, hs = fingerprint(raw)
        return doc, coll, path, n, ex, hs
    except Exception as e:  # noqa: BLE001
        return doc, coll, f"error {e}", 0, 0, []


def index_dirs(out):
    con = sqlite3.connect(out)
    have = {r[0] for r in con.execute("SELECT src FROM docs")}
    start = con.execute("SELECT COALESCE(MAX(doc), 0) + 1 FROM docs").fetchone()[0]
    ts = []
    for coll, ds in DIRS.items():
        for d in ds:
            for root, _, fs in os.walk(f"{RQ}/data/raw/{d}"):
                for f in fs:
                    p = os.path.join(root, f)
                    if f.lower().endswith(TEXT_EXT) and p not in have and os.path.getsize(p) < 200_000_000:
                        ts.append((start + len(ts), coll, p))
    print("tasks", len(ts), flush=True)
    with Pool(8) as pool:
        for k, (doc, c, p, n, ex, hs) in enumerate(pool.imap_unordered(_work_file, ts, chunksize=8)):
            con.execute("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?)", (doc, "rq", c, os.path.basename(p), p, n, ex, len(hs)))
            con.executemany("INSERT INTO sh VALUES (?,?)", [(h, doc) for h in hs])
            if k % 5000 == 0:
                con.commit()
                print(k, flush=True)
    con.commit()
    print("done", con.execute("SELECT COUNT(*), SUM(nwords) FROM docs").fetchone())


if __name__ == "__main__" and sys.argv[1] == "index-dirs":
    index_dirs(sys.argv[2])
