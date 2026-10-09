"""Submission and discovery metadata must survive conversion into public records."""
import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

from scripts import discover, issue_to_entry
from scripts.languages import catalogue_languages

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "schema/entry.schema.json").read_text())


class EntryIngestTests(unittest.TestCase):
    def test_form_doi_normalization_and_language_categories(self):
        body = """### Project name
Letters

### URL
https://example.org/letters

### Language(s)
Latin, Ancient Greek, Modern Greek, Multilingual, Romance (other)

### Collection DOI
https://doi.org/10.5281/zenodo.14559525
"""
        entry = issue_to_entry.fields_to_entry(issue_to_entry.parse_issue_body(body))
        self.assertEqual(entry["doi"], "10.5281/zenodo.14559525")
        self.assertEqual(entry["languages"], ["Latin", "Greek"])
        jsonschema.validate(entry, SCHEMA)
        for value in ["10.5281/zenodo.14559525", "DOI: 10.5281/zenodo.14559525",
                      "http://dx.doi.org/10.5281/zenodo.14559525"]:
            entry = issue_to_entry.fields_to_entry({"collection doi": value})
            self.assertEqual(entry["doi"], "10.5281/zenodo.14559525")

    def test_discovery_preserves_identifiers_rights_and_access_metadata(self):
        candidate = {"title": "Letters", "url": "https://example.org/letters", "languages": ["Modern Greek"],
                     "encoding": "tei", "doi": "10.5281/zenodo.14559525", "texts": 10,
                     "data_url": "https://example.org/data", "data_format": "tei", "data_formats": ["tei", "plain-text"],
                     "api_url": "https://example.org/api", "license": "CC-BY-4.0",
                     "license_url": "https://example.org/terms", "license_note": "Texts only."}
        entry = discover.candidate_to_entry(candidate)
        for key in ["doi", "texts", "data_formats", "api_url", "license", "license_url", "license_note"]:
            self.assertEqual(entry[key], candidate[key])
        self.assertEqual(entry["languages"], ["Greek"])
        jsonschema.validate(entry, SCHEMA)

    def test_invalid_doi_and_retired_language_labels_are_rejected(self):
        entry = discover.candidate_to_entry({"title": "Letters", "url": "https://example.org", "languages": ["Latin"]})
        for value in ["https://doi.org/10.5281/zenodo.1", "10.5281/contains spaces", "not-a-doi"]:
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(dict(entry, doi=value), SCHEMA)
        for label in ["Ancient Greek", "Modern Greek", "Multilingual", "Romance", "Romance (other)"]:
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(dict(entry, languages=[label]), SCHEMA)
        self.assertEqual(catalogue_languages(["Greek", "Modern Greek", "Romance", "Latin"]), ["Greek", "Latin"])

    def test_only_active_rejections_block_discovery(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rejected.json"
            active = {"title": "Subscription collection", "url": "https://example.org", "reason": "Paid access."}
            path.write_text(json.dumps({"rejected": [active], "review_pending": [{"title": "Overlapping texts"}]}))
            self.assertEqual(discover.load_rejected(path), [active])
