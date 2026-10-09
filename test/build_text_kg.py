"""Build the PROTO text knowledge graph (test/text_kg.ttl) from test/texts.json.

Point 6 of the v1.1 improvements: test the ontology by using it as a lens on
real texts (news, blogs, forums, social media). Each text is annotated by hand
in texts.json; this script turns the annotations into RDF that

  * uses only core PROTO for what PROTO can already express
    (Proverb, TacitLesson, SituationOfUse, usedIn, CrossCulturalEquivalence), and
  * uses the proposed extension (proto-text-extension.ttl) for what it cannot
    (the text, the speaker, the target, the stance).

Usage:  python test/build_text_kg.py
"""
import json
import re
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD

HERE = Path(__file__).resolve().parent
RAW = 'https://raw.githubusercontent.com/callmesevda/KR-Project/main/'

TBOX_DOC = URIRef(RAW + 'proto-ontology-structure.ttl')
ABOX_DOC = URIRef(RAW + 'proto_data.ttl')
EXT_DOC = URIRef(RAW + 'test/proto-text-extension.ttl')
TKG_DOC = URIRef(RAW + 'test/text_kg.ttl')

PROTO = Namespace(str(TBOX_DOC) + '#')   # schema (classes, properties)
KG = Namespace(str(ABOX_DOC) + '#')      # main knowledge graph (PRV-001 ...)
PEXT = Namespace(str(EXT_DOC) + '#')     # proposed extension
T = Namespace(str(TKG_DOC) + '#')        # this text graph
WD = Namespace('http://www.wikidata.org/entity/')

ANNOTATOR = 'Polyxeni Chasanai'

# Proverbs found in the texts that are NOT in the main corpus.
NEW_PROVERBS = {
    'PRV-101': dict(
        text='A few bad apples.',
        language='en',
        translation='A few bad apples.',
        lesson='GroupVulnerability',
        domains=[('Apple', 'Q89')],
        comment=("Modern shortened form of 'One bad apple spoils the (whole) barrel'. "
                 "Found in texts T1 and T2, where it is used with the opposite meaning "
                 "(only a few members are bad, the group is fine)."),
        # Same tacit lesson as the Albanian sheep proverb, different image.
        equivalent_to=('PRV-031', 'SameLessonDifferentImage',
                       "Added from the text test. Same lesson as the Albanian 'Një dele e "
                       "zgjebosur prish gjithë tufën' (one bad member spoils the group), "
                       "different image (apple vs sheep). In current English usage the "
                       "short form 'a few bad apples' reverses the lesson; see occurrences "
                       "Occ_T1_1 and Occ_T2_1."),
    ),
}


def local(label):
    return ''.join(w.capitalize() for w in re.findall(r'[A-Za-z0-9]+', label))


def proverb_uri(pid):
    return T[pid] if pid in NEW_PROVERBS else KG[pid]


def build(texts):
    g = Graph()
    for prefix, ns in [('', T), ('proto', PROTO), ('kg', KG), ('pext', PEXT),
                       ('wd', WD), ('dcterms', DCTERMS), ('owl', OWL)]:
        g.bind(prefix, ns)

    g.add((TKG_DOC, RDF.type, OWL.Ontology))
    for doc in (TBOX_DOC, ABOX_DOC, EXT_DOC):
        g.add((TKG_DOC, OWL.imports, doc))
    g.add((TKG_DOC, RDFS.label, Literal('PROTO text knowledge graph (test of point 6)', lang='en')))
    g.add((TKG_DOC, RDFS.comment, Literal(
        'Proverbs found in nine real texts (news, opinion, blogs, a forum and a social-media '
        'post in English, Albanian, Italian and Persian), described with PROTO and the '
        'proposed text-usage extension.', lang='en')))
    g.add((TKG_DOC, DCTERMS.creator, Literal(ANNOTATOR)))
    g.add((TKG_DOC, DCTERMS.created, Literal('2026-10-07', datatype=XSD.date)))
    g.add((TKG_DOC, DCTERMS.license, URIRef('https://creativecommons.org/licenses/by/4.0/')))

    def individual(uri, cls):
        g.add((uri, RDF.type, OWL.NamedIndividual))
        g.add((uri, RDF.type, cls))

    # New proverbs (core PROTO only)
    for pid, p in NEW_PROVERBS.items():
        uri = T[pid]
        individual(uri, PROTO.Proverb)
        g.add((uri, PROTO.hasProverbID, Literal(pid)))
        g.add((uri, PROTO.hasText, Literal(p['text'])))
        g.add((uri, PROTO.hasLanguage, Literal(p['language'])))
        g.add((uri, PROTO.hasTranslation, Literal(p['translation'])))
        g.add((uri, PROTO.hasLesson, KG[p['lesson']]))
        g.add((uri, RDFS.comment, Literal(p['comment'], lang='en')))
        for label, qid in p['domains']:
            d = T[local(label)]
            individual(d, PROTO.SourceDomain)
            g.add((d, RDFS.label, Literal(label)))
            g.add((d, PROTO.groundedIn, WD[qid]))
            g.add((uri, PROTO.hasSourceDomain, d))
        other, kind, note = p['equivalent_to']
        e = T[f'Equiv_{other}_{pid}']
        individual(e, PROTO.CrossCulturalEquivalence)
        g.add((e, PROTO.linksProverbA, KG[other]))
        g.add((e, PROTO.linksProverbB, uri))
        g.add((e, PROTO.hasEquivalenceType, PROTO[kind]))
        g.add((e, PROTO.hasDivergenceNote, Literal(note)))
        g.add((e, PROTO.annotatedBy, Literal(ANNOTATOR)))

    targets = {}
    for text in texts:
        tid = text['id']
        doc = T[tid]
        individual(doc, PEXT.Text)
        g.add((doc, DCTERMS.title, Literal(text['title'], lang=text['language'])))
        g.add((doc, DCTERMS.publisher, Literal(text['publisher'])))
        g.add((doc, DCTERMS.language, Literal(text['language'])))
        g.add((doc, DCTERMS.source, URIRef(text['url'])))
        g.add((doc, PEXT.hasGenre, PEXT[text['genre']]))
        if text.get('author'):
            g.add((doc, DCTERMS.creator, Literal(text['author'])))
        if text.get('date'):
            g.add((doc, DCTERMS.date, Literal(text['date'], datatype=XSD.date)))

        for n, occ in enumerate(text['occurrences'], start=1):
            key = f'{tid}_{n}'
            prov = proverb_uri(occ['proverb'])

            # --- Core PROTO layer: the proverb is used in a new situation ---
            sit = T[f'Situation_{key}']
            individual(sit, PROTO.SituationOfUse)
            g.add((sit, RDFS.label, Literal(occ['situation'], lang='en')))
            g.add((sit, DCTERMS.source, URIRef(text['url'])))
            g.add((prov, PROTO.usedIn, sit))

            # --- Extension layer: who, to whom, how ---
            tlabel = occ['target']
            if tlabel not in targets:
                turi = T['Target_' + local(tlabel)]
                targets[tlabel] = turi
                individual(turi, PEXT.SocialGroup if occ['target_is_group'] else PEXT.Target)
                g.add((turi, RDFS.label, Literal(tlabel, lang='en')))
            o = T[f'Occ_{key}']
            individual(o, PEXT.ProverbOccurrence)
            g.add((o, PEXT.occurrenceOf, prov))
            g.add((o, PEXT.occursIn, doc))
            g.add((o, PEXT.inSituation, sit))
            g.add((o, PEXT.appliedTo, targets[tlabel]))
            g.add((o, PEXT.hasStance, PEXT[occ['stance']]))
            g.add((o, PEXT.quote, Literal(text['excerpt'], lang=text['language'])))
            g.add((o, PEXT.speaker, Literal(occ['speaker'])))
            g.add((o, PEXT.hasMeaningShift, Literal(bool(occ['meaning_shift']))))
            if occ.get('note'):
                g.add((o, RDFS.comment, Literal(occ['note'], lang='en')))
    return g


def main():
    texts = json.loads((HERE / 'texts.json').read_text(encoding='utf-8'))
    g = build(texts)
    out = HERE / 'text_kg.ttl'
    out.write_text(g.serialize(format='turtle'), encoding='utf-8')
    n_occ = sum(len(t['occurrences']) for t in texts)
    print(f'{out.name}: {len(g)} triples, {len(texts)} texts, {n_occ} occurrences')


if __name__ == '__main__':
    main()
