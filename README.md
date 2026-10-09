# Renascor

**Find Renaissance texts online.** An open catalogue of digital editions, manuscripts and correspondence from **1450–1700**.

[![Browse the catalogue](https://img.shields.io/badge/Browse_the_catalogue-1a56db?style=for-the-badge&logo=github&logoColor=white)](https://pantagrueliste.github.io/renascor/)

[![Suggest a collection](https://img.shields.io/badge/Suggest_a_collection-4b5563?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Pantagrueliste/renascor/issues/new?template=new-entry.yml) [![Report a correction](https://img.shields.io/badge/Report_a_correction-4b5563?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Pantagrueliste/renascor/issues/new?template=correction.yml) [![Buy me a coffee](https://img.shields.io/badge/Buy_me_a_coffee-ff5e5b?style=for-the-badge&logo=kofi&logoColor=white)](https://ko-fi.com/clementgodbarge)

## Explore

- Search and filter by language, period, format and collection size.
- Find text files, APIs and licences, with a permanent link to every record.
- Download the catalogue as CSV or JSON, with citation information.

Renascor points to freely accessible collections of transcribed or corrected text. Each record identifies the project, its scope, format, rights, access links and DOI where available.

## Counts and scope

“Renaissance” defines a historical and cultural focus centred on Europe, particularly Western Europe, within **1450–1700**. The catalogue also covers texts arising from documented contacts with other populations, written by any community involved, in any language. See the website’s [scope statement](https://pantagrueliste.github.io/renascor/#about).

Collection sizes count texts within **1450–1700 before content deduplication**. Overlapping collections are welcome. The **Renascor Corpus total excludes duplicate texts**; separate corpus contributions, partial harvests and unknown counts are identified.

## Contribute

Use the links above to suggest a collection or report an error. You can also edit a JSON file in [data/entries](data/entries) and open a pull request. [CONTRIBUTING.md](CONTRIBUTING.md) explains how; the [schema guide](schema/README.md) describes the fields.

Every addition is reviewed by a human. Weekly searches use [Mistral Large 4](https://mistral.ai/news/mistral-large-4/), chosen for its multilingual capabilities and planned open-weight release.

## Reuse and cite

[![Download CSV](https://img.shields.io/badge/Download_CSV-1a56db?style=for-the-badge)](https://pantagrueliste.github.io/renascor/renascor.csv) [![Download JSON](https://img.shields.io/badge/Download_JSON-1a56db?style=for-the-badge)](https://pantagrueliste.github.io/renascor/renascor.json)

| Resource | Terms |
| --- | --- |
| Catalogue metadata | [CC0](LICENSE-DATA) |
| Code | [MIT](LICENSE) |
| Edition texts | Each record gives the source’s licence |

Please cite the catalogue when using it in research: [citation details](CITATION.cff).

## Origins

The catalogue grew out of the **Renascor Corpus Project**, which aims to assemble the most complete possible corpus of Renaissance texts for AI training. The corpus is ongoing and unreleased. Rapid progress in agentic coding assistants made a long-postponed catalogue feasible: a way to clarify which Renaissance texts are available online in digital text form.

## Support

[Buy me a coffee on Ko-fi](https://ko-fi.com/clementgodbarge), or use this repository’s **Sponsor** button. Donations help cover catalogue maintenance and automated discovery.

## Work on the project

```bash
python3 -m pip install -e .
python3 scripts/build_site.py
python3 -m http.server 8000 --directory docs
```

Open [localhost:8000](http://localhost:8000). See [maintenance instructions](docs/MAINTENANCE.md) for tests, source recounts and audits.

---

Maintained by **Clément Godbarge**, Lecturer in Digital Humanities, University of St Andrews. [Behave well.](CODE_OF_CONDUCT.md)
