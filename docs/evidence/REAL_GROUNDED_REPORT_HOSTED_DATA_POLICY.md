# Real Grounded Report Hosted Data Policy

Date: 2026-07-30  
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

## Excluded by default

Authors, DOI, OpenAlex Work ID, source URL, OpenAlex rank, citation count, local
project/database/run IDs, filesystem paths, user notes, approval internals,
human labels, other model outputs, raw OpenAlex responses, credentials, and
unrelated project content are excluded. An excluded field may be added only
through a revised data manifest explaining necessity and new owner approval.

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
retention and training/data-use contract for this bounded sample. This is not
currently allowed by `REAL_REPORT_DATA_RETENTION_POLICY.md`. Selecting Policy B
therefore requires an explicit owner exception and revision/acceptance of ADR
0008 before execution.

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

