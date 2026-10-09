# Testing PROTO on real texts

Polyxeni Chasanai, October 2026

This folder is our answer to point 6 of the professor's feedback: *test the ontology by extracting proverbial knowledge/bias as knowledge graphs from a few texts (blogs, news, chats), using the ontology as a lens.*

We took nine real texts where proverbs from our corpus are used, described each use with PROTO, and looked at what the ontology could and could not capture. In short: PROTO is good at saying which proverb is used and which lesson it carries, but it has no way to say who the proverb is aimed at or what attitude the speaker takes. Those are exactly the things that show bias, so we wrote a small extension module for them.

## The texts

| ID | Type | Lang | Source | Proverb | Applied to |
|----|------|------|--------|---------|------------|
| T1 | news | en | [ABC News, 14 Jun 2020](https://abcnews.com/US/bad-apples-phrase-describing-rotten-police-officers-meaning/story?id=71201096) | "a few bad apples" (new, PRV-101) | police officers |
| T2 | news analysis | en | [The Conversation](https://theconversation.com/police-violence-in-the-united-states-what-lies-behind-the-bad-apples-narrative-139931) | "bad apples" (PRV-101) | police officers |
| T3 | blog | en | [Upfort](https://www.upfort.com/blog-articles/no-more-weakest-links-why-every-employee-needs-cybersecurity-protection) | A chain is only as strong as its weakest link (PRV-012) | employees |
| T4 | blog | en | [HRZone, 26 Jun 2012](https://www.hrzone.com/talent/development/blog-still-waters-run-deep-never-underestimate-an-introvert) | Still waters run deep (PRV-008) | introverts at work |
| T5 | forum | en | [WordReference, 2007](https://forum.wordreference.com/threads/still-water-runs-deep.448648/) | Still waters run deep (PRV-008) | quiet people |
| T6 | opinion | sq | [Gazeta Tema, 3 Mar 2015](https://www.gazetatema.net/web/2015/03/03/historia-e-te-forteve-ne-politike-ose-cfare-te-mbjellesh-do-korresh) | Ç'të mbjellësh, do të korrësh (PRV-033), used twice | politicians in power / the government's reforms |
| T7 | social media | it | [Agenzia Stampa Italia, 9 Aug 2026](https://agenziastampaitalia.it/politica/politica-nazionale/74957-migranti-casini-avviso-ai-naviganti-chi-semina-vento-raccoglie-tempesta) (Instagram post by P.F. Casini) | Chi semina vento, raccoglie tempesta (PRV-023) | European migration policy |
| T8 | editorial | it | [Quotidiano di Sicilia, 14 Nov 2024](https://qds.it/chi-semina-vento-raccoglie-tempesta/) | Chi semina vento, raccoglie tempesta (PRV-023), used twice | politicians / citizens |
| T9 | personal blog | fa | [blogfa](https://nahidkhirolahi.blogfa.com/post/199) | دوستی خاله خرسه (PRV-002) | well-meaning friends |

That gives 11 occurrences in total, because T6 and T8 each apply the same proverb to two different targets. Quotes, speakers and our annotations are in `texts.json`.

## How we did it

1. We annotated every occurrence by hand: which proverb, applied to whom, by whom, with what stance, and a short description of the situation.
2. `build_text_kg.py` turns these annotations into `text_kg.ttl`. The file imports the PROTO schema and the main knowledge graph, so it points to the existing individuals (`kg:PRV-008`, `kg:GroupVulnerability`, ...) instead of copying them.
3. With core PROTO, each occurrence becomes a new `SituationOfUse` attached to the proverb through `usedIn`. Everything PROTO can't express goes into the extension (see below).
4. `run_queries.py` runs the queries in `queries.rq` together with an OWL 2 RL reasoner. Its output is saved in `query_results.md`.
5. `extract_baseline.py` checks whether the proverbs could have been found automatically.

## What worked

All 11 occurrences fit the existing model. Every one of them maps onto one of our six tacit lessons, so we didn't need a new lesson.

One proverb was missing from the corpus: "a few bad apples", the short form of "one bad apple spoils the barrel". We added it as PRV-101 under *Group vulnerability*, with a new source domain *Apple* (wd:Q89). We also linked it to the Albanian PRV-031 ("Një dele e zgjebosur prish gjithë tufën") as `SameLessonDifferentImage`, and this time `annotatedBy` is filled in.

Two texts also back up findings from the cross-cultural review:

- **Still waters run deep.** T4 uses it as praise. In T5, though, forum users disagree about it, and one of them counted 5 negative, 2 positive and 3 unclear uses in a corpus. So the English proverb is not as purely positive as our data says, and in practice it overlaps with the Albanian "Uji i qetë të mbyt". This supports the review's point that proverbs should be compared by situation of use, not just by image.
- **Aunt Bear.** T9 confirms that the Persian proverb is about a foolish friend whose help does harm. That is the sub-lesson the review had identified.

## What was missing, and the extension

| Missing in PROTO | Example from the texts | Added in `proto-text-extension.ttl` |
|---|---|---|
| the text and its type | T7 is an Instagram post, T5 a forum thread | `Text`, `hasGenre` (News, Opinion, Blog, Forum, SocialMedia) |
| who is speaking | T6: the journalist vs. the Prime Minister | `speaker` |
| who the proverb is aimed at | T1 police officers, T3 employees | `Target`, `SocialGroup`, `appliedTo` |
| the speaker's attitude | T1 plays the problem down, T2 criticises that use | `Stance` (6 values), `hasStance` |
| a meaning different from ours | T1, T6 | `hasMeaningShift` |
| several uses in one text | T8 targets politicians and citizens | `ProverbOccurrence`, `quote` |

`ProverbOccurrence` is tied back to PROTO through `inSituation`, which points to a `SituationOfUse`. We followed the same modelling rules Saba used for the schema: the new classes are disjoint from each other and from the PROTO classes, `Stance` and `Genre` are closed lists (`oneOf` + `AllDifferent`), and `occurrenceOf`, `occursIn` and `hasStance` are functional.

The extension is a separate module and a proposal. It does not change the main schema.

## Can the proverbs be found automatically?

We tried two simple extractors. The first looks for the proverb text exactly as it is stored in `proto:hasText`. The second looks for key words instead. We compared both against our hand annotation (9 text/proverb pairs) and added two decoy sentences that use proverb words without containing a proverb.

| Method | Found | Correct | Recall | Missed |
|---|---|---|---|---|
| exact text from the graph | 6 | 6 | 0.67 | "a few bad apples" (T1, T2), "ka mbjellë reforma ... për të korrur" (T6) |
| key words | 9 | 9 | 1.00 | none |

Neither method produced false positives. The main lesson is that people rarely quote a proverb exactly: they shorten it, inflect it or split it across a sentence. The key-word result is too optimistic, though, because we wrote the key words after reading these texts, so it would need to be tested on new ones. Neither method can tell who the proverb is aimed at or with what attitude, and those were the most interesting parts of the annotation.

## Bias: what the queries show

TQ2 lists the lessons that are applied to whole groups of people, and TQ4 lists the proverbs used with more than one stance.

- **The same phrase can defend or accuse.** "One bad apple" used to mean that one bad member spoils the whole group. In T1, US officials say "a few bad apples" to argue the opposite: the police as a whole are fine, and the problem is a few individuals, "not systemic racism". T2 criticises exactly this use. In the graph, this shows up as one proverb with two stances, minimising and critical, aimed at the same group.
- **A warning can be turned into a promise.** In T6 the journalist uses sow/reap as a warning to people in power, while the Prime Minister uses the same image to promise that today's reforms will pay off.
- **Proverbs let people blame without naming anyone.** T3 makes "employees" the weakest link in order to sell a security product. T7 warns about "whoever sows wind" in the migration debate, but leaves the reader to work out who that is.
- **Karma proverbs show up in politics.** Four of the five Karma occurrences are warnings to politicians, governments or citizens. The fifth is the Prime Minister's promise in T6.

## Checks

- **SPARQL checks V1–V4** find nothing wrong: no proverb without a lesson, no link between two proverbs of the same language, no non-FalseFriend link across lessons, and no occurrence without a stance or target. These checks are needed because OWL can't detect missing values (open world).
- **Reasoner on the real data:** no inconsistencies.
- **Reasoner on two deliberate errors**, each added alone to a copy of the graph:
  - giving an occurrence two stances is caught (functional property + AllDifferent);
  - typing an occurrence as a Proverb is caught (disjoint classes).
- **CQ1–CQ8** now use the new IRIs and language codes (`it`, `sq`) and return the same answers as before. The only difference is that CQ1 counts one more `SameLessonDifferentImage` link (44 instead of 43) when the text graph is loaded, because of the new PRV-101 to PRV-031 link.

## Limitations

- Nine texts are enough to test the model, but not to say anything about how often a proverb is used.
- The annotation was done by one person. The stance labels are a judgement call, and a second annotator would make them stronger.
- The Persian text (T9) and the Italian texts (T7, T8) should be double-checked by native speakers.
- Two other sources we wanted to use couldn't be accessed (one returned 403, the other 404), so we replaced them.

## Running it

```
pip install rdflib owlrl pandas openpyxl
python test/build_text_kg.py       # texts.json -> text_kg.ttl
python test/extract_baseline.py    # -> extraction_results.json
python test/run_queries.py         # queries + reasoner -> query_results.md
```

## Files

- `texts.json`: the texts, quotes and hand annotations
- `proto-text-extension.ttl`: the extension module
- `build_text_kg.py`, `text_kg.ttl`: builds the text graph, and the graph itself
- `queries.rq`: CQ1–CQ8, checks V1–V4 and text queries TQ1–TQ5
- `run_queries.py`, `query_results.md`: runs the queries and the reasoner, and the output of the last run
- `extract_baseline.py`, `extraction_results.json`: the extraction test and its results
