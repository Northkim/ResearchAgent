# Real Judge Calibration Data Retention Policy

Policy version: `reagent-real-judge-retention/v1-proposed`
Date: 2026-07-29
Status: Proposed engineering risk assessment, not legal advice

## Authorization boundary

The current owner authorization does **not** permit hosted processing of real
abstract previews. ADR 0005 deferred every real Judge, key, budget, and hosted
adapter. Real calibration is therefore blocked until the owner explicitly
approves the provider/organization, ZDR state, preview processing, length,
region, retention, and deletion plan.

## Minimal hosted request

Permitted only after approval:

- topic description and optional research question;
- inclusion/exclusion rubric;
- paper title;
- at most **500 normalized Unicode characters** of abstract preview, matching
  the current request contract;
- minimal year and venue metadata;
- pseudonymous candidate ID;
- prompt/rubric/schema content.

Explicitly excluded:

- API key in content or artifacts;
- OpenAlex/provider rank or deterministic score;
- citation count;
- full abstract unless a later owner decision changes both contract and policy;
- author names or other personal data unless separately justified;
- DOI or OpenAlex ID;
- raw OpenAlex response;
- another Judge output or human label;
- internal database/run identifiers beyond the pseudonym;
- local paths, credentials, environment values, or unrelated artifacts.

The 500-character maximum is **Proposed Class D policy** and also matches the
current Fake Judge request boundary. Rationale: it limits disclosure while
preserving the architecture-tested input. Alternatives: 300 (less disclosure,
more CANNOT_JUDGE) or 1,000 (more context, more rights/retention exposure).
Owner approval is required. Revisit if CANNOT_JUDGE is driven by truncation or
the request contract changes.

## Hosted-provider requirements

Blocking requirements:

1. A commercial organization/project, not a consumer chat surface.
2. Contractual/console confirmation that the exact Messages/Responses endpoint,
   model, structured-output feature, and region are eligible for Zero Data
   Retention.
3. ZDR enabled for the exact organization/project and verified without printing
   secrets.
4. No Batch, Files, managed agents, web/tool calls, prompt storage, feedback
   sharing, background execution, or third-party integration.
5. No sensitive candidate data embedded in the JSON Schema. Anthropic documents
   a 24-hour compiled-grammar cache distinct from message content.
6. Provider contract rechecked on execution day and recorded by URL/access date.

Anthropic currently states that qualified ZDR Messages requests are not stored
at rest after the response, subject to flagged-content/legal-hold exceptions.
OpenAI currently states that approved ZDR excludes content from abuse logs and
forces `store=false` for Responses/Chat, subject to eligibility and documented
exceptions. These are provider contracts, not guarantees about an unverified
owner account.

If ZDR cannot be confirmed, the hosted calibration does not run. Standard
provider retention is not an automatic fallback.

## Local private retention

All calibration artifacts use an injected ignored root, relative immutable
keys, canonical checksums, and no raw HTTP body.

| Data | Proposed retention | Content rule |
|---|---:|---|
| private manifest | until 14 days after calibration, then delete | IDs/checksums/rationale only; no title/preview |
| canonical request and structured response | 14 days maximum, or 7 days after owner accepts/rejects report, whichever is earlier | private; contains bounded title/preview and short output |
| ProviderOperation journal | 30 days | IDs, state, usage, cost, latency, request ID; no full prompt/response |
| human reference labels | 12 months | pseudonyms, labels, reasons, candidate checksum; no duplicated preview |
| aggregate calibration report | retained with project evidence | no real title/preview; aggregate and pseudonymous results only |
| credentials | never in artifacts | secret store/environment at adapter composition only |

These periods are **Proposed Class D policy**. Rationale: short content
retention permits checksum/replay/audit while limiting third-party text
exposure; longer human-label retention supports later comparison. Alternatives:
ephemeral request/response deletion immediately after report (lower auditability)
or 30-day content retention (higher auditability/exposure). Owner approval is
required. Revisit on rights/terms change, security incident, public release,
new provider, or any need to retain full abstracts.

Deletion must remove request/response/manifest artifacts and any temporary
render/log copies while retaining content-free tombstone checksums where the
artifact contract supports them. Backup, Time Machine, cloud sync, trash, swap,
and crash-dump behavior must be assessed by the owner; this document cannot
guarantee their deletion.

## Prompt, response, and logging

- retain only canonical structured request/response artifacts; no provider raw
  body or streaming transcript;
- logs contain operation ID, provider request ID, status, byte/token counts, and
  hashes, not title/preview/reason/span;
- normalize errors and strip response bodies before logging;
- never print keys or authorization headers;
- supporting spans remain short and private;
- diagnostic scans report leakage yes/no without printing a key fragment;
- prompts treat title/preview as delimited untrusted data.

## Incident and deletion triggers

Stop new calls and notify the owner on key leakage, unexpected provider storage,
wrong model ID/region, full-abstract transmission, unapproved tool use, raw-body
retention, checksum mismatch, or inability to delete expired content. Delete
private content at expiry, owner rejection, rights withdrawal, or incident
response direction. Preserve only the minimum content-free audit record.

## Official evidence

| Source | Organization | URL | Class | Accessed | Claim / limitation |
|---|---|---|---|---|---|
| API and data retention | Anthropic | https://platform.claude.com/docs/en/manage-claude/api-and-data-retention | A | 2026-07-29 | organization-scoped ZDR, feature eligibility, prompt/response handling, schema cache, exceptions; contract/account remains authoritative |
| Data residency | Anthropic | https://platform.claude.com/docs/en/manage-claude/data-residency | A | 2026-07-29 | inference and storage geography are separate; availability is account-dependent |
| Data controls in the OpenAI platform | OpenAI | https://developers.openai.com/api/docs/guides/your-data | A | 2026-07-29 | no-training default, default abuse retention, Responses application state, ZDR and regions; exact project eligibility unknown |
| OpenAlex data retention policy | ReAgent evidence synthesis | `OPENALEX_DATA_RETENTION_POLICY.md` | D/project policy | 2026-07-29 | existing private metadata/abstract boundaries; not legal advice and does not authorize hosted Judge processing |

