# Multilingual Search Failure Analysis

Phase 9B-2C-1 status: safe future diagnostics implemented; historical details
remain unavailable. The validation limits below were not relaxed.

Topic: `nonenglish-chinese-digital-humanities`  
Evidence date: 2026-07-29  
No live search or candidate regeneration was performed.

## Observed evidence

- Frozen query: `中国 数字人文 文本分析`.
- OpenAlex provider returned one record.
- Zero records normalized; one record was rejected.
- Retained safe diagnostic:
  `record[0] rejected: provider text exceeds the safe length limit`.
- The topic remains in the pilot with zero reviewable candidates.
- No raw response or full rejected field is retained.

## Current normalization boundaries

Repository inspection found these applicable OpenAlex adapter limits:

| Field/path | Configured maximum |
|---|---:|
| title/display name | 500 characters |
| author display name | 300 characters |
| ORCID | 50 characters |
| venue display name | 500 characters |
| abstract inverted-index token | 200 characters |
| reconstructed abstract | 50,000 characters |
| abstract position | less than 10,000 |

The shared text validator emits the same generic message for multiple fields. The
retained artifact records neither field name nor measured length. Therefore:

> The exact rejected field and exact triggered limit are not recoverable from
> retained Phase 9B-2B-1 evidence.

Naming a field would fabricate evidence. This is a diagnostic-observability gap,
not a reason to loosen the safety boundary.

## Cause assessment

| Possible cause | Evidence-based assessment |
|---|---|
| Provider coverage | Indeterminate. One result from one bounded query cannot establish OpenAlex Chinese recall or lack of coverage. |
| Query construction | Plausible contributor. The V1 exact term-level query has no explicit Chinese synonyms, English pivot, or bilingual variant. No comparative search was run. |
| Local validation | Confirmed immediate cause of the empty normalized pool: the only returned record was rejected at an existing field-length boundary. |
| Metadata shape | Plausible contributor because a provider text field exceeded one adapter limit, but the current diagnostic cannot identify which field or whether it was malformed. |
| Overall | Combination of a narrow single-query plan and confirmed local rejection; provider coverage remains unmeasured. |

## Is the limit reasonable?

The boundaries are defensible safety controls against unexpectedly large
third-party strings, control-character abuse, logging exposure, and artifact
inflation. The available evidence is insufficient to determine whether the
specific triggered field's threshold was too strict because that field and
length were not recorded. The abstract-level 50,000-character cap is already far
larger than the 500-character evaluation preview. The correct next action is
field-specific safe diagnostics and fixture testing, not relaxation.

## Later implementation test plan

No test below authorizes a live call in this phase.

1. Add field-aware validation errors containing field name, measured length,
   unit, configured limit, and boundary version; exclude full content.
2. Add network-free fixtures for every text boundary at limit-1, limit, and
   limit+1, including Chinese Unicode, combining characters, emoji, bidirectional
   controls, NUL/control characters, overlong title/venue/author/ORCID, overlong
   abstract token, excessive abstract reconstruction, and invalid positions.
3. Verify logs/artifacts contain only a short safe fragment or hash and no full
   rejected content.
4. Replay a sanitized, synthetic equivalent of the failure through the adapter;
   do not reconstruct or fabricate the missing real record.
5. Implement explicit approved query variants and mock separate provider
   responses to test provenance, exact DOI/ID merge, advisory title/year cluster,
   bilingual conflicts, and zero-result visibility.
6. After owner approval in a later milestone, execute each approved variant
   independently under the existing provider budget and compare per-variant
   result/rejection diagnostics.
7. Review any field-limit changes as a separate security decision supported by
   observed distributions; do not alter the gate merely to populate this topic.

## Phase 9B-2C-1 result

The adapter now emits `FieldRejectionDiagnostic/v1` for future rejected values:

- rejection category;
- field name;
- normalized measured character length;
- configured character limit;
- safely available OpenAlex Work ID;
- SHA-256 of the rejected normalized value;
- normalized, control-free, secret-redacted preview capped at 80 characters;
- preview length;
- adapter and validator versions.

Full rejected values and raw HTTP bodies are not retained. Control characters
and invalid Unicode receive distinct typed diagnostics. The validator still
rejects over-limit values; observability did not change admissibility.

The Phase 9B-2B-1 event predates this schema. Its representation remains
`details_available: false` with the reason that field name, measured length,
and configured limit were not recorded. No source field, length, limit, content,
or replacement candidate was reconstructed.

Cause attribution is unchanged: local validation is the confirmed immediate
cause; query construction and metadata shape are plausible contributors;
provider coverage is indeterminate from one bounded query.

### New supervised observation

The separate Phase 9B-2C-1 live evaluation
`openalex-chinese-multilingual-v1-live` supplied future evidence under the new
schema:

- original Chinese variant: one received, zero normalized, one rejected;
- manual Chinese synonym: zero received;
- English pivot: 20 received and normalized from one bounded page;
- manual bilingual conjunction: zero received;
- merged: 20, all with declared language `en`;
- zero exact merges and zero title/year advisory clusters.

The new rejection identified `abstract_inverted_index.token`, normalized length
324, configured limit 200. That is a new observation, not a reconstruction of
the old artifact. It shows the safety gate and diagnostic work as designed; it
does not establish that the same field/value caused the historical failure,
that the rejected paper was relevant, or that English-pivot results improve
scientific retrieval quality.

## Required reporting

The current report must keep:

- one provider result;
- zero normalized/reviewable candidates;
- one generic length-boundary rejection;
- exact-field/length diagnostic unavailable;
- no retrieval-quality conclusion;
- no fabricated replacement candidate.
