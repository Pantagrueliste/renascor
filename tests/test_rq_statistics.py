"""Resource counts must survive corpus deduplication without changing its snapshot."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import rq_import
import rq_statistics as rs


class ResourceStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "frozen.sqlite"
        con = sqlite3.connect(self.db)
        con.execute("CREATE TABLE texts (collection, filename, lang_display, year, wordcount, "
                    "in_core, is_dup, fmt_detected, origin, work_dup_level)")
        con.executemany("INSERT INTO texts VALUES (?,?,?,?,?,?,?,?,?,?)", [
            ("Example", "kept", "Latin", 1500, 100, 1, 0, "plain", "source", 0),
            ("Example", "duplicate", "Latin", 1550, 200, 1, 1, "plain", "source", 0),
            ("Example", "witness", "French", 1600, 50, 1, 0, "plain", "source", 1),
            ("Example", "outside", "Latin", 1800, 999, 0, 0, "plain", "source", 0),
        ])
        con.commit()
        con.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_duplicate_rows_count_for_resource_but_not_corpus(self):
        digest = rs.checksum(self.db)
        counts, seen = rs.read_database(self.db)
        aggregate = rs.aggregate_collections(counts, ["Example"])
        self.assertEqual((aggregate["texts"], aggregate["words"]), (3, 350))
        self.assertEqual((aggregate["corpus_texts"], aggregate["corpus_words"]), (2, 150))
        self.assertEqual(aggregate["period"], (1500, 1600))
        self.assertIn("outside", seen["Example"])
        imported = rq_import.aggregate(self.db, ["Example"])
        self.assertEqual((imported["texts"], imported["words"]), (3, 350))
        self.assertEqual(rs.checksum(self.db), digest)

    def test_rq_refresh_preserves_a_newer_source_census(self):
        counts, _ = rs.read_database(self.db)
        folder = self.root / "entries"
        folder.mkdir()
        path = folder / "example.json"
        entry = {"title": "A newer source census", "words": 1000, "texts": 5,
                 "period": "1450-1700", "count_basis": "sefaria-source-versions",
                 "corpus_statistics": {"snapshot": "v2026.06", "words": 150, "texts": 2},
                 "resource_statistics": {"url": "https://example.org/audit", "date": "2026-10-09", "note": "A full census"},
                 "notes": rq_import.STATS_NOTE, "license": "Not stated"}
        path.write_text(json.dumps(entry))
        families = {"groups": [{"slug": "example", "match": ["^Example$"]}]}
        rs.refresh_entries(folder, counts, families, {})
        self.assertEqual(json.loads(path.read_text()), entry)
        rq_import.set_statistics(entry, rs.aggregate_collections(counts, ["Example"]))
        self.assertEqual((entry["words"], entry["texts"], entry["period"]), (1000, 5, "1450-1700"))

    def test_staging_restores_short_texts_without_recounting_saved_ids(self):
        counts, seen = rs.read_database(self.db)
        raw = self.root / "data/Example.jsonl"
        raw.parent.mkdir()
        records = [
            {"filename": "kept", "year": 1500, "raw": "Already counted"},
            {"filename": "short", "year": 1450, "raw": "A short motto"},
            {"filename": "short", "year": 1450, "raw": "Saved mirror of the same ID"},
            {"filename": "late", "year": 1701, "raw": "An out of scope text"},
            {"filename": "empty", "year": 1500, "raw": ""},
        ]
        raw.write_text("".join(json.dumps(r) + "\n" for r in records))
        rebuild = self.root / "rebuild"
        rebuild.mkdir()
        lock = rebuild / "lock.tsv"
        lock.write_text("path\tsha256\tstatus\n" +
                        f"data/Example.jsonl\t{rs.checksum(raw)}\tok\n")
        manifest = {"stages": [{"command": ["python", "scripts/ingest_from_staging.py",
                    "--collection", "Example", "--staging", "data/Example.jsonl"],
                    "retrieval": {"checksum": "rebuild/lock.tsv"}}]}
        (rebuild / "rq_open_corpus_2026-06-12.json").write_text(json.dumps(manifest))
        extract = lambda text: {"words": len(text.split()), "alpha_ratio": 1.0}
        normalize = lambda language: ("lat", "Latin")
        audits = rs.recover_staging(counts, seen, self.root, extract, normalize)
        self.assertEqual(audits[0]["restored_texts"], 1)
        self.assertEqual((counts["Example"]["texts"], counts["Example"]["words"]), (4, 353))
        self.assertEqual(counts["Example"]["corpus_words"], 150)
        lock.write_text(lock.read_text().replace(rs.checksum(raw), "0" * 64))
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            rs.recover_staging(counts, seen, self.root, extract, normalize)

    def test_refresh_is_idempotent_and_preserves_editorial_metadata(self):
        counts, _ = rs.read_database(self.db)
        folder = self.root / "entries"
        folder.mkdir()
        path = folder / "example.json"
        entry = {"title": "An edited corpus", "words": 150, "texts": 2,
                 "encoding": "html", "url": "https://example.org",
                 "notes": rq_import.STATS_NOTE}
        path.write_text(json.dumps(entry))
        families = {"groups": [{"slug": "example", "match": ["^Example$"]}]}
        result = rs.refresh_entries(folder, counts, families, {})
        self.assertEqual(result["counts_refreshed"], 1)
        updated = json.loads(path.read_text())
        self.assertEqual(updated["words"], 350)
        self.assertEqual(updated["corpus_statistics"]["words"], 150)
        self.assertEqual(updated["encoding"], "html")
        before = path.read_bytes()
        self.assertEqual(rs.refresh_entries(folder, counts, families, {})["changed"], 0)
        self.assertEqual(path.read_bytes(), before)

    def test_mismatched_snapshot_is_rejected_before_writes(self):
        counts, _ = rs.read_database(self.db)
        folder = self.root / "entries"
        folder.mkdir()
        entry = {"words": 999, "texts": 2, "notes": rq_import.STATS_NOTE}
        path = folder / "example.json"
        path.write_text(json.dumps(entry))
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "exact snapshot"):
            rs.refresh_entries(folder, counts, {"groups": []}, {})
        self.assertEqual(path.read_bytes(), before)

    def test_entry_fields_are_included_in_public_exports(self):
        spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        fields = build.export_fields(build.load_schema())
        for field in ("corpus_statistics", "count_basis", "license", "license_url",
                      "license_note", "data_formats", "api_url"):
            self.assertIn(field, fields)


if __name__ == "__main__":
    unittest.main()
