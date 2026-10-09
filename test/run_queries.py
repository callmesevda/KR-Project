"""Run every query in test/queries.rq and write the results to test/query_results.md.

Loads the schema, the main knowledge graph, the text-usage extension and the
text graph into one graph (what owl:imports declares), then:
  1. runs CQ1-CQ8, V1-V4, TQ1-TQ5;
  2. runs an OWL 2 RL reasoner (owlrl) and checks for inconsistencies;
  3. repeats step 2 on a copy with one deliberately wrong triple, to show the
     restrictions catch it.

Usage:
  python test/run_queries.py                 # files from the repository root
  python test/run_queries.py --kg-dir DIR    # take TBox + ABox from DIR instead
"""
import argparse
import re
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = 'https://raw.githubusercontent.com/callmesevda/KR-Project/main/'
PEXT = Namespace(RAW + 'test/proto-text-extension.ttl#')
T = Namespace(RAW + 'test/text_kg.ttl#')


def load(kg_dir):
    g = Graph()
    for f in [kg_dir / 'proto-ontology-structure.ttl', kg_dir / 'proto_data.ttl',
              HERE / 'proto-text-extension.ttl', HERE / 'text_kg.ttl']:
        g.parse(f, format='turtle')
    return g


def parse_queries(path):
    text = path.read_text(encoding='utf-8')
    blocks = re.split(r'^#### ', text, flags=re.M)[1:]
    prefixes, queries = '', []
    for b in blocks:
        head, _, body = b.partition('\n')
        if head.strip() == 'PREFIXES':
            prefixes = body
            continue
        qid, _, question = head.partition('|')
        queries.append((qid.strip(), question.strip(), body.strip()))
    return prefixes, queries


def short(v):
    s = str(v)
    for ns, p in [(RAW + 'proto-ontology-structure.ttl#', 'proto:'), (RAW + 'proto_data.ttl#', 'kg:'),
                  (RAW + 'test/proto-text-extension.ttl#', 'pext:'), (RAW + 'test/text_kg.ttl#', 'text:')]:
        s = s.replace(ns, p)
    s = s.replace('|', '\\|').replace('\n', ' ')
    return s if len(s) <= 140 else s[:137] + '...'


def inconsistencies(g):
    """OWL 2 RL closure, then look for the classic contradictions."""
    import owlrl
    c = Graph()
    for t in g:
        c.add(t)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(c)
    found = []
    err = Namespace('http://www.daml.org/2002/03/agents/agent-ont#')
    for m in c.subjects(RDF.type, err.ErrorMessage):
        found.append('reasoner error: ' + short(c.value(m, err.error)))
    for s in c.subjects(RDF.type, OWL.Nothing):
        found.append(f'{short(s)} is inferred to be owl:Nothing')
    for a, b in c.subject_objects(OWL.sameAs):
        if a != b and (a, OWL.differentFrom, b) in c:
            found.append(f'{short(a)} and {short(b)} must be the same AND different')
    for s in set(c.subjects(RDF.type, None)):
        types = set(c.objects(s, RDF.type))
        for dl in c.subjects(RDF.type, OWL.AllDisjointClasses):
            members = set(Graph.collection(c, next(c.objects(dl, OWL.members))))
            both = types & members
            if len(both) > 1:
                found.append(f'{short(s)} is in disjoint classes {sorted(short(x) for x in both)}')
    return sorted(set(found))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kg-dir', type=Path, default=ROOT)
    args = ap.parse_args()

    g = load(args.kg_dir)
    prefixes, queries = parse_queries(HERE / 'queries.rq')
    out = ['# Query results', '',
           f'Graph: schema + main knowledge graph + text extension + text graph = **{len(g)} triples**.', '']
    for qid, question, body in queries:
        res = list(g.query(prefixes + '\n' + body))
        vars_ = [str(v) for v in g.query(prefixes + '\n' + body).vars]
        out += [f'## {qid} — {question}', '', f'{len(res)} row(s).', '']
        if res:
            out.append('| ' + ' | '.join(vars_) + ' |')
            out.append('|' + ' --- |' * len(vars_))
            for row in res:
                out.append('| ' + ' | '.join(short(v) if v is not None else '' for v in row) + ' |')
            out.append('')
        print(f'{qid}: {len(res)} rows')

    out += ['## Reasoner check (OWL 2 RL, owlrl)', '']
    problems = inconsistencies(g)
    out.append(f'Real data: **{len(problems)} inconsistencies**.' if not problems
               else 'Real data: inconsistencies found:\n\n' + '\n'.join(f'- {p}' for p in problems))
    print('reasoner, real data:', len(problems))

    proto = Namespace(RAW + 'proto-ontology-structure.ttl#')
    tests = [
        ('Occ_T4_1 is given a second stance (`pext:Warning` next to `pext:Positive`). '
         '`hasStance` is functional and the six stances are declared all different.',
         (T['Occ_T4_1'], PEXT.hasStance, PEXT.Warning)),
        ('Occ_T7_1 is also typed as a `proto:Proverb`. ProverbOccurrence and Proverb are declared disjoint.',
         (T['Occ_T7_1'], RDF.type, proto.Proverb)),
    ]
    out += ['', 'Tests with deliberate errors (each added alone to a copy of the graph):', '']
    for i, (desc, triple) in enumerate(tests, 1):
        bad = Graph()
        for t in g:
            bad.add(t)
        bad.add(triple)
        found = inconsistencies(bad)
        out += [f'{i}. {desc}', ''] + [f'    - detected: {p}' for p in found] + (['    - not detected'] if not found else []) + ['']
        print(f'reasoner, error test {i}:', len(found))

    (HERE / 'query_results.md').write_text('\n'.join(out) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
