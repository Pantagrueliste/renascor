# Renascore

An open catalogue of digital editions of Renaissance-era written documents: manuscripts, printed works, and correspondence.

The name blends Latin *renascor* ('I am reborn') with 'corpus'.

## What this is

Renascore records projects that have produced digital editions of texts from roughly 1450 to 1700. Each entry describes one edition project: who made it, what it contains, in which language, in which format, and where to find it.

This is a catalogue of editions, not a corpus of texts. We do not host the texts themselves. We point to them.

## What is in an entry

Every entry in `data/entries/` is a single JSON file describing one edition project. The full field list is defined in `schema/entry.schema.json`. At minimum, each entry records:

- the title of the project or collection
- the URL where the edition can be found
- the language or languages of the texts
- the encoding format (TEI, HTML, Markdown, or other)
- whether the project is active or archived
- how the entry was added (submitted by a contributor, or discovered by automated search)
- the date the entry was added

## How to contribute

There are two ways to add an entry:

1. **Open an issue.** Use the [new entry form](https://github.com/Pantagrueliste/renascore/issues/new?template=new-entry.yml). You do not need to know Git or JSON.
2. **Edit a file directly.** Add a JSON file to `data/entries/` and open a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for the format.

Every contribution is reviewed by a human before it appears in the catalogue.

## The public site

The catalogue is published as a static website at [renascore.github.io](https://renascore.github.io) (or your GitHub Pages URL). The site is generated from the JSON files in `data/entries/` and offers:

- search across all entries
- filters for language, period, region, encoding, and status
- download of the full dataset as CSV or JSON

### Running the site locally

```bash
# Build the site data from entries
python scripts/build_site.py

# Serve the site locally (Python 3)
python -m http.server 8000 --directory docs
```

Then open http://localhost:8000 in your browser.

## Licence

- **Data** (the JSON files in `data/entries/`): [CC0 1.0 Universal](LICENSE-DATA). You may use, modify, and share the data for any purpose, with no obligation to attribute.
- **Code** (scripts, site generator): [MIT Licence](LICENSE).

## Citation

If you use this catalogue in your research, please cite it. See [CITATION.cff](CITATION.cff).

## Contact

Clément Godbarge, Lecturer in Digital Humanities, University of St Andrews.
