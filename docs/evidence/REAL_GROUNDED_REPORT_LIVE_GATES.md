# Real Grounded Report Live Gates

Date: 2026-07-30  
Status: **Proposed; every numeric value is Class D ReAgent policy**

## A. Preflight blocking gates

- clean owner-reviewed Git baseline and accepted ADR 0008;
- separately approved implementation and execution authorities;
- approved Anthropic account/workspace, `claude-sonnet-5`, region, and scoped
  backend key;
- key source ignored/untracked and leakage scan clean;
- current model availability, price, account tier, and spend limit confirmed;
- ZDR confirmed for exact account/model/endpoint/features, or an explicit
  accepted Policy B exception;
- title/abstract transmission and 12,000-character abstract cap approved;
- exact private three-paper approval/fingerprint/checksums complete;
- USD 1.00, 60k/20k tokens, six calls, eight attempts, one repair, and 15-minute
  policies approved;
- isolated DB/root/journal and 30-day cleanup owner ready;
- live network flag and endpoint allow-list explicitly enabled.

Failure means zero provider calls.

## B. Provider blocking gates

- returned model equals the approved identity;
- structured output validates or uses the one allowed mechanical repair;
- every attempted call has a provider request ID and complete input/output
  usage;
- refusal, max-token, timeout, and provider errors are not treated as success;
- every ProviderOperation is settled or explicitly unresolved;
- no token, attempt, runtime, or monetary cap is exceeded;
- retries remain within the global two-transient-attempt allowance;
- raw provider bodies are not retained.

## C. Grounding blocking gates

- exact approved ordered source set and all checksums match;
- every EvidenceUnit span is a bounded exact substring of approved
  SourceContent;
- every summary/claim/evidence/paper link is known;
- category cardinality and disagreement support rules pass;
- every substantive claim is supported;
- every inference is marked and every gap remains tentative;
- only `[P1]`, `[P2]`, `[P3]` appear;
- no unapproved paper, duplicate identity, or unsupported claim appears;
- abstract-only disclosure and complete 13-artifact set exist;
- report/provenance/corpus/artifact checksums all link.

## D. Product blocking gates

- report is readable and three references render correctly;
- human reviewer finds no material unsupported statement;
- report scope and inference boundaries are conspicuous;
- process restart reloads identical report/provenance/corpus bytes;
- completed replay makes zero generation calls and no new reservation;
- API/artifact reads return verified immutable bytes.

## E. Warnings

Any retry, repair, refusal, provider-side latency spike, missing optional
metadata, weak comparison evidence, human wording concern, or non-blocking
format issue is reported. Runtime above 10 minutes but at or below the
15-minute cap is a proposed warning.

## F. Informational metrics

Tokens, USD cost, latency, operation/attempt counts, summary/evidence/claim
counts, report length, human-review duration, artifact sizes, and reload time
are descriptive only. One acceptance does not measure provider superiority or
statistical reliability.

## Policy rationale and revisit

The 100% identity, citation, evidence, settlement, and checksum requirements
are fail-closed safety invariants for a three-paper report. Numeric envelopes
are bounded engineering choices informed by the synthetic path and official
prices. Alternatives are lower caps/no retries/no repair or deferral.
Tradeoffs are recovery and readability versus exposure, cost, and ambiguity.
All need owner approval and are revisited after any incident, contract/model/
prompt/schema change, human rejection, or proposed broader use.

