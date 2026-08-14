# Shared boundaries for Real Experiment, Writing, and Review

Status: Owner-ratified interface/safety boundary; scientific method design is deferred

This document defines only contracts shared by the three remaining Real Cores.
It does not authorize implementation, introduce persisted enum values, or
specify complete Experiment, Writing, or Review methodology.

## Artifact versioning

- Published Artifact v1 schemas and semantics remain immutable.
- A capability that cannot be represented compatibly uses a new Artifact
  version or a separately named companion Artifact.
- No consumer may reinterpret a v1 field to carry incompatible v2 semantics.
- Producer and consumer compatibility is explicit in Workflow Definition and
  Capsule contracts; there is no implicit coercion or auto-latest selection.
- Historical Artifact bytes, checksums, provenance, and consumers remain
  testable after a new version is introduced.
- Publication requires an explicit versioning/migration decision. A schema
  migration is not assumed merely because a new Registry contract is needed.

## Evidence identity

Every future scientific assertion, result, manuscript claim, or review issue
must be able to identify, directly or through a validated companion record:

```text
source Artifact ID
source Artifact kind/version
source checksum
producer Workflow Instance
producer Progress round
specific evidence item or location
evidence availability
evidence limitation
```

Locations may be structured item IDs, claim IDs, result IDs, table/section
anchors, or a bounded unavailable-location marker. Free text alone is not
sufficient identity. Missing or inaccessible evidence is represented as a
limitation, never converted into confidence.

## Exact handoff and isolation

- Owners bind exact immutable input Artifacts.
- The system does not choose the latest compatible Artifact automatically.
- A Workflow reads only materialized, declared inputs and its own package/local
  state. It does not inspect a sibling Workflow's private files.
- The browser changes Cloud desired state and binding metadata only. Local bytes
  are written by the root Workspace client or Capsule execution path.
- Cross-Core provenance is carried by typed Artifacts, not directory knowledge.

## Mandatory owner approval points

Approval is a recorded transition with exact proposed inputs/actions; it is not
inferred from conversation continuation.

| Core/surface | Mandatory approval |
|---|---|
| Experiment | plan; exact execution command; network access; resource use; final Artifact publication |
| Writing | outline; disposition of unsupported claims; final Artifact publication |
| Review | scope; final Artifact publication |
| Shared | any changed binding after approval requires renewed approval |

Whether each approval is Cloud-persisted, Progress-mediated, or represented in
a future companion contract remains an owner decision. Implementation must not
invent a persistence model in the interim.

## Progress semantics

Shared conceptual meanings:

| State | Meaning | Current Progress v0.2 expression |
|---|---|---|
| `IN_PROGRESS` | Work is advancing without a required external decision | Direct persisted status |
| `AWAITING_OWNER` | A bounded owner decision is required; execution must not proceed | Indirect only: `IN_PROGRESS` plus state/next-action/continuation metadata; no persisted status exists |
| `BLOCKED` | Execution cannot proceed without a prerequisite or authorized change | Direct persisted status |
| `FAILED` | The attempted execution terminated unsuccessfully with preserved evidence | Direct persisted status |
| `CANCELLED` | The owner/system intentionally ended the attempt without completion | Direct persisted status |
| `COMPLETED` | The exact round and declared outputs are finalized and eligible for Cloud acknowledgement | Direct persisted status |

No new persisted state is authorized here. S1 must decide whether indirect
`AWAITING_OWNER` is sufficient before any Core depends on it. Finalization must
preserve adopt-or-finalize exactly-once behavior: a valid Agent-finalized next
round is adopted; otherwise the runner may finalize once. Cloud-missing local
completion is recovered by validating and uploading the exact immutable report,
never by rerunning the Harness or creating a repair round.

## Resource readiness

Resource readiness is a ladder, not one boolean:

| Layer | Required proof | Current support |
|---|---|---|
| `METADATA_REFERENCE_EXISTS` | provider/name/reference recorded | Direct |
| `EXACT_REVISION_IDENTIFIED` | immutable commit/revision identity | Direct for supported resolution paths |
| `BYTES_AVAILABLE_LOCALLY` | contained local materialization exists | Direct where resolver/materializer supports it |
| `CHECKSUM_VERIFIED` | expected bytes/index checksum matches | Direct where materialized |
| `LICENSE_ACCEPTED` | applicable use terms accepted by owner | Not represented canonically |
| `RUNTIME_USABLE` | environment/dependencies/entry point pass readiness checks | Not represented canonically |
| `OWNER_APPROVED` | exact revision/use/command approved | Not represented as a shared canonical contract |

A GitHub or Hugging Face metadata reference is not execution-ready. UI and
Workflow code must not collapse these layers into a single green status.

## Minimum cross-Core provenance

Future v2 or companion Artifacts must support:

- exact producer Definition and Capsule identity;
- Project and Workflow Instance identity;
- Progress report ID, checksum, and round;
- exact input Artifact IDs, versions, checksums, roles, and producer lineage;
- exact Resource identity/revision/checksum and relevant readiness/approval;
- owner approval records applicable to the output;
- output checksum, size, media/schema type, and bounded evidence references;
- limitations, unavailable evidence, and unsupported assertions;
- for revision outputs, exact prior manuscript and causal Review Artifact;
- for review issues, exact manuscript claim/location and supporting or missing
  evidence;
- for experiment results, plan/execution identity and a distinction between
  observed results and placeholders or non-execution.

## Core-specific interface edges

### Real Experiment

Consumes an exact selected idea and any explicitly approved Resources. Produces
evidence that distinguishes plan, authorized command, actual execution, result,
and non-execution. A general scheduler, hosted execution, live network policy,
and scientific methodology are outside this shared specification.

### Real Writing

Consumes exact idea, literature, optional Experiment, Review, and prior draft
Artifacts. Initial drafting is evidence-bound; unsupported claims remain
visible. Revision provenance must identify its prior draft and causal review.
Prose generation method and citation-verification method are deferred.

### Real Review

Consumes an exact manuscript and explicitly bound evidence. Issues must anchor
to claims/locations and evidence or evidence absence. Publication acceptance,
numeric scoring, and confidence semantics remain owner decisions and are not
introduced here.

## Writing #2 evidence gate

Repository documentation currently proves that a controlled/synthetic revision
path was specified and qualified. It does not contain owner-observed evidence
confirming all of the following for the real Writing #2 UX:

| Required observation | Repository status |
|---|---|
| Writing #2 instance created | Not owner-confirmed |
| Draft A explicitly bound | Not owner-confirmed |
| Review A explicitly bound | Not owner-confirmed |
| Experiment intentionally not bound | Not owner-confirmed |
| revision round detected | Not owner-confirmed |
| no reviewer comments fabricated | Not owner-confirmed |
| Draft B finalized | Not owner-confirmed |
| Draft B provenance recorded | Not owner-confirmed |
| owner UX observations recorded | Absent from the current observation record |

```text
WRITING_2_UX_CLOSURE = OWNER_EVIDENCE_REQUIRED
```

This does not block approval or later implementation of the Engineering Harness.
It blocks final approval of Real Writing and Real Review contracts.
