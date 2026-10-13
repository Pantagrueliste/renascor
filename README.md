# Renascor 
An open catalogue of digital editions from **1450–1700**.
[![Deployment](https://img.shields.io/github/actions/workflow/status/Pantagrueliste/renascor/pages.yml?branch=main&style=for-the-badge&label=Deployment&logo=github&logoColor=white)](https://github.com/Pantagrueliste/renascor/actions/workflows/pages.yml) [![WCAG 2.2 AA](https://img.shields.io/badge/WCAG_2.2-AA-1a7f37?style=for-the-badge)](https://pantagrueliste.github.io/renascor/#accessibility)  
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.23345610-1682d4?style=for-the-badge)](https://doi.org/10.5281/zenodo.23345610) 
[![Suggest a collection](https://img.shields.io/badge/Suggest_a_collection-4b5563?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Pantagrueliste/renascor/issues/new?template=new-entry.yml) [![Report a correction](https://img.shields.io/badge/Report_a_correction-4b5563?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Pantagrueliste/renascor/issues/new?template=correction.yml) [![Buy me a coffee](https://img.shields.io/badge/Buy_me_a_coffee-ff5e5b?style=for-the-badge&logo=kofi&logoColor=white)](https://ko-fi.com/clementgodbarge)


## Who this is for

Researchers, teachers, students and readers who need Renaissance texts in digital form, and the librarians, collection managers and volunteers who help catalogue them.

If you are looking for a text, start at the [catalogue](https://pantagrueliste.github.io/renascor/). If you know a collection we are missing, or spot an error, the links above are the fastest way in.

## What it is

Renascor is an open, searchable catalogue that points to freely accessible collections of digital texts from the Renaissance. It does not host the texts: each record identifies the project behind a collection, its scope, format, rights, access links and DOI where available.

- Search and filter by language, period, format and collection size.
- Find text files, APIs and licences, with a permanent link to every record.
- Download the whole catalogue as CSV or JSON, with citation information.

Renascor aims at being cheap, lean, and sustainable. It does not receive any funding.

## When: scope and origins

By "Renaissance" we understand a historical period emerging from Europe and the Mediterranean within **1450–1700**. The catalogue also covers texts arising from documented contacts with populations around the world, written on either side of these exchanges, in any language. See the website's [scope statement](https://pantagrueliste.github.io/renascor/#about).

Collection sizes count each individual texts within 1450–1700. The **Renascor Corpus total excludes duplicate texts**, and separate corpus contributions, partial harvests and unknown counts are identified as such.

The catalogue grew out of the **Renascor Corpus Project**, which aims to assemble the most complete possible corpus of Renaissance texts for AI training. That corpus is ongoing and unreleased. Rapid progress in agentic coding assistants made this long-postponed side project feasible: a way to map which Renaissance texts are available online in digital text form.

## How: use, contribute, support, run

### Use it

[![Browse the catalogue](https://img.shields.io/badge/Browse_the_catalogue-1a56db?style=for-the-badge&logo=github&logoColor=white)](https://pantagrueliste.github.io/renascor/)   
[![Download CSV](https://img.shields.io/badge/Download_CSV-1a56db?style=for-the-badge)](https://pantagrueliste.github.io/renascor/renascor.csv) [![Download JSON](https://img.shields.io/badge/Download_JSON-1a56db?style=for-the-badge)](https://pantagrueliste.github.io/renascor/renascor.json) [![Download BibTeX](https://img.shields.io/badge/Download_BibTeX-1a56db?style=for-the-badge)](https://pantagrueliste.github.io/renascor/renascor.bib)

| Resource | Terms |
| --- | --- |
| Catalogue metadata | [CC0](LICENSE-DATA) |
| Code | [MIT](LICENSE) |
| Edition texts | Each record gives the source's licence |

Please cite the catalogue when using it in research. Every release is archived on Zenodo under the DOI [10.5281/zenodo.23345610](https://doi.org/10.5281/zenodo.23345610), which always resolves to the latest version; see the [citation details](CITATION.cff).

### Contribute

Use the buttons at the top of this page to suggest a collection or report a correction. You can also edit a JSON file in [data/entries](data/entries) and open a pull request — [CONTRIBUTING.md](CONTRIBUTING.md) explains how, and the [schema guide](schema/README.md) describes the fields.

Every addition is reviewed by a human. Weekly automated searches use [Mistral Large 4](https://mistral.ai/news/mistral-large-4/), chosen for its multilingual capabilities and planned open-weight release.

[Code of Conduct](https://www.gutenberg.org/files/67799/67799-h/67799-h.htm)

### Support the project

[Buy me a coffee on Ko-fi](https://ko-fi.com/clementgodbarge), or use this repository's **Sponsor** button. Donations help cover catalogue maintenance and automated discovery.

### Run it locally

```bash
python3 -m pip install -e .
python3 scripts/build_site.py
python3 -m http.server 8000 --directory docs
```

Open [localhost:8000](http://localhost:8000). See [maintenance instructions](docs/MAINTENANCE.md) for tests, source recounts and audits.

---

Maintained by **Clément Godbarge**, Lecturer in Digital Humanities, University of St Andrews.
