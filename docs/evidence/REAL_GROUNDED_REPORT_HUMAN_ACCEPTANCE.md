# Real Grounded Report Human Acceptance

Date: 2026-07-30  
Status: **Proposed supervised review form**

## Reviewer task

One named human reviewer receives the exact approved topic, three approved
titles/abstracts, validated report, citations, and provenance view. Codex or
another model must not act as the reviewer.

Review every:

- paper summary;
- displayed citation;
- scope/abstract-only disclosure;
- executive-summary statement;
- cross-paper theme;
- agreement;
- disagreement or qualified comparison;
- limitation;
- tentative research gap;
- conclusion;
- reference.

For each substantive statement record:

| Check | Result |
|---|---|
| Citation exists and maps to `[P1]`, `[P2]`, or `[P3]` | pass / fail |
| Cited paper is in the approved set | pass / fail |
| Supplied abstract supports the wording | pass / concern / fail |
| Inference is explicitly labelled | pass / not applicable / fail |
| Wording avoids overstating the source | pass / concern / fail |
| No unknown paper/source appears | pass / fail |

The reviewer also records readability, visible disclosures, reference links,
and review duration. This is product acceptance, not peer review or a
scientific-correctness assessment.

## Outcomes

- `ACCEPT`: no blocking issue and no substantive edit required.
- `ACCEPT_WITH_EDITS`: all source/provenance constraints can be met, but
  substantive wording changes are required.
- `REJECT`: material unsupported statement, unapproved source, missing
  disclosure, misleading synthesis, or other blocking issue.

Recommended V1 edit policy: any substantive edit creates a new immutable report
version, updates its checksum and provenance links, and reruns the complete
publication gate. Editing published bytes in place is prohibited. Cosmetic UI
rendering fixes that do not change artifact bytes may be documented outside the
artifact; ambiguity is treated as substantive.

## Completion

Acceptance is complete only after the signed/pseudonymous review result links
to report/provenance checksums and the fresh-process reload/replay check passes.
Human rejection prevents publication and requires owner review before another
generation attempt or changed sample.

