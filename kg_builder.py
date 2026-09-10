"""
PROTO project — Data Builder pipeline (step: spreadsheet -> RDF)

Reads the shared "Single Source of Truth" spreadsheet and converts it into
an RDF/Turtle knowledge graph, ready to be loaded into a SPARQL endpoint
(TriplyDB / Blazegraph).

Re-runnable: every time teammates add rows to the spreadsheet, just run
this script again to regenerate proto_data.ttl.

NOTE ON NAMESPACES: the ontology namespace below (PROTO_ONTO) is a
PLACEHOLDER. It assumes classes/properties named the way the project brief
describes (Proverb, TacitLesson, hasTacitLesson, etc). Once the Modeler
(TBox lead) shares the real ontology.ttl, swap PROTO_ONTO for the real URI
and re-run -- the row-reading logic below does not need to change.
"""

import re
import pandas as pd
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS
from rdflib.namespace import SKOS, XSD

# ---------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------
PROTO_ONTO = Namespace("https://w3id.org/proto/ontology#")   # placeholder -> replace with Modeler's real ontology URI
PROTO_DATA = Namespace("https://w3id.org/proto/data/")       # placeholder -> replace with real data namespace once hosted (e.g. TriplyDB base)
WD = Namespace("http://www.wikidata.org/entity/")

g = Graph()
g.bind("proto", PROTO_ONTO)
g.bind("data", PROTO_DATA)
g.bind("wd", WD)
g.bind("skos", SKOS)

# Spreadsheet language codes -> proper BCP-47/ISO-639-1 tags.
# ("ita" and "alb" are ISO 639-2/3 codes, not valid RDF language tags —
#  normalized here so language-tagged literals are actually valid.)
LANG_NORMALIZE = {"en": "en", "fa": "fa", "ita": "it", "alb": "sq"}


def slugify(label: str) -> str:
    """Turn a lesson label into a URI-safe slug, e.g.
    'Hidden depths / Deceptive appearances' -> 'HiddenDepths-DeceptiveAppearances'"""
    parts = re.split(r"[/,]", label)
    parts = ["".join(w.capitalize() for w in re.findall(r"[A-Za-z0-9]+", p)) for p in parts]
    return "-".join(p for p in parts if p)


def split_wd_uris(cell: str):
    """'wd:Q34442, wd:Q564' -> ['Q34442', 'Q564']"""
    if not isinstance(cell, str) or not cell.strip():
        return []
    return [tok.strip().split(":")[-1] for tok in cell.split(",") if tok.strip()]


# ---------------------------------------------------------------------
# Load spreadsheet
# ---------------------------------------------------------------------
df = pd.read_excel("The_Single_Source_of_Truth_-_Formatted__2_.xlsx", sheet_name="first page")
df.columns = [c.strip() for c in df.columns]

lesson_uri_by_label = {}   # label -> Wikidata Q-id (sanity-checked for consistency)
lesson_node_by_label = {}  # label -> rdflib URIRef

warnings = []

for _, row in df.iterrows():
    pid = str(row["Proverb ID"]).strip()
    raw_lang = str(row["Language"]).strip()
    lang = LANG_NORMALIZE.get(raw_lang, raw_lang)
    if raw_lang not in LANG_NORMALIZE:
        warnings.append(f"Unrecognized language code '{raw_lang}' on {pid} — used as-is, unnormalized")

    proverb_uri = PROTO_DATA[pid]
    g.add((proverb_uri, RDF.type, PROTO_ONTO.Proverb))
    g.add((proverb_uri, PROTO_ONTO.proverbID, Literal(pid)))
    g.add((proverb_uri, PROTO_ONTO.language, Literal(lang)))
    g.add((proverb_uri, PROTO_ONTO.originalText, Literal(str(row["Original Text"]).strip(), lang=lang)))
    g.add((proverb_uri, PROTO_ONTO.literalTranslation, Literal(str(row["Literal English Translation"]).strip(), lang="en")))
    g.add((proverb_uri, PROTO_ONTO.literalImageLabel, Literal(str(row["Literal Image (Source Domain)"]).strip())))
    g.add((proverb_uri, PROTO_ONTO.situationOfUse, Literal(str(row["Situation of Use"]).strip())))

    # Link literal-image source domain to its Wikidata concept(s)
    for qid in split_wd_uris(row["Literal Image URI"]):
        g.add((proverb_uri, SKOS.closeMatch, WD[qid]))

    # Tacit lesson: create/reuse one shared individual per lesson label
    lesson_label = str(row["Tacit Lesson (Dropdown)"]).strip()
    lesson_qids = split_wd_uris(row["Tacit Lesson URI"])

    if lesson_label not in lesson_node_by_label:
        lesson_slug = slugify(lesson_label)
        lesson_uri = PROTO_DATA[f"Lesson-{lesson_slug}"]
        lesson_node_by_label[lesson_label] = lesson_uri
        g.add((lesson_uri, RDF.type, PROTO_ONTO.TacitLesson))
        g.add((lesson_uri, RDFS.label, Literal(lesson_label, lang="en")))
        for qid in lesson_qids:
            g.add((lesson_uri, SKOS.closeMatch, WD[qid]))
        lesson_uri_by_label[lesson_label] = set(lesson_qids)
    else:
        # sanity check: same lesson label should always point to the same Wikidata concept(s)
        if set(lesson_qids) != lesson_uri_by_label[lesson_label]:
            warnings.append(
                f"Lesson '{lesson_label}' has inconsistent Tacit Lesson URI on {pid}: "
                f"{lesson_qids} vs earlier {lesson_uri_by_label[lesson_label]}"
            )

    g.add((proverb_uri, PROTO_ONTO.hasTacitLesson, lesson_node_by_label[lesson_label]))

# ---------------------------------------------------------------------
# Derive CrossCulturalEquivalence: proverbs in different languages that
# share a TacitLesson are cross-cultural equivalents of each other.
# (This is exactly what the project brief says should "fall out naturally".)
# ---------------------------------------------------------------------
by_lesson = {}
for _, row in df.iterrows():
    lesson_label = str(row["Tacit Lesson (Dropdown)"]).strip()
    by_lesson.setdefault(lesson_label, []).append((str(row["Proverb ID"]).strip(), str(row["Language"]).strip()))

equiv_pairs = 0
for lesson_label, entries in by_lesson.items():
    for i in range(len(entries)):
        for j in range(len(entries)):
            if i == j:
                continue
            pid_a, lang_a = entries[i]
            pid_b, lang_b = entries[j]
            if lang_a != lang_b:
                g.add((PROTO_DATA[pid_a], PROTO_ONTO.crossCulturallyEquivalentTo, PROTO_DATA[pid_b]))
                equiv_pairs += 1

# ---------------------------------------------------------------------
# Serialize + report
# ---------------------------------------------------------------------
g.serialize(destination="proto_data.ttl", format="turtle")

print(f"Rows read from spreadsheet : {len(df)}")
print(f"Triples generated          : {len(g)}")
print(f"Distinct proverbs          : {df['Proverb ID'].nunique()}")
print(f"Distinct tacit lessons     : {df['Tacit Lesson (Dropdown)'].nunique()}")
print(f"Languages                  : {sorted(df['Language'].unique().tolist())}")
print(f"crossCulturallyEquivalentTo triples (directed): {equiv_pairs}")
print()
if warnings:
    print("WARNINGS:")
    for w in warnings:
        print(" -", w)
else:
    print("No data-quality warnings.")