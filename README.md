# PROTO — Proverbs & Tacit-knowledge Ontology

PROTO is an OWL ontology that models proverbs, the tacit (unspoken) lessons
they carry, the situations in which they are used, and the cross-cultural
equivalences that link a proverb in one language to a proverb in another
when they teach the same lesson — whether or not they share the same
imagery.

**Course:** Knowledge Representation and Extraction.

## Repository contents

| File | Description |
|---|---|
| [`proto-ontology-structure.ttl`](proto-ontology-structure.ttl) | The TBox: 5 classes, a 4-value controlled vocabulary (`EquivalenceType`), 6 object properties, 8 data properties. |
| [`proto_data.ttl`](proto_data.ttl) | The ABox: 834 triples generated from the spreadsheet below — 28 proverbs, 6 tacit lessons, 40 source domains, 48 cross-cultural equivalences. |
| [`The Single Source of Truth - Formatted.xlsx`](<The Single Source of Truth - Formatted.xlsx>) | The shared spreadsheet: one row per proverb, annotated with language, literal text, translation, source domain, tacit lesson, situation of use, and Wikidata groundings. |
| [`xlsx_to_rdf.py`](xlsx_to_rdf.py) | Converts the spreadsheet into the ABox, deduplicating repeated lessons/domains and deriving `CrossCulturalEquivalence` instances automatically. |
| [`docs/`](docs/) | The project website (see below). |

TBox + ABox (931 triples combined) are also published live as the
`proverbs-kr` dataset on
[TriplyDB](https://triplydb.com/SevdaRezaeiMelal/proverbs-kr), with a
working public [SPARQL endpoint](https://triplydb.com/SevdaRezaeiMelal/proverbs-kr/sparql) —
no local triplestore needed to query it.

## The website

The `docs/` folder is a static site (no build step) with the pages:

- **Home** (`index.html`) — project overview, stats, core classes.
- **Proverbs** (`proverbs.html`) — a filterable table of all 28 proverbs.
- **Database** (`database.html`) — downloads, dataset statistics, a
  cross-cultural-equivalence browser, and example SPARQL queries.
- **Documentation** (`documentation.html`) — schema reference plus links to
  the full [WIDOCO](https://github.com/dgarijo/Widoco)-generated
  documentation and WebVOWL schema browser (`docs/documentation/`).
- **Questions** (`questions.html`) — the 8 competency questions, each
  one a SPARQL query from Polikseni's analyst review.
- **Team** (`team.html`) — contributors.

Data used by the Proverbs/Database pages is generated from the ABox and
spreadsheet into `docs/assets/js/proto-data.js` (see
`docs/data/proverbs.json` / `docs/data/equivalences.json` for the same data
as plain JSON).

## Regenerating the WIDOCO documentation

`docs/documentation/` is already generated and committed. If the TBox
(`proto-ontology-structure.ttl`) changes, regenerate it with
[WIDOCO](https://github.com/dgarijo/Widoco) (requires Java 11+) from the
repository root:

```bash
java -jar widoco.jar \
  -ontFile proto-ontology-structure.ttl \
  -outFolder docs/documentation \
  -confFile widoco-config.properties \
  -webVowl -rewriteAll -lang en -includeAnnotationProperties
```

`widoco-config.properties` carries the real abstract/introduction text (so
WIDOCO doesn't fall back to its placeholder boilerplate) plus metadata
fields — license and authors are filled in; `citeAs` and `DOI` stay blank
for now.

`docs/documentation.html` already links to `docs/documentation/index-en.html`
(full reference) and `docs/documentation/webvowl/index.html` (visual schema
browser) — no changes needed there after a regeneration.

## Team

- **Sevda Rezaei Melal** — knowledge graph (ABox) & the published knowledge graph
- **Polyxeni Chasanai** — cross-cultural analysis
- **Saba Afsharzadehtorghab** —  ontology structure model
- **Claudia Briccolani** — website, documentation & dissemination

See [`docs/team.html`](docs/team.html).
