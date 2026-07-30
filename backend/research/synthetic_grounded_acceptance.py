"""Network-free synthetic acceptance command for guided-literature-review@3.0.0."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from backend.api.composition import ApplicationContainer
from backend.application.commands import (
    ApprovalDecision,
    ApprovalDecisionCommand,
    CreateWorkflowRunCommand,
    StepSpec,
    WorkflowSpec,
)
from backend.demo.seed import (
    GROUNDED_RESEARCH_WORKFLOW_HASH,
    load_grounded_research_workflow,
)
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.research.adapters import LocalFilesystemArtifactStorage
from backend.research.synthetic_grounded_fixtures import SYNTHETIC_TOPIC


def _spec(workflow) -> WorkflowSpec:
    return WorkflowSpec(
        id=workflow.id,
        version=workflow.version,
        name=workflow.name,
        schema_version=workflow.schema_version,
        input_schema=workflow.input_schema,
        outputs=workflow.outputs,
        steps=tuple(
            StepSpec(
                id=step.id,
                kind=step.kind,
                needs=step.needs,
                uses=step.uses,
                input_mapping=step.input_mapping,
                timeout_seconds=step.timeout_seconds,
                max_attempts=step.max_attempts,
                retry_backoff=step.retry_backoff,
                retry_initial_seconds=step.retry_initial_seconds,
                retry_max_seconds=step.retry_max_seconds,
                checkpoint_policy=step.checkpoint_policy,
                approval_policy=step.approval_policy,
            )
            for step in workflow.steps
        ),
    )


async def run_synthetic_acceptance(root: str | Path) -> dict[str, object]:
    database = InMemoryDatabase()
    storage = LocalFilesystemArtifactStorage(root)
    first_uow = InMemoryUnitOfWork(database)
    first = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        artifact_storage=storage,
    )
    services = first.build_services(first_uow)
    workflow = load_grounded_research_workflow()
    created = services.create_workflow_run.execute(
        CreateWorkflowRunCommand(
            project_id="synthetic-grounded-project",
            actor_user_id="synthetic-owner",
            idempotency_key="synthetic-grounded-v3-run",
            agent_profile_ref="synthetic-grounded-agent/v1",
            workflow=_spec(workflow),
            inputs={
                "topic": SYNTHETIC_TOPIC,
                "year_from": 2020,
                "year_to": 2026,
                "max_papers": 3,
                "workflow_hash": f"sha256:{GROUNDED_RESEARCH_WORKFLOW_HASH}",
            },
        )
    )
    await services.runtime.run(created.id)
    pending = first_uow.approvals.list_pending_for_run(
        "synthetic-grounded-project", created.id
    )
    if len(pending) != 1:
        raise RuntimeError("Synthetic V3 acceptance did not pause at one approval")
    approval = pending[0]
    await services.decide_approval.execute(
        ApprovalDecisionCommand(
            approval_id=approval.id,
            decision=ApprovalDecision.APPROVE,
            resolved_by="synthetic-owner",
            decision_idempotency_key="synthetic-grounded-approval-v1",
            current_fingerprint=approval.request_fingerprint,
            reason="Network-free synthetic architecture acceptance",
        )
    )
    execution = first_uow.workflows.get(created.id)
    if execution is None or not execution.workflow_run.status.is_terminal:
        raise RuntimeError("Synthetic V3 acceptance did not reach a terminal state")
    if execution.workflow_run.status.value != "COMPLETED":
        failed = [
            (item.step_id, item.error_code)
            for item in execution.current_step_runs()
            if item.error_code is not None
        ]
        events = first_uow.events.list_for_run(
            "synthetic-grounded-project", created.id
        )
        failure_events = [
            dict(item.payload.data)
            for item in events
            if item.payload.data.get("success") is False
        ]
        raise RuntimeError(
            "Synthetic V3 acceptance failed: "
            f"{execution.workflow_run.error_code or 'unknown'}; steps={failed}; "
            f"events={failure_events}"
        )
    outputs = dict(execution.workflow_run.outputs)
    operations = first_uow.provider_operations.list_for_run(
        "synthetic-grounded-project", created.id
    )
    initial_calls = sum(first.structured_generation_provider.calls.values())

    # Reconstruct from committed in-memory persistence and the same immutable
    # artifact root.  A completed replay must not call the fresh provider.
    restart_uow = InMemoryUnitOfWork(database)
    restarted = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        artifact_storage=storage,
    )
    restart_services = restarted.build_services(restart_uow)
    replay = await restart_services.runtime.run(created.id)
    replay_calls = sum(restarted.structured_generation_provider.calls.values())
    reloaded = restart_uow.workflows.get(created.id)
    if reloaded is None or dict(reloaded.workflow_run.outputs) != outputs:
        raise RuntimeError("Synthetic V3 restart did not reproduce persisted outputs")

    artifacts = tuple(
        item
        for item in restart_uow.artifacts.list_for_project(
            "synthetic-grounded-project"
        )
        if item.producer_run_id == created.id
    )
    publication = outputs["publication"]
    return {
        "workflow_id": workflow.id,
        "workflow_version": workflow.version,
        "workflow_hash": GROUNDED_RESEARCH_WORKFLOW_HASH,
        "workflow_status": replay.status.value,
        "paper_count": publication["paper_count"],
        "summary_count": publication["summary_count"],
        "evidence_count": publication["evidence_count"],
        "claim_count": publication["claim_count"],
        "citation_count": publication["citation_count"],
        "artifact_count": len(artifacts),
        "generation_operation_count": len(operations),
        "initial_generation_calls": initial_calls,
        "replay_generation_calls": replay_calls,
        "actual_cost_minor_units": publication["actual_cost_minor_units"],
        "all_operations_settled": publication["all_provider_operations_settled"],
        "report_checksum": publication["report_checksum"],
        "provenance_checksum": publication["provenance_checksum"],
        "literature_corpus_checksum": publication["literature_corpus_checksum"],
        "network_used": False,
        "real_provider_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        default="runtime_data/grounded_v3_synthetic_acceptance",
    )
    args = parser.parse_args()
    try:
        result = asyncio.run(run_synthetic_acceptance(args.artifact_root))
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "network_used": False,
                },
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps({"status": "passed", **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
