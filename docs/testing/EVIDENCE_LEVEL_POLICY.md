# Engineering evidence-level policy

Status: Owner-ratified policy; implementation not authorized

This policy ranks evidence used for ReAgent engineering and release claims. It
does not make higher-level observations into design authority, and it does not
permit lower-level evidence to erase a higher-level failure.

## Levels

| Level | Evidence | Minimum meaning |
|---|---|---|
| E0 | Static claim | A document, comment, type annotation, or source inspection states the behavior. It has not executed. |
| E1 | Unit or schema test | An isolated function, validator, serializer, or schema contract executed. |
| E2 | Internal helper test | Multiple internal collaborators executed, but not through a supported public product path. |
| E3 | Service integration | Domain services and repositories executed together with controlled dependencies. |
| E4 | Real PostgreSQL or public API integration | The real persistence/API boundary executed against a disposable database. |
| E5 | Public CLI or Workspace command | A supported command executed through the root client and local package boundary. PTY and fake-Harness evidence must be labeled separately. |
| E6 | Controlled browser against a real controlled API | A browser exercised the frontend and real controlled backend with a verified disposable dataset. |
| E7 | Real Codex qualification | Installed Codex executed the relevant path. Startup-only and complete-lifecycle tests are distinct claims. |
| E8 | Long-lived Workspace compatibility | Existing durable local state survived upgrade, reconciliation, or recovery without regeneration. |
| E9 | Owner-observed real product evidence | The owner observed the real product path and supplied bounded evidence. |

## Interpretation rules

1. Evidence is cumulative, not substitutive. A higher level can reveal a
   limitation hidden by lower levels; it does not make the lower test useless.
2. A lower-level PASS must never overwrite a higher-level FAIL for the same
   claim. The claim remains failed or conflicting until the higher-level issue
   is resolved or its scope is explicitly distinguished.
3. Every qualification statement records its highest achieved level, the exact
   path exercised, fixture class, date, and all relevant skipped levels.
4. Synthetic, mocked, fake-Harness, controlled, long-lived, and owner evidence
   are named explicitly. `PASS` without a fixture/evidence qualifier is invalid.
5. A real Codex startup smoke does not qualify finalization, publication,
   recovery, or Cloud acknowledgement.
6. A public Workspace command with a fake Harness does not qualify the real
   Harness. A component mock does not qualify a real frontend/backend contract.
7. An internal helper test does not qualify public argument parsing, file
   discovery, authentication, persistence, or presentation behavior.
8. A synthetic historical fixture cannot override conflicting owner long-lived
   Workspace evidence. The conflict remains visible.
9. E9 records an occurrence and user impact. It is not automatically a broadly
   generalizable contract and cannot override immutable schemas or accepted
   architectural decisions without an explicit owner decision.
10. Evidence must be reproducible or carry a bounded evidence record: command,
    version, identity/checksum where safe, expected result, actual result, and
    limitations. Secrets and owner research payloads are excluded.

## Claim format

Every material release or architecture claim should use:

```text
claim_id:
claim:
scope:
result: PASS | FAIL | BLOCKED | CONFLICTING
highest_evidence_level:
qualification_path:
fixture_class:
versions:
evidence_references:
skipped_levels:
known_limitations:
```

## Current conflict marker

The Experiment 0.4 recovery claim is `CONFLICTING`: controlled synthetic
fixtures reached recovery, while owner long-lived evidence remained
`LOCAL_PROGRESS_INVALID`. The owner observation is the stronger product
evidence for that instance. It must not be rewritten as a PASS, generalized to
other states, or used as a reason to mutate the frozen historical Capsule.
