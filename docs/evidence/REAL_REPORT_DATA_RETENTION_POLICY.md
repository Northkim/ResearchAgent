# Real Report Data Processing and Retention Policy

Date: 2026-07-30
Status: **Proposed engineering risk assessment; not legal advice**

## Hosted payload

May be sent only after explicit owner permission: topic, run-scoped
pseudonymous paper ID, citation label, approved title, bounded abstract, year,
venue, abstract-only disclosure, rubric, and output schema.

Excluded by default: authors, DOI, OpenAlex ID/URL, local project/database IDs,
rank, citation count, human notes, approval internals, other Judge/model
outputs, raw OpenAlex response, unrelated content, paths, database URL, and
keys. API keys are injected only by composition from one documented server-side
setting and never enter prompts/artifacts/logs/UI.

Abstract input is untrusted data inside typed delimiters. Prompt/response logs
default off. Diagnostics store hashes, IDs, counts, and bounded sanitized error
text—never raw HTTP bodies or full content.

## Hosted retention gate

The first live acceptance requires confirmed ZDR for the exact organization,
project, endpoint, model, and structured-output features. “Not used for
training by default” is not ZDR. Anthropic ZDR is agreement-specific; its
structured-output schema may be cached up to 24 hours, so schemas contain no
paper or user data. If ZDR cannot be confirmed, hosted abstract processing is
blocked pending a new owner decision. Region and subprocessor configuration
must also be recorded.

## Proposed local retention

| Data | Private local retention | Git |
|---|---|---|
| approved PaperRecords and abstracts | 30 days or project deletion, whichever first | never real content |
| canonical LLM request/response payloads | 14 days or acceptance completion + 7 days, whichever first | never |
| failed partial outputs | 7 days | never |
| summaries, EvidenceUnits, claims, report, corpus | 12 months or project deletion | schemas/synthetic fixtures only |
| provenance, generation manifest, usage, ProviderOperations | same lifetime as report (12 months) | content-free examples only |
| human approval metadata | 12 months | no real labels/content |
| sanitized operational logs | 30 days | never live logs |
| isolated acceptance database/artifact root | 30 days after acceptance | never |
| raw HTTP responses | not retained | never |

These are Proposed Class D durations. Alternatives are immediate deletion,
30-day all-content retention, or owner-managed project lifetime. The tradeoff is
replay/audit value against content exposure. Owner approval and abstract-rights
review are required; revisit after the first acceptance, provider-policy
change, deletion tooling, authentication, or deployment beyond trusted
single-user use.

Deletion removes content artifacts and payloads; content-free operation/audit
records may remain only for their approved term. No retention worker currently
exists, so acceptance cleanup is supervised and recorded. The platform has no
authentication; real generation is limited to a trusted, single-user,
supervised environment.

User-visible report/corpus downloads are allowed only if separately approved
and after provenance publication. Access control and multi-user use are
deferred production requirements.

## Phase 9C-2A acceptance refinement

Current policy continues to require **Policy A: confirmed ZDR** for the exact
organization/workspace, Messages endpoint, `claude-sonnet-5`, structured
outputs, and region. **Policy B: explicitly accepted standard retention** is a
possible owner choice only through an explicit policy exception and accepted
ADR 0008; it cannot be inferred from “not used for training.”

The proposed exactly-three-paper acceptance uses a 12,000 normalized
Unicode-character abstract cap per paper and fails rather than silently
truncating. It narrows canonical hosted payload/normalized-response retention
to 7 days and retains the isolated acceptance environment for 30 days. These
are Proposed Class D values. Real title/abstract transmission and either
retention policy remain unapproved.
