# Final Owner release approval and project handoff

- Date: 2026-08-16
- Status: `CONTROLLED_LOCAL_RELEASE = OWNER_APPROVED`
- Release profile: `CONTROLLED_LOCAL_SINGLE_OWNER`
- Release candidate: `35a961d7251ebbb3faedfbed446f12b6a0fea44c`
- Q1 result: `PASS_Q1_TECHNICALLY_QUALIFIED`
- Migration sole head: `20260815_0026`

## Owner release decision

The Owner approved the exact clean Q1 candidate above. This is the final
handoff/documentation state, not a new product phase. E1, W1, R1, W2, FE-M, the
Engineering Harness, B0, UX-A1, S1, and UI-P0 remain complete, accepted, and
frozen. No production source, test, migration, Registry publication, immutable
Artifact/Capsule identity, API, Core contract, or frontend behavior changed in
this handoff.

```text
OWNER_RELEASE_DECISION = APPROVED
PROJECT_CORE_STATUS = COMPLETE
CONTROLLED_LOCAL_RELEASE = OWNER_APPROVED
RELEASE_CANDIDATE_SHA = 35a961d7251ebbb3faedfbed446f12b6a0fea44c
FURTHER_PRODUCT_DEVELOPMENT = NOT_REQUIRED_FOR_CURRENT_RELEASE
Q1 = COMPLETE
```

## Completed roadmap

| Milestone | Final state |
|---|---|
| Engineering Harness | DONE / FROZEN |
| B0 controlled browser runtime | DONE / FROZEN |
| UX-A1 | DONE |
| S1 | ACCEPTED |
| UI-P0 | ACCEPTED |
| E1 Real Experiment | COMPLETE / FROZEN |
| W1 Real Writing | COMPLETE / FROZEN |
| R1 Real Review | COMPLETE / FROZEN |
| W2 Revision Integration | COMPLETE / FROZEN |
| FE-M production frontend | OWNER ACCEPTED / FROZEN |
| Q1 release qualification | COMPLETE / TECHNICALLY QUALIFIED |

## Supported release boundary

`CONTROLLED_LOCAL_SINGLE_OWNER` supports one loopback-only instance for one
owner on a trusted local machine. Cloud coordinates Project, Workflow, Skill,
Resource, Progress, and Artifact metadata. The Local Workspace executes
research. Artifact and Resource bindings are exact and explicit. Codex is the
supported Agent Harness. Progress and Artifact metadata return through the
supported local-session path. The Owner-accepted desktop frontend presents
task-first Project and Workflow state.

## Completed product capabilities

- **Literature Search:** real local capability producing the selected paper
  library Artifact.
- **Idea Discovery:** real local capability producing the selected research
  idea Artifact from exact selected literature.
- **Real Experiment:** exact Idea and Resource bindings drive requirements,
  readiness, plan, Owner approval, bounded local execution, evaluation,
  `experiment-record/v2`, terminal Progress, and Cloud Artifact projection.
- **Real Writing:** exact Idea/Literature and an optional valid Experiment drive
  the Writing Brief, Evidence Map, Outline approval, evidence-bound drafting,
  claim/citation validation, and `manuscript-draft/v2`.
- **Real Review:** exact Draft and explicit evidence drive Review Scope, bounded
  evidence audit, structured revision issues, and `review-report/v2`.
- **Review-to-Writing Revision:** exact Draft and causal Review drive issue
  reconciliation, Revision Plan, Owner approval, bounded revision, evidence
  recheck, and `manuscript-draft/v3`.
- **Production frontend:** task-first Projects, Project Overview, Workflow
  Detail, Outputs, and Activity; backend-derived presentation projections remain
  authoritative.

## Frozen architecture

Cloud coordinates. The Local Workspace executes. Codex performs substantive
research reasoning. Artifact handoff is explicit and exact. Published Artifacts
and Capsules are immutable. The browser never writes the Local Workspace
directly. Workflow continuity is represented by local files, Progress, exact
Artifact provenance, and durable approval state rather than chat history.

## Immutable product identities

| Capability | Definition | Definition contract checksum | Capsule | Capsule checksum | Output |
|---|---|---|---|---|---|
| Experiment | 0.4.0 | `sha256:809029bd63ac101a49abbcbe253550284c369b1024ca774e61f49fa88fcb8193` | 0.7.0 | `sha256:a01688245334eb95a7733a746e6357c1876daf09139492477b7186ebaea34fa3` | `experiment-record/v2` |
| Writing | 0.3.0 | `sha256:6d0142be692570bcf11569d557e8a87821d45e84936a3cff549fab5f378a7223` | 0.5.0 | `sha256:3f94b97702190efed2a4fcd2c0e5f770eaf64020a56ec5f14eaf41412314e8ad` | `manuscript-draft/v2` |
| Review | 0.3.0 | `sha256:93d171fe62223837da97c146e7d7c5f66b209ad28e0ab39c7fa487ebe2952068` | 0.5.0 | `sha256:d8565c18f6d0c5d540d4d0ff63b90d7e7c2cf844e3f3d954c22cca2af5622262` | `review-report/v2` |
| Writing Revision | 0.4.0 | `sha256:53e910ac525f4fe6f69e2c75631d0d1f8ff82ad7620a9c1f879c3198e45828ea` | 0.6.0 | `sha256:d10eeb323d17944c6ef8b4ed9bfb149751ee96bbf6cac6b6bd41b45629c327c3` | `manuscript-draft/v3` |

These identities remain immutable and were not republished.

## Final Q1 evidence

- Backend: `959 passed / 14 skipped / 0 failed`.
- Frontend TypeScript: PASS.
- Frontend ESLint: PASS.
- Frontend Vitest: `17 files / 36 tests` PASS.
- Production Next.js build: PASS.
- Guarded disposable PostgreSQL and migration qualification: PASS.
- E1/W1/R1/W2 public Workspace paths: PASS at their controlled public-command
  evidence levels.
- W1/R1/W2 bounded Real Codex completion: PASS at E7.
- Full Real Codex Experiment completion: `NOT_CLAIMED`; E1 retains controlled
  public-Workspace evidence.
- Controlled browser suite: PASS at E6, including canonical FE-M, H1, and Local
  V0.1 interactive/unattended journeys.
- Cloud/local authority, exactly-once/recovery, supported security boundary,
  bounded compatibility, immutable identities, cleanup, and candidate-mutation
  gates: PASS.
- Candidate mutation: NONE.

`VERIFIER_INDEPENDENCE = LIMITED` because the verifier participated in earlier
test-only release-candidate corrections. No evidence level is upgraded by this
handoff.

## Known limitations

### Supported boundary

The approved release is intentionally loopback-only, single-owner,
trusted-local-machine, local-first, and Codex-backed. Those constraints define
the release rather than defects.

### Deferred future capability

- public SaaS deployment and multi-user isolation;
- hosted research execution and hostile-code containment;
- live Provider correctness and Claude Code qualification;
- generalized long-lived Workspace compatibility;
- arbitrary scientific correctness and publication fitness;
- mobile visual fidelity;
- full Real Codex Experiment completion;
- frozen Experiment 0.4 Owner Workspace recovery.

## Recommended Owner demonstration

1. Open Projects and identify the research project needing attention.
2. Open Project Overview and show the single recommended next step.
3. Open Workflow Detail and show its specific task and primary action.
4. Explain the exact selected Artifact inputs and their Ready state.
5. Demonstrate the Literature Search to Idea Discovery handoff.
6. Show the selected research idea and the Experiment Output.
7. Show the evidence-bound Writing draft and its approved outline lineage.
8. Show structured Review issues and their exact Draft/evidence references.
9. Show the Review-driven revised manuscript and issue reconciliation.
10. Open Outputs and Activity to show result navigation and durable progress.
11. Briefly expand Technical Details to show exact schema and provenance.
12. Close by explaining that Cloud coordinates, the Local Workspace executes,
    and Codex performs the bounded research reasoning.

## Handoff and future directions

No further product development is required for this approved release. Deferred
capabilities above require a new explicit Owner authorization and must not be
treated as automatic next phases. No ADR was added because release approval did
not alter the frozen architecture or immutable contracts.
