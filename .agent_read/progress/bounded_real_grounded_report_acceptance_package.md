# Phase 9C-2A: Bounded Real Grounded Report Acceptance Package

Status: **PASS — owner package prepared; no execution authorization**  
Date: 2026-07-30  
Baseline: `ce25c8e feat: add synthetic grounded literature report workflow`

## Scope

This documentation-only phase reverified Phase 9C-1 source and current official
provider contracts, then froze a proposed exactly-three-paper live acceptance.
It did not modify source, workflow, migration, dependency, runtime data or
credentials; did not call any provider/OpenAlex; and did not select, transmit,
or summarize a real paper.

ADR 0007 remains **Accepted with limited implementation scope**. ADR 0008 is
**Proposed**. The Optional Evaluation Module remains **DEFERRED**.

## Verified implementation

- V3 hash:
  `c103aa95290ed13407cf5fa5e9984bcd9cd0efb7cc5451176b73c6fbcf1cb0ec`;
- V2 hash:
  `af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`;
- existing port: `StructuredGenerationProvider`;
- inactive target: injected `AnthropicStructuredTransport` and
  `AnthropicStructuredAdapter` for `claude-sonnet-5`;
- normal V3 composition: `SyntheticGroundedProvider`, no key/network;
- current broad substrate caps: 8 calls, 11 attempts, 90k/32k tokens,
  20 minutes, USD 1.25;
- fail-closed approved-source, operation, provenance, artifact, and replay
  boundaries remain present.

## Proposed live design

Primary remains Anthropic first-party API / `claude-sonnet-5`, unapproved. Use
an injected direct HTTP transport with existing HTTPX rather than adding an SDK.
Exactly three privately approved real abstracts feed three summary/evidence
calls, one claims call, one report call, and at most one repair. Proposed live
caps are six logical operations, eight attempts, 60k input, 20k output, 15
minutes, USD 0.75 reservation and USD 1.00 hard cap. Authorized spend is still
USD 0.00.

Current project policy requires confirmed ZDR. Standard retention is an
alternative only through an explicit owner exception/revision. No title or
abstract transmission is approved.

## Official evidence

Anthropic sources accessed 2026-07-30 confirm the exact canonical pinned ID,
1M/128k limits, structured JSON Schema constraints, request ID/error/retry
contracts, current $2/$10 introductory and $3/$15 standard pricing,
organization-specific ZDR, qualified structured-output schema caching, and
account-dependent rate limits. OpenAI Terra and local gpt-oss facts were
rechecked as alternatives only. Account/workspace/key/tier/ZDR/region/tax and
observed behavior remain unresolved.

## Deliverables

Created the live protocol, owner response table, provider preflight, private
sample protocol, hosted-data policy, cost model, human review, gates, failure
matrix, execution plan, Proposed ADR 0008, and this handoff. Updated the
provider matrix, base cost/retention/gates, evidence register, and compressed
context.

## Validation

Documentation deliverables and status markers were checked; `git diff --check`
passed. Runtime tests were not required or run. Final Git/safety verification
confirmed only documentation changes, ignored `.env`/`runtime_data`, no staged
files, no credential/real paper content, no real API call, and no spend.

## Next permitted milestone

**Owner review: approve or revise ADR 0008 and complete every blocking response.**
Phase 9C-2B implementation or execution is not permitted until those answers
and separate authorities exist.

