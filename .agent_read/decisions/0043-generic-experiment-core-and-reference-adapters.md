# 0043: Generic Experiment Core and reference preparation adapters

- Status: Accepted
- Date: 2026-08-17
- Supersedes: 0042 only where it interprets Experiment 0.5 as the generic default Path A

## Context

Experiment Definition 0.5.0, Capsule 0.8.0, `experiment-record/v3`, and
`SKLEARN_TABULAR_CLASSIFICATION_V1` prove a reviewed, constrained
scikit-learn/tabular-classification preparation path. Their implementation and
publication are intentionally narrow: they encode Wine/KNN methodology,
scikit-learn-shaped implementation and evaluation data, and a Python scientific
runtime. Those assumptions are suitable for a reference qualification slice but
cannot define the research-domain-agnostic Experiment product.

ADR 0042 remains the historical authority for why the constrained slice was
created, including its non-programmer Owner goal, checksum-bound approvals,
provider-neutral package identity, no-egress execution, and refusal to install
dependencies. Immutable historical publication bytes must not be rewritten to
retrofit the corrected generic interpretation.

## Decision

Experiment 0.5.0 / Capsule 0.8.0 / `experiment-record/v3` is preserved as
`SKLEARN_REFERENCE_SLICE`. It is a historical/reference capability, not the
generic default Experiment product. KNN/Wine is a reference qualification case
only. The forward generic repair uses the reserved, currently unpublished
identities:

- `reproduction-experiment-local-experimental@0.6.0`;
- Experiment Capsule `0.9.0`;
- `experiment-record/v4`.

The future reference preparation Skill identity is
`sklearn-tabular-classification-preparation-local-builtin@0.1.0`. It is a
`REFERENCE_PREPARATION_ADAPTER`, not the generic Experiment Definition.

Forward Experiment Core is research-domain-agnostic. The intended forward scope
is generic local computational experiments within the existing controlled-local
execution boundary. It does not currently claim generic execution of wet-lab or
human-subject procedures, physical robotics/hardware loops, remote HPC
scheduling, distributed/cloud execution, interactive notebook orchestration, or
hostile untrusted-code containment.

`CODEX_AND_EXPERIMENT_CAPABILITIES_UNDERSTAND_THE_EXPERIMENT`.
`REAGENT_CORE_UNDERSTANDS_THE_EXPERIMENT_LIFECYCLE`.

ReAgent Core owns exact research input/objective identity, the methodology
lifecycle, approvals, exact capability identity and selection evidence, generic
Resource requirements and readiness, preparation requirements, package
identity, runtime requirement/candidate compatibility, execution admission and
bounded execution, normalized process/evaluation/evidence status, provenance,
limitations, and finalization. Codex and exact reviewed Experiment Capabilities
own domain-specific experiment understanding. Capability-owned preparation
adapters own domain-specific typed implementation specifications,
methodology-to-specification validation, deterministic preparation, and domain
evaluation. Preparation is the forward extension boundary; generic Resource,
runtime compatibility, and evaluation are explicit Core/capability seams.

The generic Core records exact specification and evaluation identities and
bounded normalized results; it must not parse domain-specific implementation
specifications or evaluator payload semantics. Git, GitHub, Python,
scikit-learn, machine learning, KNN, Wine, tabular data, numeric metrics,
cross-validation, and robustness analysis are not generic Experiment Core
assumptions.

Preparation-capability selection follows these rules:

- zero supported capabilities returns `AUTOMATIC_PREPARATION_UNSUPPORTED`;
- one supported capability may be selected automatically;
- multiple supported capabilities may be selected automatically only when the
  alternatives are explicitly classified as non-material fallback
  implementations under the approved methodology contract;
- otherwise selection returns `PREPARATION_CAPABILITY_SELECTION_REQUIRED`,
  presents bounded capability differences, and requires explicit Owner
  confirmation.

Numeric or declared priority may order candidates for presentation or govern a
deterministic non-material fallback. It must never substitute for a material
scientific Owner decision.

## Consequences

The 0.5/0.8/v3 publication and its checksums remain immutable. Its production
code may continue to contain reference-slice assumptions because those
assumptions define that exact historical capability. Generic forward work must
use new identities and isolate domain knowledge behind an exact reviewed
Experiment Capability/preparation boundary rather than editing the reference
publication. Research expertise may be required, programming expertise is not a
default Owner prerequisite, and Terminal/CLI use remains an accepted temporary
controlled-local limitation. The five top-level Workflows remain unchanged;
Reproduction & Experiment remains one Workflow, Cloud coordinates metadata,
the Local Workspace owns concrete files and execution, and the existing bounded
Experiment runner remains execution authority.

The following decisions are explicitly deferred and are not GEN-A blockers:

1. The Cloud presentation persistence carrier will be decided in GEN-D after
   inspecting existing Cloud metadata primitives.
2. The current D1 Experiment 0.4 to future 0.6 transition mechanics will be
   decided after GEN-C publication exists.
3. The Full Research preset will advance only after forward downstream
   consumers can consume `experiment-record/v4`.
4. scikit-learn/NumPy supported-runtime provisioning will be decided during
   reference-adapter execution qualification, not generic contract work.

No GEN-A, GEN-B, GEN-C, or GEN-D implementation is authorized by this decision.

## Alternatives considered

Rewriting 0.5/0.8/v3 into a generic publication was rejected because immutable
publication identity must remain truthful. Keeping the sklearn slice as the
generic default was rejected because it couples Experiment Core to one
scientific domain and runtime. Choosing among materially different adapters by
numeric priority was rejected because it would silently make a scientific
Owner decision. Discarding the reference slice was rejected because its bounded
contracts and qualification evidence remain useful as an exact historical
capability and future adapter fixture.
