# ADR 0008: Bounded Real Grounded Report Acceptance

Status: **Proposed**
Date: 2026-07-30
Last revalidated: 2026-08-03
Owner: ReAgent owner

## Context

Phase 9C-1 implemented immutable
`guided-literature-review@3.0.0` at
`c103aa95290ed13407cf5fa5e9984bcd9cd0efb7cc5451176b73c6fbcf1cb0ec`
while preserving V2 at
`af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`.
Synthetic validation proved exact approved-source binding, structured
summary/evidence, grounded claims, deterministic citations, fail-closed
publication, 13 immutable artifacts, ProviderOperation replay, and zero-call
completed reconstruction. The Anthropic adapter remains an inactive
transport-injected substrate. Current source inspection also confirms that the
application call boundary rejects configured live-provider names, records V3
generation as non-live with synthetic idempotency identity, and passes a
permissive generic object schema. A transport alone therefore cannot activate
the live path.

ADR 0007 is accepted only for Fake/synthetic implementation. Real provider
activation, credentials, real abstract transmission, spending, and live
acceptance remain unauthorized. The Optional Evaluation Module remains
**DEFERRED**.

## Problem

ReAgent needs one low-risk experiment to determine whether the V3 architecture
can operate with a current hosted model on exactly three real, owner-approved
abstracts. Code acceptance alone does not establish provider structure,
grounding, citations, usage/cost, human readability, or replay under live
conditions.

## Acceptance objective

Validate that one current hosted model generates an abstract-only,
citation-aware, provenance-valid report from exactly three approved papers,
with complete usage, private artifacts, human review, restart, and zero-call
completed replay.

No scientific correctness, systematic-review, full-paper, expert-review,
production-readiness, provider-superiority, multilingual-generalization, or
statistical claim follows.

## Proposed provider and model

Use Anthropic first-party Claude API with exact canonical model ID
`claude-sonnet-5`. Anthropic documents this 4.6+ dateless ID as a fixed model
snapshot, although serving infrastructure can change. It supports constrained
JSON outputs, a 1M context window, 128k maximum output, request IDs, usage, and
an organization-specific ZDR path.

OpenAI `gpt-5.6-terra` and local `gpt-oss-20b` remain evidence alternatives,
not fallback or comparison providers. Provider/model selection remains
unapproved until the owner accepts this ADR and current preflight facts.

## Transport boundary

Implement later an injected direct HTTP transport for the existing
`AnthropicStructuredTransport` protocol using the repository's existing HTTPX
dependency. No new package is proposed. Construct it only at an explicit live
backend composition boundary; inject the key; disable client-owned retries;
normalize identity, request ID, usage, stop state, errors and safe diagnostics;
retain no raw body.

The minimum Phase 9C-2B source change must also add an explicit opt-in live
provider execution policy, mark live ProviderOperations correctly, use a live
idempotency identity, and provide operation-specific supported JSON Schemas at
the existing application boundary. These changes must preserve the immutable
V3 workflow definition and remain disabled in default composition.

The official `anthropic` SDK is an alternative requiring an exact reviewed
version, dependency approval, retries set to zero, and controlled client
injection. No dependency or transport is authorized by this Proposed ADR.

## Three-paper sample

Privately select exactly one central, one complementary, and one contrasting
paper from one approved topic. All must have usable public abstracts, exact
identity uniqueness, no known retraction when metadata is available, and owner
permission for hosted processing. At least two should support a common theme
and agreement; at least two should permit a qualified comparison.

The ignored manifest binds acceptance/run, topic, paper/SourceContent/selected
artifact IDs and checksums, approval fingerprint, deterministic `[P1]`–`[P3]`,
rationale category, abstract-only scope, expiry, schema and checksum. Actual
titles, abstracts, DOI, and OpenAlex IDs do not appear in committed evidence.

## Hosted payload

Include only topic, English report language, citation label, approved title and
abstract, year, venue, abstract-only disclosure, prompt/schema, and a
pseudonymous paper/request ID.

Exclude authors, DOI, OpenAlex ID/URL, rank, citation count, local IDs/paths,
notes, approval internals, human labels, other model outputs, raw OpenAlex
responses, secrets and unrelated content.

Proposed maximum is 12,000 normalized Unicode characters per abstract. Exceeding
it fails preflight; no silent truncation.

## Abstract processing and retention

Current project policy requires **Policy A: confirmed ZDR** for the exact
organization, workspace, endpoint, model and structured-output feature.
Structured-output schemas contain no content and may be cached by Anthropic for
up to 24 hours. Account/feature eligibility, region, flagged/legal exceptions,
and contractual terms require confirmation.

Anthropic's public commercial API policy, rechecked 2026-08-03, describes
standard input/output deletion within 30 days and no training without express
permission, subject to feature, safety, legal, and contract exceptions. That
public policy is not proof of the future account's ZDR or region status.

**Policy B: explicitly accepted standard retention** is an alternative only if
the owner explicitly revises the current ZDR-only policy while accepting this
ADR. Public abstracts still carry rights and governance risk; this is an
engineering assessment, not legal advice.

Proposed local retention: real sources and isolated acceptance environment 30
days; canonical hosted payloads/normalized responses and failed partials 7
days; content-free operation/provenance/usage metadata 12 months; sanitized
logs 30 days; raw HTTP never retained. No automated retention worker exists.

## Report language and content

Generate English while preserving original titles and `[P1]`–`[P3]`.
Prominently disclose abstract-only scope; mark missing data unavailable; keep
source-stated limitation separate from inference; qualify gaps; normally show
paraphrased evidence rather than private spans. Defer Chinese output.

## Proposed call and budget policy

All numbers are **Proposed Class D ReAgent policy**, require owner approval, and
are revisited on any model/price/payload/prompt/retry change:

- exactly three summary/evidence calls;
- one claim synthesis;
- one report composition;
- at most one mechanical repair;
- six logical operations, eight total attempts;
- at most two transient retry attempts globally;
- 60,000 input and 20,000 output tokens across all attempts;
- 15-minute runtime;
- USD 0.75 reservation, USD 0.30 per-operation cap, USD 1.00 hard cap;
- one provider, no fallback/comparison/race/cache-discount assumption.

At current introductory Sonnet 5 price the token envelope is USD 0.32; at
documented standard price it is USD 0.48, before tax/account variation. Current
authorized spend remains **USD 0.00**.

## API-key policy

If later approved, use a scoped backend-only key under the exact variable
`ANTHROPIC_API_KEY`, read only in explicit live composition. `.env` or the
approved secret source must remain ignored/untracked. Never place a key or
fragment in frontend, prompts, logs, diagnostics, fixtures, artifacts, or
documentation. Missing key fails before reservation. This ADR does not
authorize creating or reading it.

## Isolated storage

Use acceptance ID `grounded-report-live-v1`, dedicated database
`reagent_grounded_report_live_v1` if the SQL path is used, isolated ignored
root `runtime_data/acceptance/grounded-report-live-v1/` and its journal, and a
30-day expiry. Never use ProjectDB, prior OpenAlex acceptance databases,
synthetic roots, or production roots. Retain private failure evidence until
review/expiry. Cleanup uses these exact validated names, never placeholders or
globs.

## Human review

One named human reviews all summaries, substantive report statements,
citations, disclosures, themes, agreement/comparison, limitations, gaps,
conclusions and references against the supplied abstracts. Outcomes are
`ACCEPT`, `ACCEPT_WITH_EDITS`, or `REJECT`.

Any substantive edit creates a new immutable report version and requires full
provenance revalidation. Codex/model output cannot be the human decision.

## Blocking and warning gates

Preflight blocks on missing approval/account/model/key/retention/abstract/
sample/budget/storage/network authority. Provider gates require exact model,
valid structure, request IDs, complete usage, settled operations, bounded
retries and no raw-body retention. Grounding gates require exact checksums,
valid spans/support/cardinality/citations/inference/disclosure and complete
linked artifacts. Product gates require human acceptance, readable references,
fresh-process reload, API/artifact reload, and zero-call replay.

Any retry, repair, refusal, high latency, weak comparison, human wording concern
or formatting issue is a warning even if blocking gates pass. Tokens, cost,
latency, counts and review duration are informational.

## Failure policy

Missing authority, price, retention certainty, key, sample or budget means no
call. Authentication/model/permission errors do not retry. Rate/timeout/network
errors may use one bounded retry within the global allowance, but ambiguous
settlement blocks blind retry. One repair may address structure only; invalid
span, unsupported claim, unknown substantive citation, missing usage,
unsettled operation, exhausted cap, artifact failure or human rejection blocks
publication.

Crashes reconstruct settled operations and verified checkpoints. A failed run
is private and never appears completed.

## Proposed Phase 9C-2B sequence

1. Accept/revise owner decisions and grant implementation authority.
2. Implement injected direct HTTP plus network-free tests and opt-in preflight.
3. Create isolated storage and private approved three-paper manifest.
4. Reconfirm model/price/account/ZDR/region and reserve budget.
5. Obtain separate execution and network authority.
6. Execute the bounded V3 call plan.
7. Validate provenance and immutable artifacts.
8. Complete human review.
9. Restart and verify zero-call replay.
10. Record content-minimized evidence, disable live composition, and retain or
    clean by policy.

## Consequences

Positive: minimal real-data exposure, explicit owner control, current provider
evidence, bounded cost, inspectable grounding, and replay evidence.

Negative: account/ZDR setup, direct transport work, synchronous latency,
manual review/cleanup, abstract-rights risk, and one-sample uncertainty.

## Risks

Model/serving drift, structured-output refusal, content hallucination despite
schemas, abstract incompleteness, provider retention/region/account mismatch,
tokenizer/price change, ambiguous timeout billing, no authentication,
filesystem/DB non-atomicity, orphaned private evidence, and overinterpretation
of a single acceptance.

## Revisit triggers

Provider/model/deprecation/price/retention/region change; new dependency;
prompt/schema/workflow change; abstract limit or sample change; any secret,
rights, unsupported-claim, citation, settlement, replay, or human-review
incident; request for Chinese/full-text/full-pool/fallback/production use.

## Owner approvals required

Every blocking response in
`docs/evidence/REAL_GROUNDED_REPORT_OWNER_DECISIONS.md`, plus separate
implementation and execution authorities, is required.

## Explicit exclusions

This Proposed ADR authorizes **none** of the following:

- real API call or live network;
- API key creation, configuration, or reading;
- title or abstract transmission;
- non-zero spend or budget reservation;
- transport implementation or provider activation;
- provider fallback or comparison;
- full text or PDF;
- relevance Judge or candidate-pool screening;
- processing more than the one exact three-paper sample;
- downstream Idea/Writing execution;
- production deployment.
