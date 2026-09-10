"""
PROTO project — Data Builder pipeline (step: spreadsheet -> RDF)

Reads the shared "Single Source of Truth" spreadsheet and converts it into
an RDF/Turtle knowledge graph that matches the Modeler's ontology.ttl
(classes/properties: Proverb, TacitLesson, SourceDomain, SituationOfUse,
CrossCulturalEquivalence, hasLesson, hasSourceDomain, usedIn, groundedIn,
linksProverbA/B, hasEquivalenceType, etc).

Re-runnable: every time teammates add rows to the spreadsheet, run this
again to regenerate proto_data.ttl. If the Modeler revises ontology.ttl,
only the PROTO namespace constant below should ever need to change.
"""

import itertools
import re
import pandas as pd
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL

# ---------------------------------------------------------------------
# Namespaces — taken directly from ontology.ttl
# ---------------------------------------------------------------------
PROTO = Namespace("http://example.org/proto#")
WD = Namespace("http://www.wikidata.org/entity/")

g = Graph()
g.bind("", PROTO)
g.bind("wd", WD)


def pascalize(label: str) -> str:
    """'Hidden depths / Deceptive appearances' -> 'HiddenDepthsDeceptiveAppearances'
    (matches the Modeler's own individual-naming style, e.g. :DontBeLazy, :EarlyBird)."""
    words = re.findall(r"[A-Za-z0-9]+", label)
    return "".join(w.capitalize() for w in words)


def split_pair(label_cell: str, uri_cell: str):
    """Split a '/'-joined label cell and a ','-joined wd: URI cell into
    aligned (label, qid) pairs. Assumes a 1:1 count match (verified upfront)."""
    labels = [x.strip() for x in str(label_cell).split("/")]
    qids = [x.strip().split(":")[-1] for x in str(uri_cell).split(",")]
    return list(zip(labels, qids))


# ---------------------------------------------------------------------
# Load spreadsheet
# ---------------------------------------------------------------------
df = pd.read_excel("The_Single_Source_of_Truth_-_Formatted__2_.xlsx", sheet_name="first page")
df.columns = [c.strip() for c in df.columns]

lesson_node_by_label = {}       # lesson label -> URIRef, deduped
lesson_qids_by_label = {}       # lesson label -> set of qids seen (consistency check)
source_domain_node_by_label = {}  # source-domain label -> URIRef, deduped
source_domain_qid_by_label = {}   # source-domain label -> qid seen (consistency check)

warnings = []
row_source_domains = {}  # proverb id -> set of source-domain labels (for equivalence-type check)

for _, row in df.iterrows():
    pid = str(row["Proverb ID"]).strip()
    lang = str(row["Language"]).strip()

    proverb_uri = PROTO[pid]
    g.add((proverb_uri, RDF.type, OWL.NamedIndividual))
    g.add((proverb_uri, RDF.type, PROTO.Proverb))
    g.add((proverb_uri, PROTO.hasProverbID, Literal(pid)))
    g.add((proverb_uri, PROTO.hasLanguage, Literal(lang)))
    g.add((proverb_uri, PROTO.hasText, Literal(str(row["Original Text"]).strip())))
    g.add((proverb_uri, PROTO.hasTranslation, Literal(str(row["Literal English Translation"]).strip())))

    # --- SourceDomain: one individual per '/'-split image concept, deduped by label ---
    sd_labels = set()
    for label, qid in split_pair(row["Literal Image (Source Domain)"], row["Literal Image URI"]):
        sd_labels.add(label)
        if label not in source_domain_node_by_label:
            sd_uri = PROTO[pascalize(label)]
            source_domain_node_by_label[label] = sd_uri
            source_domain_qid_by_label[label] = qid
            g.add((sd_uri, RDF.type, OWL.NamedIndividual))
            g.add((sd_uri, RDF.type, PROTO.SourceDomain))
            g.add((sd_uri, RDFS.label, Literal(label)))
            g.add((sd_uri, PROTO.groundedIn, WD[qid]))
        elif source_domain_qid_by_label[label] != qid:
            warnings.append(
                f"SourceDomain '{label}' has inconsistent Wikidata QID on {pid}: "
                f"{qid} vs earlier {source_domain_qid_by_label[label]}"
            )
        g.add((proverb_uri, PROTO.hasSourceDomain, source_domain_node_by_label[label]))
    row_source_domains[pid] = sd_labels

    # --- SituationOfUse: one individual per proverb (text is essentially unique per row) ---
    situation_uri = PROTO[f"Situation_{pid}"]
    g.add((situation_uri, RDF.type, OWL.NamedIndividual))
    g.add((situation_uri, RDF.type, PROTO.SituationOfUse))
    g.add((situation_uri, RDFS.label, Literal(str(row["Situation of Use"]).strip())))
    g.add((proverb_uri, PROTO.usedIn, situation_uri))

    # --- TacitLesson: one individual per distinct lesson label, deduped ---
    lesson_label = str(row["Tacit Lesson (Dropdown)"]).strip()
    lesson_qids = [x.strip().split(":")[-1] for x in str(row["Tacit Lesson URI"]).split(",")]
    if lesson_label not in lesson_node_by_label:
        lesson_uri = PROTO[pascalize(lesson_label)]
        lesson_node_by_label[lesson_label] = lesson_uri
        lesson_qids_by_label[lesson_label] = set(lesson_qids)
        g.add((lesson_uri, RDF.type, OWL.NamedIndividual))
        g.add((lesson_uri, RDF.type, PROTO.TacitLesson))
        g.add((lesson_uri, PROTO.hasLabel, Literal(lesson_label)))
        for qid in lesson_qids:
            g.add((lesson_uri, PROTO.groundedIn, WD[qid]))
    elif set(lesson_qids) != lesson_qids_by_label[lesson_label]:
        warnings.append(
            f"TacitLesson '{lesson_label}' has inconsistent Wikidata QID(s) on {pid}: "
            f"{lesson_qids} vs earlier {lesson_qids_by_label[lesson_label]}"
        )
    g.add((proverb_uri, PROTO.hasLesson, lesson_node_by_label[lesson_label]))

# ---------------------------------------------------------------------
# CrossCulturalEquivalence: reified individual per unordered pair of
# proverbs (different languages) sharing a TacitLesson.
# ---------------------------------------------------------------------
by_lesson = {}
for _, row in df.iterrows():
    lesson_label = str(row["Tacit Lesson (Dropdown)"]).strip()
    by_lesson.setdefault(lesson_label, []).append(
        (str(row["Proverb ID"]).strip(), str(row["Language"]).strip())
    )

n_equivalences = 0
n_needs_review = 0
for lesson_label, entries in by_lesson.items():
    for (pid_a, lang_a), (pid_b, lang_b) in itertools.combinations(entries, 2):
        if lang_a == lang_b:
            continue
        equiv_uri = PROTO[f"Equiv_{pid_a}_{pid_b}"]
        g.add((equiv_uri, RDF.type, OWL.NamedIndividual))
        g.add((equiv_uri, RDF.type, PROTO.CrossCulturalEquivalence))
        g.add((equiv_uri, PROTO.linksProverbA, PROTO[pid_a]))
        g.add((equiv_uri, PROTO.linksProverbB, PROTO[pid_b]))

        domains_a, domains_b = row_source_domains[pid_a], row_source_domains[pid_b]
        if domains_a != domains_b:
            g.add((equiv_uri, PROTO.hasEquivalenceType, PROTO.SameLessonDifferentImage))
            g.add((equiv_uri, PROTO.hasDivergenceNote, Literal(
                f"Auto-derived: shared tacit lesson '{lesson_label}'; "
                f"source domains differ ({', '.join(domains_a)} vs {', '.join(domains_b)})."
            )))
        else:
            # Same lesson AND same source domain -- doesn't fit any of the
            # three defined EquivalenceType individuals cleanly. Left
            # untyped on purpose rather than guessed; flagged below.
            g.add((equiv_uri, PROTO.hasDivergenceNote, Literal(
                f"Auto-derived: shared tacit lesson '{lesson_label}' AND identical source domain "
                f"({', '.join(domains_a)}) -- needs manual review / possible new EquivalenceType."
            )))
            n_needs_review += 1
        n_equivalences += 1

# ---------------------------------------------------------------------
# Serialize + report
# ---------------------------------------------------------------------
g.serialize(destination="proto_data.ttl", format="turtle")

print(f"Rows read from spreadsheet         : {len(df)}")
print(f"Triples generated                  : {len(g)}")
print(f"Distinct proverbs                  : {df['Proverb ID'].nunique()}")
print(f"Distinct tacit lessons             : {df['Tacit Lesson (Dropdown)'].nunique()}")
print(f"Distinct source domains            : {len(source_domain_node_by_label)}")
print(f"CrossCulturalEquivalence instances : {n_equivalences}")
print(f"  ...of which need manual review   : {n_needs_review} (same lesson AND same image)")
print()
if warnings:
    print("WARNINGS:")
    for w in warnings:
        print(" -", w)
else:
    print("No data-quality warnings.")
