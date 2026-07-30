# Citation and ResearchReport Contract

Status: **Proposed `ResearchReport/v2`**
Date: 2026-07-30

## Deterministic references

Citation labels are assigned `[P1]`, `[P2]`, … in the immutable approved
selected-paper artifact order. Labels are stable for the input checksum, not
global identifiers. They map to one PaperRecord and cannot be invented by the
LLM.

- In-text substantive statements use one or more adjacent supplied labels.
- References appear once in label order, never in model-chosen order.
- A normalized DOI is rendered as the DOI URL; otherwise use the approved source
  URL/OpenAlex URL; absent links are displayed as unavailable.
- Duplicate normalized DOI blocks input; title similarity never merges papers.
- Unknown/malformed labels, a reference without an approved paper, or a cited
  paper absent from the reference section fails closed.
- Frontend links use only persisted validated reference URLs and safe link
  attributes; model-emitted URLs are ignored.

## Required report sections

1. Title
2. Scope and abstract-only disclosure
3. Search and source-selection methodology
4. Executive summary
5. Selected papers
6. Per-paper summaries
7. Cross-paper themes
8. Agreements
9. Disagreements
10. Limitations
11. Possible research gaps
12. Conclusions
13. References
14. Generation and provenance note

All headings are present for stable parsing. When evidence does not support an
agreement, disagreement, or gap, the section says no supported item was
identified; it is not silently omitted or filled.

## Mandatory disclosure

The report states prominently that it uses owner-approved metadata and
abstracts only; is not a full-text or systematic review; gaps may be
model-assisted inferences; and scientific claims should be verified in the
original papers. It must not claim PRISMA compliance, exhaustive recall, expert
peer review, evidence of scientific correctness, or paper-quality ranking.

## Report object

The structured report records section content, referenced claim IDs,
deterministic CitationReferences, disclosure version, generation language,
report/prompt/provider/model/workflow/skill/schema identities, input/provenance
checksums, timestamps, and validation status. Markdown is rendered from the
validated structure where feasible; the final free-form generation is parsed
and validated against the same claim/citation allow list.

## Publication gate

Publication requires:

1. exact approved paper set and all SourceContent checksums;
2. every summary references a known paper;
3. every EvidenceUnit maps to known SourceContent and a valid span;
4. every substantive claim has valid evidence;
5. every citation maps to one approved PaperRecord;
6. zero unknown citations or unapproved papers;
7. no duplicate DOI;
8. abstract-only disclosure;
9. provider/model/prompt/workflow/skill/schema versions;
10. all ProviderOperations settled;
11. report/provenance/artifact checksums linked both ways;
12. zero unsupported claims;
13. every inference explicitly marked;
14. all immutable artifact writes completed.

Any failure prevents completed/public status. A partial Markdown file may remain
private diagnostic evidence but is never served as the completed report.
