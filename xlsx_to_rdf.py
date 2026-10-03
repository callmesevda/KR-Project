import argparse
import itertools
import json
import re
from pathlib import Path

import pandas as pd
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parent
TBOX_DOC = URIRef('https://raw.githubusercontent.com/callmesevda/KR-Project/main/proto-ontology-structure.ttl')
ABOX_DOC = URIRef('https://raw.githubusercontent.com/callmesevda/KR-Project/main/proto_data.ttl')
SCHEMA = Namespace(str(TBOX_DOC) + '#')
DATA = Namespace(str(ABOX_DOC) + '#')
WD = Namespace('http://www.wikidata.org/entity/')
DEFAULT_INPUT = ROOT / 'The Single Source of Truth - Formatted.xlsx'
COLUMNS = ('Proverb ID', 'Language', 'Original Text', 'Literal English Translation',
           'Literal Image (Source Domain)', 'Tacit Lesson (Dropdown)',
           'Situation of Use', 'Literal Image URI', 'Tacit Lesson URI')
CLASSES = ('Proverb', 'SourceDomain', 'SituationOfUse', 'TacitLesson', 'CrossCulturalEquivalence', 'EquivalenceType')
OBJECT_PROPERTIES = ('hasLesson', 'hasSourceDomain', 'usedIn', 'linksProverbA', 'linksProverbB', 'hasEquivalenceType', 'groundedIn')
DATA_PROPERTIES = ('hasText', 'hasTranslation', 'hasProverbID', 'hasLanguage', 'hasLabel', 'hasDivergenceNote', 'annotatedBy')


def pascalize(label):
    return ''.join(w.capitalize() for w in re.findall(r'[A-Za-z0-9]+', label))


def parse_qids(cell):
    result = []
    for token in str(cell).split(','):
        token = token.strip()
        match = re.fullmatch(r'(?:wd:|https?://www\.wikidata\.org/entity/)?(Q[1-9][0-9]*)', token)
        if not match:
            raise ValueError(f'Invalid Wikidata identifier: {token!r}')
        result.append(match.group(1))
    return result


def split_pair(label_cell, uri_cell):
    labels = [x.strip() for x in str(label_cell).split('/')]
    qids = parse_qids(uri_cell)
    if not all(labels) or len(labels) != len(qids):
        raise ValueError(f'Image labels and QIDs must match one-to-one: {label_cell!r} / {uri_cell!r}')
    return list(zip(labels, qids))


def load_rows(path):
    df = pd.read_excel(path, sheet_name='first page', dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    if df.columns.duplicated().any():
        raise ValueError('Duplicate column names')
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}')
    df = df.dropna(how='all').copy()
    if df.empty:
        raise ValueError('No proverb rows')
    for col in COLUMNS:
        df[col] = df[col].fillna('').str.strip()
        if (df[col] == '').any():
            rows = [int(i) + 2 for i in df.index[df[col] == '']]
            raise ValueError(f'Blank required values in {col!r}, Excel rows {rows}')
    if df['Proverb ID'].duplicated().any():
        raise ValueError('Duplicate proverb IDs')
    for pid in df['Proverb ID']:
        if not re.fullmatch(r'PRV-[0-9]+', pid):
            raise ValueError(f'Invalid proverb ID: {pid!r}')
    return df.sort_values('Proverb ID').to_dict('records')


def validate_schema(schema):
    if (TBOX_DOC, RDF.type, OWL.Ontology) not in schema:
        raise ValueError('TBox ontology IRI differs from TBOX_DOC')
    for names, kind in [(CLASSES, OWL.Class), (OBJECT_PROPERTIES, OWL.ObjectProperty), (DATA_PROPERTIES, OWL.DatatypeProperty)]:
        for name in names:
            if (SCHEMA[name], RDF.type, kind) not in schema:
                raise ValueError(f'Missing schema declaration: {name} as {kind}')
    for name in ('DirectMatch', 'SameLessonDifferentImage', 'PartialOverlap', 'FalseFriend'):
        if (SCHEMA[name], RDF.type, SCHEMA.EquivalenceType) not in schema:
            raise ValueError(f'Missing equivalence vocabulary individual: {name}')


def build_graph(rows):
    g = Graph()
    for prefix, ns in [('proto', SCHEMA), ('', DATA), ('wd', WD), ('owl', OWL)]:
        g.bind(prefix, ns)
    g.add((ABOX_DOC, RDF.type, OWL.Ontology))
    g.add((ABOX_DOC, OWL.imports, TBOX_DOC))
    g.add((ABOX_DOC, RDFS.label, Literal('PROTO knowledge graph', lang='en')))
    lessons, domains, row_domains, by_lesson, owners = {}, {}, {}, {}, {}
    proverbs, equivalences = [], []

    def reserve(local, kind, label):
        if not local:
            raise ValueError(f'Cannot create URI from {label!r}')
        owner = (kind, label)
        if local in owners and owners[local] != owner:
            raise ValueError(f'URI collision for {local!r}: {owners[local]} versus {owner}')
        owners[local] = owner
        return DATA[local]

    def individual(uri, kind):
        g.add((uri, RDF.type, OWL.NamedIndividual))
        g.add((uri, RDF.type, kind))

    for row in rows:
        pid, lang = row['Proverb ID'], row['Language']
        proverb = reserve(pid, 'Proverb', pid)
        individual(proverb, SCHEMA.Proverb)
        for prop, value in [(SCHEMA.hasProverbID, pid), (SCHEMA.hasLanguage, lang),
                            (SCHEMA.hasText, row['Original Text']),
                            (SCHEMA.hasTranslation, row['Literal English Translation'])]:
            g.add((proverb, prop, Literal(value)))
        labels = set()
        for label, qid in split_pair(row['Literal Image (Source Domain)'], row['Literal Image URI']):
            labels.add(label)
            if label not in domains:
                uri = reserve(pascalize(label), 'SourceDomain', label)
                domains[label] = (uri, qid)
                individual(uri, SCHEMA.SourceDomain)
                g.add((uri, RDFS.label, Literal(label)))
                g.add((uri, SCHEMA.groundedIn, WD[qid]))
            elif domains[label][1] != qid:
                raise ValueError(f'Inconsistent image QID for {label!r} on {pid}')
            g.add((proverb, SCHEMA.hasSourceDomain, domains[label][0]))
        row_domains[pid] = labels
        situation = reserve(f'Situation_{pid}', 'SituationOfUse', pid)
        individual(situation, SCHEMA.SituationOfUse)
        g.add((situation, RDFS.label, Literal(row['Situation of Use'])))
        g.add((proverb, SCHEMA.usedIn, situation))
        label = row['Tacit Lesson (Dropdown)']
        qids = set(parse_qids(row['Tacit Lesson URI']))
        if label not in lessons:
            uri = reserve(pascalize(label), 'TacitLesson', label)
            lessons[label] = (uri, qids)
            individual(uri, SCHEMA.TacitLesson)
            g.add((uri, SCHEMA.hasLabel, Literal(label)))
            for qid in sorted(qids):
                g.add((uri, SCHEMA.groundedIn, WD[qid]))
        elif lessons[label][1] != qids:
            raise ValueError(f'Inconsistent lesson QIDs for {label!r} on {pid}')
        g.add((proverb, SCHEMA.hasLesson, lessons[label][0]))
        by_lesson.setdefault(label, []).append((pid, lang))
        proverbs.append(dict(id=pid, lang=lang, text=row['Original Text'],
            translation=row['Literal English Translation'], domain=row['Literal Image (Source Domain)'],
            lesson=label, situation=row['Situation of Use']))

    for label, entries in sorted(by_lesson.items()):
        for (a, lang_a), (b, lang_b) in itertools.combinations(sorted(entries), 2):
            if lang_a == lang_b:
                continue
            uri = reserve(f'Equiv_{a}_{b}', 'CrossCulturalEquivalence', f'{a}/{b}')
            individual(uri, SCHEMA.CrossCulturalEquivalence)
            g.add((uri, SCHEMA.linksProverbA, DATA[a]))
            g.add((uri, SCHEMA.linksProverbB, DATA[b]))
            da, db = row_domains[a], row_domains[b]
            if da == db:
                kind = 'DirectMatch'
                note = f"Auto-derived: shared tacit lesson '{label}' AND identical source domain ({', '.join(sorted(da))})."
            else:
                kind = 'SameLessonDifferentImage'
                note = f"Auto-derived: shared tacit lesson '{label}'; source domains differ ({', '.join(sorted(da))} vs {', '.join(sorted(db))})."
            g.add((uri, SCHEMA.hasEquivalenceType, SCHEMA[kind]))
            g.add((uri, SCHEMA.hasDivergenceNote, Literal(note)))
            equivalences.append(dict(a=a, b=b, type=kind, note=note))
    return g, proverbs, sorted(equivalences, key=lambda e: (e['a'], e['b']))


def write_outputs(g, schema, proverbs, equivalences, output):
    turtle = g.serialize(format='turtle')
    check = Graph().parse(data=turtle, format='turtle')
    if set(check) != set(g):
        raise ValueError('RDF serialization round-trip failed')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'proto_data.ttl').write_text(turtle, encoding='utf-8')
    web = output / 'docs/data'
    web.mkdir(parents=True, exist_ok=True)
    (web / 'proto_data.ttl').write_text(turtle, encoding='utf-8')
    (web / 'proto-ontology-structure.ttl').write_bytes((ROOT / 'proto-ontology-structure.ttl').read_bytes())
    stats = dict(rows=len(proverbs), abox_triples=len(g), tbox_triples=len(schema),
        combined_triples=len(schema + g), proverbs=len(proverbs),
        lessons=len(set(g.subjects(RDF.type, SCHEMA.TacitLesson))),
        domains=len(set(g.subjects(RDF.type, SCHEMA.SourceDomain))),
        situations=len(set(g.subjects(RDF.type, SCHEMA.SituationOfUse))),
        equivalences=len(equivalences), direct_matches=sum(e['type'] == 'DirectMatch' for e in equivalences))
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        schema = Graph().parse(ROOT / 'proto-ontology-structure.ttl', format='turtle')
        validate_schema(schema)
        existing = args.output_dir / 'proto_data.ttl'
        if existing.exists():
            previous = Graph().parse(existing, format='turtle')
            if any(str(p).endswith('#annotatedBy') for _, p, _ in previous):
                raise ValueError('Existing output contains human annotations. Use --output-dir for a separate build and preserve the reviewed graph.')
        rows = load_rows(args.input)
        graph, proverbs, equivalences = build_graph(rows)
        stats = write_outputs(graph, schema, proverbs, equivalences, args.output_dir)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Build failed: {exc}\n')
    print(json.dumps(stats, indent=2))
    print('Input checks passed. Semantic accuracy and OWL reasoning are separate checks.')


if __name__ == '__main__':
    main()
