# Real Grounded Report Provider Preflight

Date/access date: 2026-07-30  
Status: **Current official evidence; provider use remains unapproved**

## Proposed primary

The proposed primary is Anthropic first-party Claude API with exact model ID
`claude-sonnet-5`. Anthropic documents 4.6-and-later dateless IDs as canonical
fixed model snapshots; the surrounding serving infrastructure may still
change. This is a pinning advantage, not a report-quality claim.

## Current comparison

| Contract | Anthropic `claude-sonnet-5` | OpenAI `gpt-5.6-terra` | Local `gpt-oss-20b` |
|---|---|---|---|
| Exact identity | canonical fixed ID | current model ID; page does not expose a distinct dated slug | pin weights, hash, tokenizer, runtime, quantization and hardware |
| Structure | constrained JSON via `output_config.format`; documented JSON Schema limits | strict structured outputs; documented subset | supported by model, guarantee/runtime operator-owned |
| Context/output | 1,000,000 / 128,000 | 1,050,000 / 128,000 | 128,000 context; output/runtime dependent |
| Sampling | non-default temperature/top-p/top-k rejected | reasoning/sampling controls; no cross-request determinism guarantee | runtime decoding/seed dependent |
| Request/usage | `request-id`; input/output usage | response/request identity and usage | must be built and verified |
| Current price | $2/M input, $10/M output through 2026-08-31; then $3/$15 | $2.50/M input, $15/M output; >272k request surcharge | weights are Apache 2.0; compute and operations are not free |
| Rate/account | organization/workspace tier dependent; Sonnet 5 separate bucket | tier dependent; free unsupported for Terra | capacity/operator dependent |
| Retention | ZDR is agreement- and feature-specific; structured-output schema cached up to 24h | API not trained by default; approved ZDR/data controls account-specific | local policy if genuinely local |
| Region | account/deployment must be confirmed | account/deployment must be confirmed | operator-selected |
| Commercial | current commercial terms; owner remains responsible for inputs | current services terms; owner remains responsible for inputs | Apache 2.0 plus usage policy and runtime licenses |

OpenAI remains evidence context, not an authorized fallback. The local model
remains a privacy/development option, not part of this acceptance.

## Recommended transport boundary

Use a new injected direct-HTTP implementation of the existing
`AnthropicStructuredTransport` protocol backed by the repository's existing
HTTPX dependency. No new dependency is recommended.

The transport should:

- be constructed only in an explicit live backend composition branch;
- receive the secret as a constructor value from that composition boundary;
- POST only to the first-party Messages endpoint;
- send `x-api-key`, the pinned Anthropic API version header, and JSON content;
- disable library-owned retries and let ReAgent enforce its retry budget;
- use explicit connect/read/write/pool timeouts;
- return only normalized structured value, returned model, request ID, usage,
  stop reason, and safe timing metadata;
- never retain or log the raw body;
- classify 400/401/402/403/404 as non-retryable except documented
  contract-specific cases; classify 408/409/429/5xx/connectivity as bounded
  retry candidates;
- treat HTTP 200 `stop_reason: refusal` as a failed/refused result;
- expose cancellation metadata even though remote cancellation may not
  guarantee that billing stopped.

Alternative: the official Python package `anthropic`. If selected later, pin an
exact reviewed release in `environment.yml`, set SDK retries to zero, inject a
controlled HTTP client, and approve the new transitive dependency. The SDK is
well documented but adds supply-chain and hidden-default surface; it is not
needed for the current narrow protocol mapper.

## Preflight checklist

No payload or token-count request may be sent until all checks pass:

1. ADR 0008 accepted for implementation and separately for execution.
2. Exact model ID still current and not deprecated.
3. Current price manifest recorded from official documentation.
4. Account/workspace access, tier, spend limit, and region confirmed.
5. ZDR eligibility confirmed for the exact account, Messages endpoint,
   Sonnet 5, structured outputs, and used features—or an explicit owner policy
   exception revises the current ZDR-only rule.
6. Key exists in the approved secret source and `.env` is ignored; do not print
   or test-read it in documentation.
7. Exact three-paper private manifest approved and checksums verified.
8. Abstract transmission and the 12,000-character cap approved.
9. USD/token/attempt/runtime budgets approved and reservable.
10. Isolated storage and cleanup owner identified.
11. Live flag and endpoint allow-list explicitly enabled for one acceptance.
12. Leakage scan rules active; diagnostics contain no content or key fragments.

## Official source register

| Source | Organization | Update/access | Supported claim | Limitation |
|---|---|---|---|---|
| [What's new in Claude Sonnet 5](https://platform.claude.com/docs/en/about-claude/models/whats-new-sonnet-5) | Anthropic | accessed 2026-07-30 | ID, 1M/128k, sampling restrictions, price, availability, ZDR eligibility | no ReAgent quality or account guarantee |
| [Model IDs and versioning](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions) | Anthropic | accessed 2026-07-30 | 4.6+ canonical IDs are fixed snapshots; infrastructure can change | does not freeze safety/router infrastructure |
| [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) | Anthropic | accessed 2026-07-30 | constrained schema output, limitations, refusal/max-token exceptions, 24h schema cache | schema validity is not semantic grounding |
| [Claude API errors](https://platform.claude.com/docs/en/api/errors) | Anthropic | accessed 2026-07-30 | status classes, request ID, retry guidance, SDK default retries | exact account behavior remains dynamic |
| [Authentication](https://platform.claude.com/docs/en/manage-claude/authentication) | Anthropic | accessed 2026-07-30 | `x-api-key`, `ANTHROPIC_API_KEY`, expiring keys/workload identity | does not approve a key |
| [API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) | Anthropic | accessed 2026-07-30 | organization-specific ZDR, feature eligibility, schema cache, flagged/legal exceptions | contract/account configuration is authoritative |
| [Rate limits](https://platform.claude.com/docs/en/api/rate-limits) | Anthropic | accessed 2026-07-30 | organization tier limits and `retry-after` | actual account tier unknown |
| [Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python) | Anthropic | accessed 2026-07-30 | package, async support, timeouts, two default retries | exact release not selected |
| [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra) | OpenAI | accessed 2026-07-30 | ID, context/output, structured outputs, price and tier limits | no distinct dated snapshot displayed; not a fallback authorization |
| [gpt-oss model card](https://openai.com/index/gpt-oss-model-card/) | OpenAI | 2025-08-05; accessed 2026-07-30 | Apache 2.0, structured outputs, open-weight status | serving/retention/usage contract operator-owned |

## Unresolved account facts

Organization/workspace identity, key scope and expiry, effective rate/spend
tier, ZDR agreement, structured-output eligibility, region, tax, billing
currency, model availability, observed latency, and exact tokenization are not
discoverable from public documentation and block live execution.

