# Engineering Harness and Core sequencing plan

Status: Owner-ratified sequence; no implementation authorized

This plan begins only after the specification packet and relevant owner
decisions are approved. Each phase requires a new explicit authorization.

```text
H1B — Owner contract ratification
→ H2A — Minimal Engineering Harness foundation
→ B0 — Controlled browser runtime qualification
→ UX-A1 — Current-state frontend browser audit
→ S1 — Shared Core contract drafts
→ UI-P0 — Canonical screens from typed fixtures
→ E1 — Real Experiment narrow vertical slice
→ W1 — Real Writing initial-draft vertical slice
→ R1 — Real Review bounded evidence-audit vertical slice
→ W2 — Writing revision integration
→ FE-M — Incremental frontend completion
→ Q1 — Focused release qualification
```

## H1B — Owner contract ratification

**Result:** the governance specifications and ODR-001 through ODR-016 are
ratified within their recorded scopes. This phase changes documentation only
and does not authorize H2A implementation.

## H2A — Minimal Engineering Harness foundation

**Prerequisites:** H1B is reviewed and committed by the Owner, followed by a
separate explicit H2A implementation authorization.

**Allowed:** exactly two repo-local Skills named `engineering-change-contract`
and `engineering-verification`; one small change-packet template; one small
verification-packet template; one minimal requirement-to-test ledger example
or schema; a concise root `AGENTS.md` routing update; and focused validation
that proves these artifacts can be discovered and used.

**Forbidden:** a third Skill, plugin framework, orchestration engine, automatic
ADR platform, general documentation generator, general policy engine,
dashboard, database, migration, Registry integration, Capsule publication,
frontend work, browser runtime, CI, or comprehensive release framework. H2A is
not an engineering-management product.

**Expected artifacts:** the two discoverable Skills, two bounded templates,
one minimal ledger artifact, the routing update, and a focused validation
record. The separate H2A change packet must name exact paths before editing.

**Evidence:** focused repository discovery/use checks only; no business or
release qualification claim.

**Stop:** scope expands beyond the enumerated artifacts, requires production
behavior or persistence, introduces a third capability, or attempts to solve a
future Core's concrete testing problem in advance.

**Owner approval:** explicit H2A authorization before any implementation and
Owner review of its bounded output before B0.

## Deferred mechanical work

The following are `DEFERRED_UNTIL_CONCRETE_NEED`, are not H2A blockers, and do
not imply an automatic H2B phase:

- Artifact or Progress golden corpora;
- historical Capsule rebuild framework;
- architecture dependency linter;
- general CI workflow;
- OpenAPI client generation;
- route-wide error-contract overhaul;
- visual regression and axe/WCAG automation;
- multi-browser testing;
- long-lived Workspace corpus;
- supply-chain hardening;
- generalized ledger platform.

A focused check may be proposed later only when it directly protects an active
implementation contract, and requires separate Owner authorization.

## B0 — Controlled browser runtime qualification

**Prerequisites:** H2A foundation accepted; approved browser runtime spec;
existing package/browser binary availability established without installation.

**Allowed:** disposable database and Workspace orchestration, deterministic
fixtures, controlled backend/frontend start/stop, Playwright/browser controller
qualification, temporary screenshots.

**Forbidden:** owner runtime/data, real Workflows, live Providers, production
fixture persistence, UX redesign.

**Expected artifacts:** seven-state B0 report, commands/ports/markers, fixture
manifest, teardown proof, screenshot policy evidence.

**Evidence:** E6 for overall PASS.

**Stop:** any ambiguity in DB/Workspace/API target, missing browser binary,
unexpected network, or failed teardown.

**Owner approval:** approve controlled fixture scope and any retained evidence.

## UX-A1 — Current-state browser UX audit

**Prerequisites:** B0 PASS and representative deterministic route/state fixtures.

**Allowed:** read-only browser navigation, screenshots, accessibility inspection,
task/route/state/IA findings.

**Forbidden:** redesign implementation, owner data, direct Workspace writes,
claims based only on source when visual evidence is required.

**Expected artifacts:** route inventory, journey findings, viewport screenshots,
state/terminology/accessibility gaps, revised design requirements.

**Evidence:** E6; owner interpretation can later add E9 without replacing E6.

**Stop:** fixture lacks a claimed state or frontend targets an uncontrolled API.

**Owner approval:** accept audit findings and choose information-architecture
direction before UI-P0 or FE work.

## S1 — Shared Core contract drafts

**Prerequisites:** approved H2A foundation; UX-A1 evidence; owner disposition of
the shared decisions; Writing #2 closure before final Writing/Review approval.

**Allowed:** contract/ADR proposals for versioned Artifacts, approval semantics,
Resource readiness, evidence identity, APIs, errors, and state transitions.

**Forbidden:** implementation, accepted ADR status without owner approval,
in-place v1 mutation, complete scientific methodology without decisions.

**Expected artifacts:** Owner Design Packets; change and verification packets;
schema/API state diagrams; compatibility matrices; unresolved-decision register.

**Evidence:** E0 specification backed by repository evidence; test designs map
future requirements to required E1-E9 levels.

**Stop:** Writing #2 evidence missing for final W/R approval, conflicting
immutable contract, unresolved v2/companion/API/persistence decision.

**Owner approval:** accept each Core contract and ADRs separately.

## UI-P0 — Canonical mock screens from typed fixtures

**Prerequisites:** accepted task-first IA direction; sufficiently stable S1 view
models; B0; typed mock fixtures derived from proposed API contracts.

**Allowed:** non-production canonical prototypes/screens, fixture types, browser
evaluation at three viewports, accessibility exploration.

**Forbidden:** claiming mock/API parity, production route migration, backend or
Workspace mutation, hiding unresolved states behind copy.

**Expected artifacts:** Projects, Project Overview, and Workflow Detail screen
spec/prototypes; state matrix; data requirements; decision log.

**Evidence:** E6 for controlled prototype behavior, clearly labeled mock data.

**Stop:** prototype requires a missing product decision or invents unavailable
backend state.

**Owner approval:** select canonical screens and terminology before FE-M.

## E1 — Real Experiment narrow vertical slice

**Prerequisites:** accepted Experiment contract; Resource/approval/network and
execution-boundary decisions; H2A contracts in use; controlled frontend/API requirements.

**Allowed:** one bounded local execution mode, exact Resource readiness,
owner-approved plan/command, actual result provenance, new immutable versions.

**Forbidden:** general scheduler, hosted execution, implicit network, arbitrary
unreviewed commands, Real Writing/Review, Experiment 0.4 mutation.

**Expected artifacts:** versioned contracts, Definition/Capsule, API/UI states,
migration only if approved, security model, ledger and qualification report.

**Evidence:** E7 full real-Codex completion plus E4/E5/E6; E8 before release
when long-lived compatibility is affected.

**Stop:** execution cannot be sandboxed/bounded, exact Resource readiness is
unknown, owner approval cannot be durable, or historical bytes drift.

**Owner approval:** approve plan/command/network model and release packet.

## W1 — Real Writing initial-draft vertical slice

**Prerequisites:** accepted Writing contract; Writing #2 UX closure; evidence
identity/citation/unsupported-claim decisions; E1 output compatibility known.

**Allowed:** evidence-bound initial drafting, outline approval, claim/evidence
mapping, explicit limitations, new immutable Artifact/Workflow versions.

**Forbidden:** fabricated citations/results/novelty, revision intelligence,
auto-latest, hidden sibling reads, publication-quality claims beyond evidence.

**Expected artifacts:** initial-draft contract, validators, API/UI states,
Definition/Capsule, ledger entries and qualification report.

**Evidence:** E7 complete bounded drafting plus E4/E5/E6; grounding negatives.

**Stop:** source availability/citation policy unresolved, owner approval or
unsupported-claim behavior ambiguous, v1 compatibility would be broken.

**Owner approval:** accept outline/claim policy and release packet.

## R1 — Real Review bounded evidence-audit vertical slice

**Prerequisites:** accepted Review scope/recommendation contract; Writing #2 UX
closure; W1 manuscript/evidence contract stable.

**Allowed:** claim/evidence and methodology/result/reproducibility audit,
structured anchored issues, bounded revision guidance, immutable new versions.

**Forbidden:** publication acceptance prediction, numeric score, unsupported
confidence, fabricated findings, general peer-review simulation.

**Expected artifacts:** review v2/companion contract, validators, API/UI states,
Definition/Capsule, ledger and qualification report.

**Evidence:** E7 full bounded review plus E4/E5/E6 and negative evidence cases.

**Stop:** recommendation semantics, evidence anchors, missing-evidence behavior,
or consumer compatibility remains unresolved.

**Owner approval:** accept Review semantics and release packet.

## W2 — Writing revision integration

**Prerequisites:** W1 and R1 contracts; causal Review provenance decision;
owner-accepted revision UX evidence.

**Allowed:** explicit Draft+Review bindings, revision plan/approval, new Draft
with exact causal provenance, preservation of prior Artifacts.

**Forbidden:** implicit latest Review/Draft, overwriting Draft A, fabricated
review comments, revising from sibling private files.

**Expected artifacts:** revision contract, cross-object validators, UI states,
interactive revision qualification and compatibility evidence.

**Evidence:** E7 full Writing→Review→Writing chain, E6 UI, and E9 owner UX
before declaring product closure.

**Stop:** causal review identity is not enforceable or prior outputs mutate.

**Owner approval:** accept revision result/UX and release packet.

## FE-M — Incremental frontend completion

**Prerequisites:** canonical screens approved; Core APIs/errors/states stable;
controlled browser suite active.

**Allowed:** incremental task-first route/component/view-model migration,
checked client updates, accessibility and responsive work.

**Forbidden:** taxonomy changes disguised as copy, browser Workspace writes,
single-bang rewrite without compatibility plan, hiding technical detail entirely.

**Expected artifacts:** migrated routes, API contract evidence, responsive and
accessibility results, visual baselines, deprecation/compatibility plan.

**Evidence:** E6 with real controlled API at all required viewports.

**Stop:** API/client drift, missing blocked/error/loading state, inaccessible
primary flow, or uncontrolled fixture dependency.

**Owner approval:** staged canonical-screen sign-off and final IA acceptance.

## Q1 — Focused release qualification

**Prerequisites:** requirements changed by the active release are mapped;
Core/frontend phases in scope are complete; no unresolved critical decision or
higher-level failure affects the release.

**Allowed:** the focused API, persistence, migration, public command, controlled
browser, real Codex, compatibility, and bounded owner qualification selected by
the approved change/verification packets.

**Forbidden:** fixing defects inside qualification without a new change packet,
normalizing owner evidence, live Provider use unless explicitly authorized.

**Expected artifacts:** bounded evidence-indexed release report, skips/gaps,
applicable immutable checksums, rollback conditions, and any separately approved
owner manual test packet.

**Evidence:** the highest level required by each active contract. E8/E9 are used
only for specifically approved compatibility or owner-observation claims; a
general long-lived Workspace corpus is not implied.

**Stop:** skipped release blocker, historical drift, Cloud/local disagreement,
real Codex incomplete path, owner evidence conflict, or teardown/security failure.

**Owner approval:** explicit release decision after reviewing all conflicts and
unachieved evidence levels.
