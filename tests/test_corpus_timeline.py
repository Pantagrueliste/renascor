"""Chronological words must conserve the frozen deduplicated counts."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts import build_site as bs, corpus_timeline as ct


class CorpusTimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "frozen.sqlite"
        con = sqlite3.connect(self.db)
        con.execute("CREATE TABLE texts (collection, year, wordcount, date_confidence, in_core, is_dup, filename, origin)")
        con.executemany("INSERT INTO texts (collection, year, wordcount, date_confidence, in_core, is_dup) VALUES (?,?,?,?,?,?)", [
            ("A", 1450, 10, "exact", 1, 0), ("A", 1459, 20, "exact", 1, 0),
            ("A", 1460, 30, "inferred", 1, 0), ("A", 1700, 40, "exact", 1, 0),
            ("A", None, 50, "collection", 1, 0), ("A", 1500, 900, "exact", 1, 1),
            ("A", 1800, 999, "exact", 0, 0), ("B", 1500, 25, "exact", 1, 0),
            ("Unlisted", 1510, 5, "exact", 1, 0), ("Zero", 1500, 15, "exact", 1, 1),
        ])
        con.commit()
        con.close()
        self.corpus = {"snapshot": "v2026.06", "scope": ct.SCOPE,
            "database_sha256": ct.checksum(self.db), "collections": {
                "A": {"corpus_words": 150, "corpus_texts": 5},
                "B": {"corpus_words": 25, "corpus_texts": 1},
                "Unlisted": {"corpus_words": 5, "corpus_texts": 1},
                "Zero": {"corpus_words": 0, "corpus_texts": 0}}}
        self.families = {"exclude": {"Unlisted": "internal bucket"}, "groups": [
            {"slug": "example", "match": ["^[AB]$"], "merge_stats": False}]}

    def tearDown(self):
        self.temp.cleanup()

    def audit(self):
        audit = ct.make_audit(self.db, self.corpus, self.families)
        audit["families_sha256"] = hashlib.sha256(
            (bs.REPO_ROOT / "scripts/rq_families.json").read_bytes()).hexdigest()
        (self.root / "rq_statistics.json").write_text(json.dumps(self.corpus))
        path = self.root / "period_word_counts.json"
        path.write_text(json.dumps(audit))
        return audit, path

    def build_counts(self, path):
        derived = [{"id": "example", "period": bs.parse_period("1570")},
                   {"id": "new-resource"}, {"id": "zero"}]
        corpus = {**self.corpus, "frozen": "2026-06-26"}
        return bs.load_period_words(path, corpus, derived), derived

    def test_year_boundaries_duplicates_undated_and_database_unchanged(self):
        before = ct.checksum(self.db)
        audit, _ = self.audit()
        a = audit["collections"]["A"]
        self.assertEqual((a["decade_words"][0], a["decade_words"][1], a["decade_words"][-1]), (30, 30, 40))
        self.assertEqual(a["decade_words"][5], 0)  # duplicate excluded
        self.assertEqual(a["undated_words"], 50)
        self.assertEqual(sum(a["decade_words"]) + a["undated_words"], 150)
        self.assertEqual(audit["date_confidence"]["inferred"]["words"], 30)
        self.assertEqual(ct.checksum(self.db), before)

    def test_grouping_source_census_unlisted_words_and_missing_data(self):
        _, path = self.audit()
        timeline, derived = self.build_counts(path)
        self.assertEqual(sum(timeline["decade_words"]), 125)
        self.assertEqual(timeline["undated_words"], 50)
        self.assertEqual(timeline["unlisted_words"], 5)
        self.assertEqual(sum(derived[0]["period_words"]["decades"]), 125)
        self.assertIsNone(derived[1]["period_words"])
        self.assertEqual(sum(derived[2]["period_words"]["decades"]), 0)
        path.unlink()
        timeline, derived = self.build_counts(path)
        self.assertIsNone(timeline)
        self.assertTrue(all(d["period_words"] is None for d in derived))

    def test_wrong_database_and_inconsistent_counts_are_rejected(self):
        self.corpus["database_sha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "exact database"):
            ct.make_audit(self.db, self.corpus, self.families)
        self.corpus["database_sha256"] = ct.checksum(self.db)
        audit, path = self.audit()
        audit["collections"]["A"]["decade_words"][0] += 1
        path.write_text(json.dumps(audit))
        with self.assertRaisesRegex(bs.BuildError, "disagree"):
            self.build_counts(path)

    def test_retained_out_of_scope_year_is_rejected(self):
        con = sqlite3.connect(self.db)
        con.execute("UPDATE texts SET year = 1701 WHERE year = 1700")
        con.commit()
        con.close()
        with self.assertRaisesRegex(ValueError, "outside 1450–1700"):
            ct.count_years(self.db)

    def test_range_allocation_conserves_words_and_includes_1700(self):
        self.assertEqual(ct.allocate_range(251, 1450, 1700), [10] * 24 + [11])
        bins = ct.allocate_range(410, 1540, 1580)
        self.assertEqual(bins[9:14], [100, 100, 100, 100, 10])
        self.assertEqual(sum(bins), 410)
        self.assertEqual(sum(ct.allocate_range(1, 1540, 1580)), 1)
        with self.assertRaises(ValueError):
            ct.allocate_range(100, 1690, 1710)

    def test_estimates_require_a_consistent_complete_in_scope_lifespan(self):
        origin = 'Project Gutenberg #42 — Example, Author, 1540-1580 — Work'
        result = ct.lifespan_estimate('GutenbergFR', 'pg42.txt', origin, 'author_death_1580')
        self.assertEqual((result['status'], result['range']), ('estimated', [1540, 1580]))
        for value, basis in [(origin.replace('1540', '1440'), 'author_death_1580'),
                             (origin.replace('1540-', '-'), 'author_death_1580'),
                             (origin, 'author_death_1590')]:
            self.assertEqual(ct.lifespan_estimate('GutenbergFR', 'pg42.txt', value, basis)['status'], 'review')
        self.assertIsNone(ct.lifespan_estimate('Other', 'work-2020.txt', origin, 'collection'))

    def test_estimates_are_separate_and_do_not_change_recorded_years_or_corpus_counts(self):
        con = sqlite3.connect(self.db)
        origin = 'Project Gutenberg #42 — Example, Author, 1540-1580 — Work'
        con.executemany('INSERT INTO texts VALUES (?,?,?,?,?,?,?,?)', [
            ('GutenbergFR', None, 410, 'author_death_1580', 1, 0, 'pg42.txt', origin),
            ('GutenbergFR', 1570, 100, 'author_death_1580', 1, 0, 'pg43.txt', origin),
            ('GutenbergFR', None, 900, 'author_death_1580', 1, 1, 'pg44.txt', origin),
        ])
        con.commit(); con.close()
        self.corpus['database_sha256'] = ct.checksum(self.db)
        self.corpus['collections']['GutenbergFR'] = {'corpus_words': 510, 'corpus_texts': 2}
        self.families['groups'][0]['match'].append('^GutenbergFR$')
        audit, path = self.audit()
        c = audit['collections']['GutenbergFR']
        self.assertEqual(sum(c['estimated_decade_words']), 410)
        self.assertEqual(sum(c['decade_words']), 100)
        self.assertEqual(c['undated_words'], 0)
        self.assertEqual(len(c['date_estimates']), 1)
        timeline, derived = self.build_counts(path)
        self.assertEqual(timeline['estimated_words'], 410)
        self.assertEqual(sum(timeline['decade_words']), 635)
        self.assertTrue(derived[0]['period']['approx'])
        self.assertEqual(derived[0]['period']['raw'], '1570')
        self.assertEqual(derived[0]['period']['label'], 'c.\u00a01540–1580')
        self.assertIn('author-lifespan', derived[0]['period']['estimate_note'])
        self.assertEqual(derived[0]['period_words']['estimated_range'], [1540, 1580])
        # The audit cannot silently change an estimated allocation's total.
        audit['collections']['GutenbergFR']['date_estimates'][0]['words'] += 1
        path.write_text(json.dumps(audit))
        with self.assertRaisesRegex(bs.BuildError, 'allocated words'):
            self.build_counts(path)


if __name__ == "__main__":
    unittest.main()
