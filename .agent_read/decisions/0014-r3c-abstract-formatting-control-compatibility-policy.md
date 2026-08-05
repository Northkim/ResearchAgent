# ADR 0014: R3C Abstract Formatting-Control Compatibility Policy

- **Status:** Accepted
- **Date:** 2026-08-05
- **Scope:** Experimental R3C OpenAlex Proxy abstract reconstruction only
- **Governing decisions:** ADR 0009, ADR 0010, ADR 0011, ADR 0012, and ADR 0013

## Context

R3C-A-R3 made one owner-authorized OpenAlex call. The response returned HTTP
200 and exact 1,000-microusd cost evidence. One Work normalized before the next
Work failed at `ABSTRACT_RECONSTRUCTION`, approved path
`/results/*/abstract_inverted_index`, record index `1`, nested token index `2`,
observed kind `CONTROL_CHARACTER`, and validator `ABSTRACT_TOKEN_CONTROL`.
Strict complete-response failure correctly discarded the whole result. The
value-free diagnostic did not retain the Provider token or its exact code
point.

TAB, LF, and CR are formatting whitespace that can occur inside an inverted-
index token without changing its textual meaning when represented by a word
boundary. Treating those three characters as spaces is a narrower compatibility
rule than broad control-character deletion or sanitization. Every other field
and every other control/format character remains governed by the existing
fail-closed policy.

## Decision

### 1. Abstract-only formatting normalization

Only string keys used to reconstruct
`/results/*/abstract_inverted_index` receive this preprocessing:

- U+0009 HORIZONTAL TAB becomes U+0020 SPACE;
- U+000A LINE FEED becomes U+0020 SPACE;
- U+000D CARRIAGE RETURN becomes U+0020 SPACE.

Within one token, each contiguous run made from ASCII SPACE and those three
formatting controls collapses to one U+0020 SPACE when the run contains at
least one formatting control. A run containing only pre-existing ASCII spaces
is unchanged. Existing outer trimming and deterministic position-ordered
reconstruction then apply. Non-control characters retain their order, word
boundaries are not concatenated, and the reconstructed text contains none of
the three permitted formatting controls.

### 2. Continued rejection

Abstract tokens still reject U+0000 through U+0008, U+000B, U+000C, U+000E
through U+001F, U+007F, and every other control/format character rejected by
the current Unicode-category policy. The failure remains:

```text
stage = ABSTRACT_RECONSTRUCTION
path = /results/*/abstract_inverted_index
observed kind = CONTROL_CHARACTER
validator = ABSTRACT_TOKEN_CONTROL
```

Work IDs, DOI, titles, author fields, venue/source, language, and every other
field receive no compatibility preprocessing. Their existing control-character
behavior is unchanged.

### 3. Strict complete-response policy

`R3C_RECORD_LEVEL_POLICY = STRICT_COMPLETE_RESPONSE_FAILURE` remains binding.
Any Work that still fails causes the complete operation to fail without a
partial normalized body, skipped record, quarantine, rejected-record payload,
or warning-bearing success.

### 4. Contract and persistence non-change

The public request/response/status schemas, Provider request mapping, selected
fields, operation ID, request-content checksum, SQL/ORM schema, migrations,
query retention, raw-body retention, credential handling, cost accounting,
idempotency, reconciliation, diagnostic schema, Package format, and Progress
Report contract are unchanged. Existing normalized response checksum
construction is unchanged and naturally reflects the corrected normalized
text. The approved selected-Work metadata checksum continues to cover the
selected Provider mapping without retaining a raw body.

### 5. Gate boundary

This decision authorizes implementation and fictional offline qualification
only. It authorizes no Provider call, key read, external documentation request,
production deployment, or R3D work. Any future live acceptance requires fresh
owner authorization and all live source, credential, cost, isolation, privacy,
restart, Package, and cleanup gates.

## Consequences

- Synthetic responses structurally corresponding to the R3C-A-R3 failure path
  can normalize TAB/LF/CR abstract-token formatting without losing word
  boundaries.
- Accepted formatting controls emit no structural diagnostic; prohibited
  controls retain the same specific value-free diagnostic.
- The exact R3C-A-R3 code point remains unknown because privacy-safe evidence
  intentionally retained only its structural category.
- No real OpenAlex response has passed after this remediation; R3C remains
  `LIVE_ACCEPTANCE_PENDING`.
- Retry 1 remains unexplained, and production/R3D remain closed.

## Alternatives considered

- Deleting all control characters was rejected because it can concatenate
  words, remove arbitrary data, and weaken the security boundary.
- Applying whitespace normalization to titles, authors, venue, language, DOI,
  or identifiers was rejected because the evidence and owner policy authorize
  only abstract tokens.
- Partial success or record quarantine was rejected by ADR 0013 and remains
  outside the public and persistence contracts.
- Retaining the live raw response or abstract token for diagnosis was rejected
  because it violates the established minimization and append-only evidence
  boundary.
