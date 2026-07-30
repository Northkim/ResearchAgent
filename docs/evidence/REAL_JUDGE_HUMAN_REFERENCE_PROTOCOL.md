# Real Judge Human Reference Protocol

Protocol version: `reagent-real-judge-human-reference/v1-proposed`
Status: Proposed; no reviewer is assigned and no label is authorized

## Task shown to reviewers

> Based only on the stated research topic, paper title, and bounded abstract
> preview, does the paper topically address the topic?

Use the existing five-label rubric:
`HIGHLY_RELEVANT`, `RELEVANT`, `PARTIALLY_RELEVANT`, `NOT_RELEVANT`, or
`CANNOT_JUDGE`.

Reviewers must not assess correctness, methodology, credibility, novelty, venue,
citations, truth, causal validity, or scientific merit. Codex and the automated
Judge cannot serve as human reviewers.

## Blinding and display

Display:

- topic ID and description;
- optional research question and inclusion/exclusion rubric;
- title;
- bounded abstract preview, original language;
- a machine-translation notice and separate text only if separately authorized;
- minimal year/venue metadata if included in the Judge request;
- metadata-warning badge without hidden rejected content.

Hide:

- OpenAlex/provider rank;
- deterministic ranking score;
- citation count;
- author prestige;
- provider relevance score;
- DOI unless identity resolution is required outside the labeling screen;
- Judge provider/model, output, confidence, spans, or reason;
- another reviewer's label until the current independent label is locked.

## Minimum-burden reference design

1. One primary human reviewer independently labels all 12 real calibration
   candidates before any Judge result is shown.
2. One secondary checker independently labels:
   - all four non-English candidates;
   - every primary `CANNOT_JUDGE` or low-confidence/uncertain item;
   - every item later disputed by the Judge;
   - a deterministic 25% sample of the remaining English items, with at least
     one from each English topic.
3. If labels agree, lock the reference.
4. If labels disagree, the two reviewers see both rationales and resolve to one
   label or `CANNOT_JUDGE`. Record the resolution reason. If they cannot resolve,
   retain `UNRESOLVED` and exclude that item from a single-label agreement
   denominator while reporting it as a calibration warning.
5. Only after the human-reference file is locked may Judge output be revealed
   for comparison.

Expected secondary burden is at least six items: four multilingual plus two
sampled English items, with more added for uncertainty or Judge disagreement.
This is **Proposed Class D policy**. Rationale: full independent dual review of
all 12 would provide a cleaner inter-rater estimate but doubles effort; targeted
checking preserves multilingual and ambiguity safeguards. Alternatives are
single review only (too weak) or dual-independent review of all 12 (preferred
for a publishable benchmark, higher burden). Tradeoff: most English reference
labels reflect one non-expert reviewer. Owner approval and reviewer assignment
are required. Revisit if primary uncertainty/disagreement exceeds 25%, if the
evaluation is used publicly, or if an expert-gold claim is contemplated.

## Reviewer record

Each private, ignored label record contains:

- evaluation ID, topic ID, pseudonymous candidate ID;
- candidate checksum and rubric/prompt-freeze checksum;
- reviewer pseudonym;
- label;
- confidence on a descriptive 0–1 scale;
- short topical-relevance reason;
- supporting span from the supplied preview or an explicit no-evidence reason;
- language/translation status;
- reviewed_at;
- record checksum and schema version.

No public or committed file may contain real title/preview text. The label record
references the candidate checksum; it does not duplicate the full preview.

## CANNOT_JUDGE

Use `CANNOT_JUDGE` when title/preview is insufficient, not as a substitute for
reviewer unfamiliarity with a method or disagreement about scientific quality.
A resolved CANNOT_JUDGE is a valid reference outcome and must route the item to
human audit in any later silver workflow.

## Human/Judge comparison

- compare the Judge to the locked human-reference label, never to a label shown
  after the Judge;
- preserve raw A/B outputs even when a human overrides;
- calculate exact and adjacent agreement separately;
- report human-human disagreement and unresolved count;
- do not call a primary-only or resolved label “gold”;
- do not infer that a human agreement threshold demonstrates expertise.

## Completion

Human-reference collection is complete only when all 12 primary labels are
locked, required secondary checks are complete, every disagreement is resolved
or explicitly unresolved, checksums verify, and no reviewer was exposed to
Judge output before locking.

