# 0044: Artifact-bound Cloud presentation companion

- Status: Accepted
- Date: 2026-08-17

## Context

Generic `experiment-record/v4` bytes remain authoritative in the Local
Workspace, but the Owner-facing Cloud page must render bounded scientific
findings. Existing Artifact References already provide exact Artifact identity
and checksum binding, while their current metadata has no typed presentation
payload. Progress metadata is mutable projection state and Hosted Artifact
storage is the wrong ownership boundary.

## Decision

Store at most one immutable typed presentation companion on the existing exact
Artifact Reference row. The companion has an exact schema identity, Artifact
ID/checksum binding, presentation checksum, bounded validated JSON payload, and
reported time. Its four nullable persistence fields are all absent or all
present. Exact replay is idempotent; any changed replay fails closed.

Cloud accepts only safe bounded presentation primitives. It never stores raw
Artifact, package, source, log, credential, or arbitrary local-file bytes.
Local remains authoritative for concrete research outputs.

## Consequences

Experiment pages and Outputs can render v4 findings without browser reads of a
Workspace. Future Artifact presentation types may reuse the generic carrier,
but each schema requires explicit validation. Presentation replacement and
deletion are intentionally unsupported; a changed result requires a new exact
Artifact identity.

## Alternatives considered

- Reuse Progress context metadata: rejected because it is not one immutable
  Artifact-bound typed carrier.
- Upload the Artifact or package: rejected because concrete bytes remain Local.
- Add an Experiment-specific presentation table: rejected because the existing
  exact Artifact row already provides the correct generic ownership identity.
- Infer findings from generic Artifact metadata: rejected because Cloud must not
  fabricate scientific content it does not possess.
