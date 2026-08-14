---
name: engineering-verification
description: Design or assess tests, review an implementation, verify acceptance criteria, qualify a public path, inspect architecture drift, assess a release claim, or decide whether ReAgent evidence is sufficient. Use after locating an approved change packet; report failures and evidence limits without repairing them unless a separate phase explicitly authorizes implementation.
---

# Engineering verification

Verify the approved contract at explicitly authorized evidence levels. Do not
repair failures while acting as verifier.

## Authoritative inputs

Read, in order:

1. the approved change packet;
2. relevant requirement-ledger entries;
3. `docs/engineering/ENGINEERING_VERIFICATION_SPEC.md`;
4. `docs/testing/EVIDENCE_LEVEL_POLICY.md`;
5. `docs/testing/QUALIFICATION_LEVELS.md`;
6. `docs/testing/templates/VERIFICATION_PACKET_TEMPLATE.md`.

## Procedure

1. Record verification scope, versions, baseline, required evidence, and the
   implementation under review.
2. Declare `VERIFIER_INDEPENDENCE = LIMITED` if this Codex session implemented
   the change. Do not claim independent verification.
3. Map every requirement to actual tests/evidence and its fixture class.
4. Distinguish unit, helper, service, PostgreSQL/API, public command, browser,
   real Codex, long-lived Workspace, and owner evidence.
5. Record negative, failure/recovery, compatibility, security, and public-path
   cases required by risk.
6. Run only tests authorized by the active phase. Record every skipped,
   unavailable, timed-out, mocked, or interrupted level.
7. Report implementation defects separately from contract or architecture
   drift. Do not add tests or production fixes automatically.
8. Fill the verification template and limit the final claim to the highest
   evidence actually achieved.

## Non-substitution rules

- Fake Harness PASS is not Real Codex PASS.
- Synthetic fixture PASS is not long-lived Workspace PASS.
- Component mock PASS is not real frontend/backend PASS.
- A skipped PostgreSQL or browser suite is not PASS.
- A lower-evidence PASS cannot erase a higher-evidence FAIL.

Never weaken acceptance criteria, turn failure into deferred PASS, use test
count or coverage percentage as sufficient proof, or claim an unexecuted level.

