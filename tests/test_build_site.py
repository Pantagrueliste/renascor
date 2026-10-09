"""Unit tests for scripts/build_site.py (standard library only; the build itself needs jsonschema).

Run: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_site", REPO / "scripts" / "build_site.py")
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)

NBSP = " "


def entry(**fields) -> dict:
    """A minimal valid entry."""
    base = {"title": "A Test Edition", "url": "https://example.org/edition/", "languages": ["Latin"],
            "encoding": "tei", "status": "active", "provenance": "submitted", "date_added": "2026-10-07"}
    base.update(fields)
    return base


class PeriodTests(unittest.TestCase):
    def check(self, raw, label, start, end, kind, note=None, beyond=False, approx=None):
        p = bs.parse_period(raw)
        self.assertEqual(p["label"], label)
        self.assertEqual((p["start"], p["end"]), (start, end))
        self.assertEqual(p["kind"], kind)
        self.assertEqual(p["note"], note)
        self.assertEqual(p["beyond_scope"], beyond)
        self.assertEqual(p["raw"], raw)
        if approx is not None:
            self.assertEqual(p["approx"], approx)

    def test_single_year_written_as_range(self):
        self.check("1620-1620", "1620", 1620, 1620, "year")

    def test_approximate_range_keeps_c_and_nbsp(self):
        self.check("c. 1539-1547", f"c.{NBSP}1539–1547", 1539, 1547, "range", approx=True)

    def test_trailing_note_is_not_part_of_the_label(self):
        self.check("1594–1636 (17th century)", "1594–1636", 1594, 1636, "range", note="17th century")

    def test_century_with_note_beyond_scope(self):
        self.check("15th century (Angelo Poliziano, 1454–1494)", "15th century", 1400, 1499, "century",
                   note="Angelo Poliziano, 1454–1494", beyond=True, approx=True)

    def test_century_range(self):
        self.check("16th–18th century (partial overlap with 1450–1700)", "16th–18th century",
                   1500, 1799, "century", note="partial overlap with 1450–1700", beyond=True)

    def test_period_in_words(self):
        p = bs.parse_period("early modern (believed 16th–18th century; uncertain)")
        self.assertEqual(p["kind"], "text")
        self.assertIsNone(p["start"])
        self.assertIsNone(p["end"])
        self.assertIsNone(p["note"])
        self.assertEqual(p["label"], "early modern (believed 16th–18th century; uncertain)")
        self.assertFalse(p["beyond_scope"])

    def test_wide_ranges_beyond_scope(self):
        self.check("800-1900", "800–1900", 800, 1900, "range", beyond=True)
        self.check("1400-1700", "1400–1700", 1400, 1700, "range", beyond=True)

    def test_reversed_range_and_missing(self):
        self.check("1700-1650", "1650–1700", 1650, 1700, "range")
        self.assertIsNone(bs.parse_period(None))
        self.assertIsNone(bs.parse_period("  "))

    def test_hyphens_between_digits_in_words_become_en_dashes(self):
        self.assertEqual(bs.parse_period("about 1500-1520 and later")["label"], "about 1500–1520 and later")


class NotesTests(unittest.TestCase):
    RQ = ("Corpus statistics (text, word and language counts, period) derived from the RQ Open Corpus "
          "snapshot v2026.06 (in-core, deduplicated texts).")

    def test_rq_sentence_and_reference_list_removed(self):
        notes = "Letters of a diplomat. " + self.RQ + " https://example.org; rebuild/x_2026.tsv; data/raw/X/x.jsonl"
        text, version = bs.split_notes(notes)
        self.assertEqual(text, "Letters of a diplomat.")
        self.assertEqual(version, "v2026.06")

    def test_only_rq_sentence_leaves_nothing(self):
        self.assertEqual(bs.split_notes(self.RQ + " https://abu.cnam.fr; rebuild/abu.tsv"), ("", "v2026.06"))

    def test_renamed_corpus_preserves_snapshot_and_hides_bookkeeping(self):
        note = "Letters. " + self.RQ.replace("RQ Open Corpus", "Renascor Corpus")
        self.assertEqual(bs.split_notes(note + " rebuild/a.tsv"), ("Letters.", "v2026.06"))
        self.assertEqual(bs.derive_entry("letters", entry(words=10, notes=note))["figures"], "rq")

    def test_discovery_tail_removed(self):
        notes = ("TEI files of a travel corpus.\n\nJustification: matches the catalogue scope. "
                 "Verify scope before cataloguing.\n\nFound at: https://example.org")
        self.assertEqual(bs.split_notes(notes), ("TEI files of a travel corpus.", None))
        self.assertEqual(bs.split_notes("Corpus.\n\nFound at: https://example.org")[0], "Corpus.")

    def test_link_check_codes_removed(self):
        text, _ = bs.split_notes("The repository Pantagrueliste/CavrianaCorr (live 200) is a digital TEI edition.")
        self.assertEqual(text, "The repository Pantagrueliste/CavrianaCorr is a digital TEI edition.")
        text, _ = bs.split_notes("GitHub repository ficino2021/bdpn (CC0, live 200) preserved the corpus.")
        self.assertEqual(text, "GitHub repository ficino2021/bdpn (CC0) preserved the corpus.")
        text, _ = bs.split_notes("Site live. Texts are in diplomatic TEI (e-ditiones/CORPUS17, live 200).")
        self.assertEqual(text, "Texts are in diplomatic TEI (e-ditiones/CORPUS17).")
        self.assertEqual(bs.split_notes("Data on Zenodo (200).")[0], "Data on Zenodo.")

    def test_origin_verbatim_both_forms(self):
        quoted = "Sermons in Bulgarian. Origin verbatim: 'Damaskini (pre-standard Balkan Slavic), 17th c.'. " + self.RQ
        self.assertEqual(bs.split_notes(quoted)[0], "Sermons in Bulgarian.")
        bare = "Correspondence edition. Origin verbatim: Cavriana correspondence (late 16th c)"
        self.assertEqual(bs.split_notes(bare)[0], "Correspondence edition.")

    def test_pipeline_parenthetical_removed(self):
        text, _ = bs.split_notes("A corpus of plays (RQ harvest path data/raw/Plays/plays.jsonl) in TEI.")
        self.assertEqual(text, "A corpus of plays in TEI.")

    def test_file_extensions_kept(self):
        notes = "Page images are .psd files; the site was renamed to ssrq-sds-fds.ch (the .sdsr URLs no longer resolve)."
        self.assertEqual(bs.split_notes(notes)[0], notes)

    def test_data_never_modified(self):
        e = entry(notes="Text (live 200). " + self.RQ)
        before = json.dumps(e, sort_keys=True)
        bs.derive_entry("x", e)
        self.assertEqual(json.dumps(e, sort_keys=True), before)

    def test_figures_classification(self):
        self.assertEqual(bs.derive_entry("a", entry(words=10, notes=self.RQ))["figures"], "rq")
        self.assertEqual(bs.derive_entry("b", entry(words=10))["figures"], "other")
        self.assertEqual(bs.derive_entry("c", entry(texts=3))["figures"], "other")
        self.assertEqual(bs.derive_entry("d", entry())["figures"], "none")


class DisplayFieldTests(unittest.TestCase):
    def test_sort_title(self):
        self.assertEqual(bs.sort_title("The Casebooks Project"), "casebooks project")
        self.assertEqual(bs.sort_title("A Social Edition of the Devonshire MS"), "social edition of the devonshire ms")
        self.assertEqual(bs.sort_title("ABU — Bibliothèque Universelle"), "abu — bibliotheque universelle")
        self.assertEqual(bs.sort_title("«travel!digital»"), "travel!digital»")
        self.assertEqual(bs.sort_title("Ἑλληνικά"), "ελληνικα")

    def test_url_parts(self):
        self.assertEqual(bs.url_parts("http://www.abu.cnam.fr:80/")[:2], ("abu.cnam.fr", "abu.cnam.fr"))
        self.assertEqual(bs.url_parts("https://github.com/ebeshero/Amadis-in-Translation/")[1],
                         "github.com/ebeshero/Amadis-in-Translation")
        host, display, archived = bs.url_parts(
            "http://web.archive.org/web/20010623201249/http://www.snhell.gr:80/a_anth_text.asp")
        self.assertEqual(host, "web.archive.org")
        self.assertEqual(display, "Archived copy of snhell.gr, 2001-06-23")
        self.assertEqual(archived, {"site": "snhell.gr", "date": "2001-06-23"})

    def test_size_band_lower_bound_inclusive(self):
        self.assertEqual(bs.size_band(10_000_000), "10m-plus")
        self.assertEqual(bs.size_band(9_999_999), "1m-10m")
        self.assertEqual(bs.size_band(100_000), "100k-1m")
        self.assertEqual(bs.size_band(0), "under-10k")
        self.assertIsNone(bs.size_band(None))
        self.assertIsNone(bs.size_band(True))

    def test_numbers_and_dates(self):
        self.assertEqual(bs.pct(1, 8), "13%")            # 12.5 rounds half up
        self.assertEqual(bs.pct(1, 3, 1), "33.3%")
        self.assertEqual(bs.pct(1342329634, 2189651998), "61%")
        self.assertEqual(bs.compact_words(2189651998), "2.19 billion")
        self.assertEqual(bs.compact_words(41616768), "41.6 million")
        self.assertEqual(bs.median_int([1, 2]), 2)        # 1.5 rounds half up
        self.assertEqual(bs.long_date("2026-10-08"), "8 October 2026")
        self.assertEqual(bs.month_year("2026-06-26"), "June 2026")
        self.assertEqual(bs.plural(1, "edition"), "1 edition")
        self.assertEqual(bs.plural(1200, "edition"), "1,200 editions")
        self.assertEqual(bs.join_and(["A", "B", "C"]), "A, B and C")

    def test_chart_label(self):
        self.assertEqual(bs.chart_label("EEBO Text Creation Partnership"), "EEBO Text Creation Partnership")
        self.assertEqual(bs.chart_label("NOSCEMUS — Nova Scientia: Early Modern Scientific Literature"), "NOSCEMUS")
        self.assertEqual(bs.chart_label("OpenEDGeS (Open Editions of Early Modern Dutch and German Bibles)"), "OpenEDGeS")


class ExportTests(unittest.TestCase):
    def test_export_fields_follow_the_schema(self):
        schema = bs.load_schema()
        props = dict(schema["properties"])
        fields = bs.export_fields({"properties": props})
        self.assertEqual(fields[:6], ["id", "title", "url", "doi", "data_url", "data_format"])
        self.assertEqual(fields[-1], "notes")
        self.assertEqual(set(fields[1:]), set(props))
        # a property added to a copy of the schema becomes a column without code changes
        props.pop("countries", None)
        props["shelfmark"] = {"type": "string"}
        fields2 = bs.export_fields({"properties": props})
        self.assertNotIn("countries", fields2)
        self.assertEqual(fields2[-2:], ["shelfmark", "notes"])
        props["countries"] = {"type": "array"}
        fields3 = bs.export_fields({"properties": props})
        self.assertLess(fields3.index("region") if "region" in fields3 else 0, fields3.index("countries"))
        self.assertLess(fields3.index("countries"), fields3.index("notes"))

    def test_export_fields_without_region(self):
        """The planned migration removes 'region' from the schema: the columns follow, countries stay."""
        props = dict(bs.load_schema()["properties"])
        props.pop("region", None)
        props.setdefault("countries", {"type": "array"})
        fields = bs.export_fields({"properties": props})
        self.assertNotIn("region", fields)
        self.assertEqual(fields[fields.index("status") + 1], "countries")
        self.assertNotIn("region", bs.csv_columns(fields))

    def test_csv_columns_split_years_active(self):
        self.assertEqual(bs.csv_columns(["id", "years_active", "notes"]),
                         ["id", "years_active_start", "years_active_end", "notes"])

    def test_csv_quoting_and_crlf(self):
        fields = ["id", "title", "languages", "years_active", "notes", "words"]
        e = entry(title='Say "hello", world', languages=["Latin", "Old French"],
                  years_active={"start": 2002, "end": "ongoing"}, notes="line one\nline two", words=12)
        text = bs.csv_text(bs.csv_columns(fields), [bs.csv_row("x-1", e, fields)])
        self.assertEqual(text, 'id,title,languages,years_active_start,years_active_end,notes,words\r\n'
                               'x-1,"Say ""hello"", world",Latin; Old French,2002,ongoing,"line one\nline two",12\r\n')
        self.assertTrue(text.endswith("\r\n"))

    def test_csv_values(self):
        self.assertEqual(bs.csv_value(None), "")
        self.assertEqual(bs.csv_value(["GB-ENG", "IE"]), "GB-ENG; IE")
        self.assertEqual(bs.csv_value({"a": 1, "b": "é"}), '{"a":1,"b":"é"}')
        self.assertEqual(bs.csv_value(True), "true")


class CorpusTotalsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.audit = self.root / "rq_statistics.json"
        self.payload = {"snapshot": "v2026.06", "scope": [1450, 1700], "collections": {
            "listed": {"words": 300, "texts": 3, "corpus_words": 100, "corpus_texts": 1},
            "other": {"words": 700, "texts": 7, "corpus_words": 250, "corpus_texts": 2}}}
        self.audit.write_text(json.dumps(self.payload))

    def tearDown(self):
        self.temp.cleanup()

    def test_complete_corpus_is_independent_of_catalogue_rows_and_raw_resource_sizes(self):
        entries = [("listed.json", entry(words=300, texts=3, notes=NotesTests.RQ))]
        with redirect_stderr(StringIO()):
            meta, _ = bs.build_payload(entries, bs.load_schema(), self.root / "entries")
        self.assertEqual(meta["stats"]["words"], 300)
        self.assertEqual((meta["corpus_statistics"]["words"], meta["corpus_statistics"]["texts"]), (350, 3))
        self.assertEqual(meta["display"]["corpus_words"], "350")

    def test_missing_corpus_audit_never_falls_back_to_summed_resource_sizes(self):
        self.audit.unlink()
        entries = [("listed.json", entry(words=300, texts=3, notes=NotesTests.RQ))]
        with redirect_stderr(StringIO()):
            meta, _ = bs.build_payload(entries, bs.load_schema(), self.root / "entries")
        self.assertIsNone(meta["corpus_statistics"])
        self.assertEqual(meta["display"]["corpus_words"], "—")

    def test_scope_and_duplicate_counts_are_checked(self):
        self.payload["scope"] = [1400, 1800]
        self.audit.write_text(json.dumps(self.payload))
        with self.assertRaises(bs.BuildError):
            bs.load_corpus_statistics(self.audit, "v2026.06")
        self.payload["scope"] = [1450, 1700]
        self.payload["collections"]["listed"]["corpus_words"] = 301
        self.audit.write_text(json.dumps(self.payload))
        with self.assertRaises(bs.BuildError):
            bs.load_corpus_statistics(self.audit, "v2026.06")


class GuardTests(unittest.TestCase):
    def test_reserved_and_malformed_ids_fail(self):
        with self.assertRaises(bs.BuildError) as cm:
            bs.check_entries([("about.json", entry())])
        self.assertIn("section id", str(cm.exception))
        with self.assertRaises(bs.BuildError):
            bs.check_entries([("Bad_Name.json", entry())])
        bs.check_entries([("good-name-2.json", entry())])

    def test_rq_open_corpus_link_fails(self):
        with self.assertRaises(bs.BuildError):
            bs.check_entries([("x.json", entry(url="https://github.com/someone/RQ-Open-Corpus"))])
        with self.assertRaises(bs.BuildError):
            bs.check_entries([("x.json", entry(data_url="https://example.org/rq-open-corpus/x", data_format="tei"))])

    def test_unknown_snapshot_fails(self):
        d = [{"snapshot": "v2099.01"}]
        with self.assertRaises(bs.BuildError) as cm:
            bs.snapshot_versions(d)
        self.assertIn("SNAPSHOTS", str(cm.exception))
        self.assertEqual(bs.snapshot_versions([{"snapshot": "v2026.06"}, {"snapshot": None}]), ["v2026.06"])


class InjectTests(unittest.TestCase):
    DISPLAY = {"editions": "197", "note": "A & B < C", "sha": "abc1234", "url": "https://x.org/commit/abc?a=1&b=2",
               "empty": "", "full": "yes"}
    PAGE = ('<p><b data-stat="editions">0</b> <span class="x" data-stat="note">old</span></p>'
            '<p data-if="empty">gone</p><p data-if="full" hidden>shown</p>'
            '<a href="#" data-href="url"><span data-stat="sha">x</span></a>'
            '<!-- build:share-chart -->old<!-- /build:share-chart -->'
            '<!-- build:languages-chart --><!-- /build:languages-chart -->')
    REGIONS = {"share-chart": "<table>S</table>", "languages-chart": "<table>L</table>"}

    def test_injection(self):
        out = bs.inject(self.PAGE, self.DISPLAY, self.REGIONS)
        self.assertIn('<b data-stat="editions">197</b>', out)
        self.assertIn('data-stat="note">A &amp; B &lt; C</span>', out)
        self.assertIn('<p data-if="empty" hidden>gone</p>', out)
        self.assertIn('<p data-if="full">shown</p>', out)
        self.assertIn('href="https://x.org/commit/abc?a=1&amp;b=2" data-href="url"', out)
        self.assertIn("<!-- build:share-chart -->\n<table>S</table>\n<!-- /build:share-chart -->", out)

    def test_injection_is_idempotent(self):
        once = bs.inject(self.PAGE, self.DISPLAY, self.REGIONS)
        self.assertEqual(bs.inject(once, self.DISPLAY, self.REGIONS), once)
        flipped = dict(self.DISPLAY, empty="now", full="")
        twice = bs.inject(once, flipped, self.REGIONS)
        self.assertIn('<p data-if="empty">gone</p>', twice)
        self.assertIn('<p data-if="full" hidden>shown</p>', twice)

    def test_unknown_key_fails(self):
        for page in ('<span data-stat="nope">x</span>', '<a href="#" data-href="nope">x</a>', '<p data-if="nope">x</p>'):
            with self.assertRaises(bs.BuildError):
                bs.inject(page + self.PAGE, self.DISPLAY, self.REGIONS)

    def test_missing_region_fails(self):
        with self.assertRaises(bs.BuildError):
            bs.inject('<span data-stat="editions">0</span>', self.DISPLAY, self.REGIONS)

    def test_data_stat_must_hold_text_only(self):
        with self.assertRaises(bs.BuildError):
            bs.inject('<span data-stat="editions"><b>0</b></span>' + self.PAGE, self.DISPLAY, self.REGIONS)

    def test_countries_text_follows_the_data(self):
        """The About text on countries and the Area filter shows once an edition records countries."""
        if not bs.COUNTRIES_PATH.exists():
            self.skipTest("schema/countries.json not present")
        page = (REPO / "docs" / "index.html").read_text(encoding="utf-8")
        areas = json.loads(bs.COUNTRIES_PATH.read_text(encoding="utf-8"))["areas"]
        schema = bs.load_schema()
        for countries in ([], ["IT", "GB-ENG"]):
            e = entry(words=10, **({"countries": countries} if countries else {}))
            with redirect_stderr(StringIO()):
                meta, _ = bs.build_payload([("a-test.json", e)], schema, Path(tempfile.gettempdir()))
            regions = {"share-chart": bs.share_chart(meta["stats"]), "languages-chart": bs.languages_chart(meta["stats"])}
            out = bs.inject(page, meta["display"], regions)
            item = re.search(r'<li data-if="with_countries"[^>]*>', out).group(0)
            self.assertEqual(" hidden" in item, not countries)
            self.assertEqual(meta["areas"], areas)
            self.assertIn(bs.join_and(areas), out)

    def test_real_page_has_only_known_keys(self):
        """docs/index.html must only use keys the build produces."""
        page = (REPO / "docs" / "index.html").read_text(encoding="utf-8")
        entries = [("a-test.json", entry(words=100, texts=2, period="1500-1550", notes=NotesTests.RQ)),
                   ("b-test.json", entry(languages=["French", "Greek"], status="archived", words=50))]
        schema = bs.load_schema()
        with redirect_stderr(StringIO()):
            meta, _ = bs.build_payload(entries, schema, Path(tempfile.gettempdir()))
        regions = {"share-chart": bs.share_chart(meta["stats"]), "languages-chart": bs.languages_chart(meta["stats"])}
        out = bs.inject(page, meta["display"], regions)
        self.assertEqual(bs.inject(out, meta["display"], regions), out)


class BuildTests(unittest.TestCase):
    """End-to-end build into a temporary directory (needs jsonschema, like the build)."""

    @classmethod
    def setUpClass(cls):
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("jsonschema not installed")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.entries = self.tmp / "entries"
        self.out = self.tmp / "site"
        self.entries.mkdir()
        samples = {
            "alpha": entry(title="The Alpha Letters", words=1_500_000, texts=40, period="1550-1600",
                           doi="10.5281/zenodo.14559525",
                           notes="Letters. " + NotesTests.RQ + " rebuild/a.tsv"),
            "beta": entry(title="Beta, \"quoted\" corpus", languages=["French", "Latin"], words=2_000, texts=3,
                          period="16th century", status="archived", data_url="https://example.org/beta.zip",
                          data_format="xml", years_active={"start": 2004}),
            "gamma": entry(title="Gamma", languages=["English"], provenance="discovered", period="early modern"),
        }
        for name, e in samples.items():
            (self.entries / f"{name}.json").write_text(json.dumps(e), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_build(self, *extra):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = bs.main(["--entries-dir", str(self.entries), "--out-dir", str(self.out), *extra])
        return code, out.getvalue(), err.getvalue()

    def test_build_writes_outputs_and_is_idempotent(self):
        code, out, err = self.run_build()
        self.assertEqual(code, 0, err)
        self.assertIn("Built site: 3 entries", out)
        for name in ("data.json", "renascor.csv", "renascor.json", "index.html", "app.js"):
            self.assertTrue((self.out / name).exists(), name)
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        code, out, _ = self.run_build()
        self.assertEqual(code, 0)
        self.assertIn("No file changed.", out)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})

        data = json.loads((self.out / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["entries"]), len(data["derived"]))
        for e, d in zip(data["entries"], data["derived"]):
            self.assertEqual(e, json.loads((self.entries / f"{d['id']}.json").read_text(encoding="utf-8")))
        self.assertEqual(data["meta"]["stats"]["editions"], 3)
        self.assertIsNone(data["meta"]["data_commit"])            # not a git checkout: no commit
        self.assertEqual(data["meta"]["updated"], "2026-10-07")   # falls back to the latest date_added

        csv_bytes = (self.out / "renascor.csv").read_bytes()
        self.assertFalse(csv_bytes.startswith(b"\xef\xbb\xbf"))
        lines = csv_bytes.decode("utf-8").split("\r\n")
        self.assertEqual(lines[0], ",".join(data["meta"]["csv_columns"]))
        self.assertTrue(lines[1].startswith("alpha,"))               # default order: sort_title, then id
        self.assertEqual(lines[-1], "")
        self.assertEqual(lines[1].split(",")[data["meta"]["csv_columns"].index("doi")],
                         "10.5281/zenodo.14559525")

        public = json.loads((self.out / "renascor.json").read_text(encoding="utf-8"))
        self.assertEqual([e["id"] for e in public["entries"]], ["alpha", "beta", "gamma"])
        self.assertEqual(list(public["meta"])[:6], ["title", "source", "licence", "version", "data_updated", "data_commit"])
        self.assertNotIn("region", public["entries"][0])            # absent fields are omitted
        self.assertEqual(public["entries"][0]["doi"], "10.5281/zenodo.14559525")
        self.assertIsNone(public["meta"]["corpus_statistics"])

        page = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn('<dd data-stat="editions">3</dd>', page)
        self.assertNotIn("rq-open-corpus", page.lower())

    def test_build_fails_on_reserved_id_and_corpus_link(self):
        (self.entries / "about.json").write_text(json.dumps(entry()), encoding="utf-8")
        code, _, err = self.run_build()
        self.assertEqual(code, 1)
        self.assertIn("section id", err)
        (self.entries / "about.json").unlink()
        (self.entries / "delta.json").write_text(json.dumps(entry(url="https://example.org/RQ-Open-Corpus/")),
                                                 encoding="utf-8")
        code, _, err = self.run_build()
        self.assertEqual(code, 1)
        self.assertIn("RQ Open Corpus", err)

    def test_build_fails_on_unknown_page_key(self):
        template = self.tmp / "template.html"
        template.write_text((REPO / "docs" / "index.html").read_text(encoding="utf-8")
                            .replace("<main ", '<p data-stat="nope">x</p><main ', 1), encoding="utf-8")
        code, _, err = self.run_build("--index", str(template))
        self.assertEqual(code, 1)
        self.assertIn("nope", err)

    def test_invalid_entry_fails_validation(self):
        (self.entries / "bad.json").write_text(json.dumps(entry(status="lost")), encoding="utf-8")
        code, _, err = self.run_build()
        self.assertEqual(code, 1)
        self.assertIn("bad.json", err)


if __name__ == "__main__":
    unittest.main()
