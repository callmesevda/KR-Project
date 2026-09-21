# PROTO — Proverbs & Tacit-knowledge Ontology

PROTO is an OWL ontology that models proverbs, the tacit (unspoken) lessons
they carry, the situations in which they are used, and the cross-cultural
equivalences that link a proverb in one language to a proverb in another
when they teach the same lesson — whether or not they share the same
imagery.

**Course:** Knowledge Representation and Extraction.

**Project website:** _pending — will be published via GitHub Pages once this
branch is merged. See [Publishing the website](#publishing-the-website)
below._

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

**Analyst review (proposal not yet applied to the graph).** Polikseni Hasanaj's 15 September 2026
review hand-checked all 48 cross-cultural equivalence links against the
original text, translation, and situation of use, and found the
auto-generated classification (which only compares source-domain tags for
exact equality) misses real matches and over-links a few pairs. Her
proposed reclassification — 6 `DirectMatch` / 32 `SameLessonDifferentImage`
/ 10 `PartialOverlap` (vs. the published 5 / 43 / 0) plus 4 cross-lesson
`FalseFriend` candidates — is summarized on
[`docs/database.html#review`](docs/database.html) and hasn't been merged
into the graph. The team has settled the review's open questions: the
six lessons are kept (not split), the Persian and Italian readings are
confirmed, and her 8 SPARQL queries are adopted as the project's
competency questions on [`docs/questions.html`](docs/questions.html).

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

### Publishing the website

To publish via GitHub Pages once this branch is merged into `main`:

1. Repository **Settings → Pages**.
2. Source: **Deploy from a branch**.
3. Branch: `main`, folder: `/docs`.
4. Save — the site will be published at `https://callmesevda.github.io/KR-Project/`.

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
fields — license and authors are filled in; `citeAs` and `DOI` stay
blank until the Zenodo DOI exists.

`docs/documentation.html` already links to `docs/documentation/index-en.html`
(full reference) and `docs/documentation/webvowl/index.html` (visual schema
browser) — no changes needed there after a regeneration.

## Archiving on Zenodo (for the DOI)

The professor requires a permanent, citable release. `CITATION.cff` and
`.zenodo.json` in the repository root carry the deposit metadata (title,
description, keywords, all four authors). One thing is still a placeholder pending the team:
the real **DOI** (the license, CC BY 4.0, is confirmed).

Steps (need a Zenodo account with GitHub linked — not something that can be
done from here):

1. Log in to [zenodo.org](https://zenodo.org) with GitHub, enable this
   repository under **GitHub → Repositories**.
2. Cut a GitHub **release** (e.g. `v1.0.0`) — Zenodo archives it
   automatically and mints a DOI.
3. Update the "Cite & archive" footer on every page of `docs/` (currently
   marked "pending Zenodo deposit") with the real DOI badge/link.

## Team

- **Sevda Rezaei Melal** — ontology modeling (TBox) & the published knowledge graph
- **Polikseni Hasanaj** ("Ksenia" in the review) — cross-cultural analysis
- **Saba Afsharzadehtorghab** — Persian-language verification
- **Claudia Briccolani** — website, documentation & dissemination

See [`docs/team.html`](docs/team.html).
