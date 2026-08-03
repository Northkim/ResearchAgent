# Real Grounded Report Provider Preflight

Original proposal: 2026-07-30
Official-contract and source revalidation: 2026-08-03
Status: **Current official evidence; provider use remains unapproved**

## Proposed primary

The proposed primary remains Anthropic's first-party Claude API with exact
model ID `claude-sonnet-5`. Anthropic documents the canonical dateless ID as a
fixed snapshot, while acknowledging that routing, safety classifiers, and
other serving infrastructure can change. This is a reproducibility advantage,
not a report-quality claim.

Current official facts: 1M context, 128k maximum output, constrained JSON via
`output_config.format`, `request-id`, token usage, introductory $2/$10 pricing
through 2026-08-31 and $3/$15 thereafter, organization-specific ZDR, and a
qualified Structured Outputs rule under which only the content-free schema may
be cached for up to 24 hours. Account/workspace behavior is unresolved.

The complete Anthropic/OpenAI/gpt-oss comparison and current source register
are in `REAL_REPORT_LLM_PROVIDER_MATRIX.md`. OpenAI and gpt-oss are not
fallbacks or comparison providers for this acceptance.

## Current source boundary and minimum Phase 9C-2B changes

Source inspection on 2026-08-03 confirmed the adapter substrate is intentionally
inactive:

- `AnthropicStructuredAdapter` accepts an injected
  `AnthropicStructuredTransport`; it creates no client, reads no environment,
  and retains no raw text.
- `ApplicationContainer` defaults V3 to `SyntheticGroundedProvider` and the
  synthetic paper catalog.
- `_generation_call` explicitly rejects any provider listed as live, writes
  `is_live_provider=False`, uses a `fake:` idempotency prefix, and sends only a
  permissive `{type: object, additionalProperties: true}` schema.
- the accepted source path therefore cannot become live through a transport
  object alone.

The smallest future implementation is additive and requires no workflow,
migration, frontend, or dependency change:

1. Implement one injected HTTPX-backed `AnthropicStructuredTransport` that
   accepts a constructor-supplied secret, exact endpoint/version/model policy,
   explicit connect/read/write/pool timeouts, and cancellation state.
2. Add an explicit live `ProviderExecutionPolicy` at backend composition with
   the approved reservation, six-call/eight-attempt, token, runtime, and USD
   caps.
3. Add a live-authorized branch in the V3 generation service that removes the
   Phase 9C-1 prohibition only when that policy is injected, marks operations
   `is_live_provider=True`, uses a live-scoped idempotency key, and preserves
   reserve/RUNNING/settlement/checkpoint ordering.
4. Freeze an operation-specific provider JSON Schema for summary/evidence,
   synthesis, report, and mechanical repair. Provider schema validity remains
   followed by the existing domain-contract and provenance validators.
5. Map the actual Messages response and headers to normalized structured value,
   returned model, request ID, complete usage, stop/refusal state, retry count,
   latency, and secret-safe error metadata. Do not retain the raw body.
6. Add explicit live composition and a network-free preflight command. Both
   default off and fail closed when any authority or account fact is missing.

## Transport decision

Recommend direct HTTP through the repository's existing HTTPX dependency. Do
not add a dependency in Phase 9C-2A.

The future transport must:

- be constructed only by the explicit live backend composition branch;
- read `ANTHROPIC_API_KEY` only at that boundary and pass it as a constructor
  value, never expose it to Skills;
- POST only to `https://api.anthropic.com/v1/messages` with `x-api-key`, a
  reviewed `anthropic-version`, and JSON content;
- use no HTTP-library retry and let ReAgent enforce the global retry budget;
- expose explicit timeouts and local cancellation metadata; remote/billing
  cancellation is not assumed;
- capture `request-id` even for errors when available;
- return only normalized structured content, model, usage, stop reason, request
  identity, retry/latency, and bounded safe diagnostics;
- recognize HTTP 200 with `stop_reason: refusal` as refusal, not success;
- normalize 400/401/402/403/404/413 as non-retryable unless a reviewed contract
  says otherwise, and treat 408/409/429/500/504/529/connectivity as retry
  candidates subject to ambiguity and global caps;
- never log or persist raw headers/bodies, credentials, abstracts, prompt text,
  or response text.

Alternative: official Python package `anthropic`. If chosen later, the owner
must approve an exact reviewed release and transitive dependency set; pin it
through the repository's Conda policy, set SDK retries to zero, inject its HTTP
client, and verify logging/raw-response behavior. The package is not needed for
the narrow mapper, so the recommendation is **no new dependency**.

## Blocking preflight checklist

No paper title, abstract, or token-count request may be sent until every item
passes:

1. ADR 0008 is accepted or revised, with separate implementation and execution
   authority.
2. Exact model ID remains current, pinned, available, and not deprecated.
3. A dated official price manifest is recorded; currency/tax/regional uplift is
   resolved.
4. Commercial organization/workspace, access, rate tier, spend limit, and
   selected inference region are confirmed.
5. ZDR is confirmed for the exact organization/workspace, Messages endpoint,
   Sonnet 5, Structured Outputs, and used features; alternatively, an explicit
   accepted Policy B exception revises the current ZDR-only rule.
6. A scoped key exists in the approved server-side source. Its value is not
   printed, logged, or read by documentation checks.
7. Exact private three-paper manifest, selected-set approval, and checksums all
   match.
8. Owner permission covers the three titles, three abstracts, and the Proposed
   Class D 12,000-character-per-abstract limit.
9. USD/token/attempt/runtime budgets are approved and reservable under current
   prices.
10. Isolated database/root/journal, retention expiry, cleanup owner, and human
    reviewer are ready.
11. One-run live configuration and egress allow-list are explicit and default
    off.
12. Network-free transport tests, schema fixtures, failure tests, and leakage
    checks pass.

## Secret-safe leakage preflight

These commands inspect tracked/configuration state without sourcing `.env` or
printing a secret value:

```bash
git check-ignore -v .env
git check-ignore -v runtime_data
git ls-files .env runtime_data
git grep -l -I -E 'sk-ant-|sk-proj-|BEGIN PRIVATE KEY|ANTHROPIC_API_KEY=[^[:space:]]+'
git diff --check
```

Any match that may contain a credential is reported only by file path through a
safe wrapper; the raw matching line must not be copied into evidence. The live
preflight must additionally verify presence/non-empty state through a boolean
secret-source interface, never echo length, prefix, suffix, hash, or fragment.

## Current official evidence and unresolved facts

Official sources accessed 2026-08-03:

- [Claude Sonnet 5](https://platform.claude.com/docs/en/about-claude/models/whats-new-sonnet-5)
- [Model IDs and versioning](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions)
- [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Claude API errors](https://platform.claude.com/docs/en/api/errors)
- [Authentication](https://platform.claude.com/docs/en/manage-claude/authentication)
- [Rate limits](https://platform.claude.com/docs/en/api/rate-limits)
- [API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)
- [Commercial API retention](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data)
- [Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)

Public evidence cannot resolve organization/workspace identity, key scope and
expiry, effective account rate/spend limits, ZDR enablement, region, tax,
billing currency, model availability to the account, exact tokenization,
observed latency, refusal behavior, or report quality. Every one remains a
blocking account- or execution-specific fact.
