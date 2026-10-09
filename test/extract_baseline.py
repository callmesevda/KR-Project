"""Automatic extraction baseline for the text test (point 6).

Question: can proverbs in real texts be found automatically, using only
what the PROTO knowledge graph already contains?

Two extractors are run over the excerpts in texts.json, plus two decoy
sentences that contain proverb words but no proverb:

  A. exact   - looks for the proverb text exactly as stored in proto:hasText
  B. variant - looks for the proverb's key words (stems), so it also catches
               shortened or inflected forms ("a few bad apples",
               "ka mbjellë ... për të korrur")

Results are compared with the hand annotation (gold standard) at the level
of (text, proverb) pairs. Target and stance are not attempted: neither
extractor can recover them, which is itself a result.

Usage:  python test/extract_baseline.py [path/to/proto_data.ttl]
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

from rdflib import Graph

HERE = Path(__file__).resolve().parent
DEFAULT_KG = HERE.parent / 'proto_data.ttl'

# Key-word patterns per proverb (variant extractor). All must match.
VARIANTS = {
    'PRV-002': [r'خاله\s*خرسه'],
    'PRV-008': [r'still waters?', r'runs? deep'],
    'PRV-012': [r'weakest link'],
    'PRV-023': [r'semina\w* vento', r'tempesta'],
    'PRV-033': [r'mbjell', r'korr'],
    'PRV-101': [r'bad apples?'],
}

# Sentences with proverb words but no proverb (false-positive check).
DECOYS = [
    ('D1', 'The apple harvest was bad this year because of the late frost.'),
    ('D2', 'Still water is sold in glass bottles; sparkling water costs more.'),
]


def norm(s):
    s = unicodedata.normalize('NFC', s).lower()
    s = re.sub(r"[^\w\s]", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def corpus_texts(kg_path):
    g = Graph().parse(kg_path, format='turtle')
    q = """SELECT ?id ?text WHERE {
             ?p ?hasID ?id ; ?hasText ?text .
             FILTER(STRENDS(STR(?hasID), "hasProverbID") && STRENDS(STR(?hasText), "hasText")) }"""
    return {str(r.id): str(r.text) for r in g.query(q)}


def run(kg_path=DEFAULT_KG):
    texts = json.loads((HERE / 'texts.json').read_text(encoding='utf-8'))
    corpus = corpus_texts(kg_path)
    docs = [(t['id'], t['excerpt']) for t in texts] + DECOYS
    gold = {(t['id'], o['proverb']) for t in texts for o in t['occurrences']}

    exact, variant = set(), set()
    for tid, excerpt in docs:
        n = norm(excerpt)
        for pid, ptext in corpus.items():
            if norm(ptext) and norm(ptext) in n:
                exact.add((tid, pid))
        for pid, pats in VARIANTS.items():
            if all(re.search(p, excerpt, re.I) for p in pats):
                variant.add((tid, pid))

    def score(found):
        tp = len(found & gold)
        p = tp / len(found) if found else 0.0
        r = tp / len(gold)
        return dict(found=len(found), correct=tp, precision=round(p, 2), recall=round(r, 2),
                    missed=sorted(gold - found), wrong=sorted(found - gold))

    return dict(gold_pairs=len(gold), exact=score(exact), variant=score(variant))


if __name__ == '__main__':
    kg = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_KG
    res = run(kg)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    (HERE / 'extraction_results.json').write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding='utf-8')
