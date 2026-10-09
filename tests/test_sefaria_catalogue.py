"""Chronology and version selection must not turn ancient or modern texts into Renaissance texts."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sefaria_catalogue as sc


class SefariaCatalogueTests(unittest.TestCase):
    def test_composition_dates_take_precedence_over_publication(self):
        self.assertEqual(sc.composition_scope({"compDate": [-400, -200], "pubDate": [1488]})[0], "outside")
        self.assertEqual(sc.composition_scope({"compDate": [1563], "pubDate": [1893]}), ("included", [1563]))
        self.assertEqual(sc.composition_scope({"pubDate": [1500]})[0], "undated")

    def test_ambiguous_dates_require_review_and_boundaries_are_inclusive(self):
        for dates in ([1450], [1700], [1450, 1700]):
            self.assertEqual(sc.composition_scope({"compDate": dates})[0], "included")
        for dates in ([1440, 1460], [1690, 1710]):
            self.assertEqual(sc.composition_scope({"compDate": dates})[0], "boundary-review")
        self.assertEqual(sc.composition_scope({"compDate": "1563"})[0], "invalid-date")

    def test_count_excludes_markup_metadata_and_modern_footnotes(self):
        record = {"title": "A title that is not text", "text": {"Section": [
            "<b>אחד</b> שני <sup class='footnote-marker'>1</sup><i class='footnote'>modern editorial note</i>",
            ["שלישי<br>רביעי", "<script>ignore script</script> חמישי"],
        ]}}
        self.assertEqual(sc.count_version(record), 5)

    def test_source_versions_are_counted_without_generated_merged_copies(self):
        book = {"language": "Hebrew", "versionTitle": "An individual edition"}
        self.assertTrue(sc.source_version(book, {"isSource": True}))
        self.assertFalse(sc.source_version(dict(book, versionTitle="merged"), {"isSource": True}))
        self.assertFalse(sc.source_version(dict(book, language="English"), {"isSource": True}))
        self.assertFalse(sc.source_version(book, {"isSource": False, "isPrimary": True}))

    def test_toc_uses_work_titles_once_and_skips_topic_collections(self):
        toc = [{"category": "Halakhah", "contents": [{"title": "A"}, {"title": "A"},
                                                     {"title": "A collection", "isCollection": True}]}]
        self.assertEqual(sc.titles_in_toc(toc), {"A"})

    def test_source_census_preserves_the_frozen_corpus_contribution(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sefaria.json"
            corpus = {"snapshot": "v2026.06", "words": 100, "texts": 1}
            path.write_text(json.dumps({"corpus_statistics": corpus, "words": 100, "texts": 1}))
            audit = {"scope": [1450, 1700], "texts": 2, "words": 200, "works": 1,
                     "retrieved": "2026-10-09", "export_generated": "2026-10-02T00:00:00Z",
                     "versions": [{"title": "A", "status": "counted", "words": 200}],
                     "indexes": [{"title": "A", "compDate": [1550, 1560]}]}
            sc.update_entry(path, audit)
            entry = json.loads(path.read_text())
            self.assertEqual(entry["corpus_statistics"], corpus)
            self.assertEqual((entry["words"], entry["texts"], entry["period"]), (200, 2, "1550-1560"))
            from build_site import derive_entry
            self.assertEqual(derive_entry("sefaria", entry)["figures"], "other")
