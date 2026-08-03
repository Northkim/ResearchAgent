# Real Grounded Report Hosted Data Policy

Original proposal: 2026-07-30
Provider-retention revalidation: 2026-08-03
Status: **Proposed engineering/data-governance assessment; not legal advice**

## Minimum hosted payload

Only the following fields may be sent after explicit owner approval:

| Field | Necessity |
|---|---|
| research topic | establishes the synthesis question |
| report language | constrains output language |
| `[P1]`–`[P3]` label | enables deterministic citation binding |
| approved paper title | identifies the work inside the report and preserves its title |
| approved abstract | sole substantive source for summary/evidence |
| publication year | minimal temporal context and reference rendering |
| venue | minimal reference context; not a quality signal |
| abstract-only disclosure | constrains scope and report language |
| prompt instructions and schema | defines the approved task/structure |
| pseudonymous request/paper ID | links normalized response without local identifiers |

Proposed maximum: 12,000 normalized Unicode characters per abstract. The limit
is **Proposed Class D policy**, requires owner approval, and is revisited after
exact token preflight. Values above the limit fail; they are not silently
truncated.

## Excluded by default and future-addition rule

| Excluded field | Why excluded | May it be added later? |
|---|---|---|
| authors | not required for summary grounding or deterministic label binding | only for a separately approved reference-rendering need and revised payload manifest |
| DOI | stable identity is enforced locally; hosted task does not need it | only if a later citation-verification task demonstrates necessity |
| OpenAlex Work ID | provider-specific local identity adds no grounding value | only for a separately approved hosted identity-resolution task |
| source URL | can expose provider/query structure and is not needed by generation | only for an approved citation-verification task with URL/retention review |
| OpenAlex rank | may bias synthesis and is not evidence | no for this acceptance; later use requires a distinct research purpose |
| citation count | not evidence of correctness and may bias language | no for this acceptance; later use requires a distinct research purpose |
| local project/run/database IDs | leak internal topology; pseudonymous request/paper IDs suffice | only if a future audited integration cannot use pseudonyms |
| local paths | machine-specific and unnecessary | no hosted-generation use is anticipated |
| user notes | private project context outside the bounded source set | only through a new consent, minimization, and retention review |
| approval internals/human labels | governance state is enforced locally and may bias output | no for generation; a separate evaluation design would require approval |
| other model outputs | creates hidden provenance and contamination | only when explicitly represented as a checked source in a new contract |
| raw OpenAlex response | contains unnecessary provider fields and potentially more content | no; use normalized approved records only |
| credentials or credential fragments | secret; never model input | never |
| unrelated project content | violates purpose limitation | never within this acceptance |

Adding any conditionally eligible field requires a revised hosted-data manifest
that explains necessity, classification, provider retention, local retention,
and owner approval. It also changes the request checksum and approval boundary.

The JSON schema contains no paper, user, project, or other sensitive data.
Abstract text is untrusted data inside explicit delimiters and cannot override
system instructions.

## Hosted retention choices

### Policy A — confirmed ZDR (recommended and current project policy)

The exact commercial organization, workspace, endpoint, model, structured
output feature, and region are confirmed eligible. Anthropic states that
eligible Messages prompts/responses are not stored at rest after response;
structured-output schemas may be cached for up to 24 hours. Legal-hold and
flagged-content exceptions may apply.

### Policy B — explicitly accepted standard retention

The owner may explicitly accept the provider's then-current standard API
retention and training/data-use contract for this bounded sample. As rechecked
2026-08-03, Anthropic's commercial API policy says inputs/outputs are deleted
within 30 days by default, subject to longer feature-specific, safety-policy,
legal, and contractual exceptions; API inputs/outputs are not used for training
without express permission. This is not currently allowed by
`REAL_REPORT_DATA_RETENTION_POLICY.md`. Selecting Policy B therefore requires
an explicit owner exception and revision/acceptance of ADR 0008 before
execution.

“Not used for training by default” is not equivalent to ZDR. Public availability
of an abstract does not eliminate rights, confidentiality, provider-retention,
or misuse risk.

## Local handling

Proposed Class D terms:

- approved real PaperRecords and SourceContent: 30 days;
- canonical LLM payload and normalized response: 7 days;
- failed partial output: 7 days;
- accepted summaries/evidence/claims/report/corpus: 30 days in the isolated
  acceptance root, then retain only owner-approved content-minimized evidence;
- ProviderOperation/usage/provenance metadata without abstract text: 12 months;
- sanitized logs: 30 days;
- raw HTTP response: never retained.

Prompt/response logging is off. Diagnostics retain category, hashes, counts,
operation/model/request identity, usage and bounded safe messages. They exclude
full prompts, abstracts, response bodies, keys, URLs with credentials, database
URLs, and absolute paths.

No automated retention worker exists. A named owner performs and records
cleanup. Real content and generated reports are never committed to Git.

## Current authorization

No title or abstract transmission is authorized. No ZDR/account configuration
has been confirmed. Policy A or an explicit Policy B exception, abstract rights
approval, exact sample approval, and the payload manifest are blocking.

Official retention evidence accessed 2026-08-03:
[Anthropic API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)
and [commercial API retention](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data).
