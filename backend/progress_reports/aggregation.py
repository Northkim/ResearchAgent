"""Derived multi-Workflow Progress projections with fixed-query loading."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape

from backend.application.errors import ApplicationCodedNotFoundError
from backend.persistence.ports import UnitOfWork
from backend.project_workspaces.contracts import WorkflowInstanceDesiredState

from .contracts import (
    PROJECT_WORKFLOW_PROGRESS_SCHEMA_VERSION,
    WORKFLOW_INSTANCE_PROJECTION_SCHEMA_VERSION,
    ProjectWorkflowProgressProjection,
    ProjectAttentionProjection,
    ProjectRecentChangeProjection,
    UploadedProgressReport,
    WorkflowActionProjection,
    WorkflowBlockerProjection,
    WorkflowInstanceProgressProjection,
    WorkflowNextActionProjection,
    WorkflowOutputProjection,
    WorkflowStageProjection,
)


class ProjectProgressAggregationService:
    """Read-only Project/Instance aggregation; never inspects a Workspace."""

    def __init__(self, *, unit_of_work: UnitOfWork, clock) -> None:
        self._uow = unit_of_work
        self._clock = clock

    def project_progress(
        self,
        *,
        project_id: str,
        workflow_instance_id: str | None = None,
        history_offset: int = 0,
        history_limit: int = 50,
    ) -> ProjectWorkflowProgressProjection:
        if history_offset < 0 or history_limit < 1 or history_limit > 100:
            raise ValueError("Progress pagination is outside the accepted bounds")
        project = self._uow.project_manifests.get_project(project_id)
        local_project = self._uow.local_projects.get(project_id)
        if project is None or local_project is None:
            raise ApplicationCodedNotFoundError(
                "Project not found", code="PROJECT_NOT_FOUND"
            )
        instances = self._uow.workflow_foundation.list_workflow_instances(project_id)
        if workflow_instance_id is not None and not any(
            item.workflow_instance_id == workflow_instance_id for item in instances
        ):
            raise ApplicationCodedNotFoundError(
                "Workflow Instance not found in Project",
                code="WORKFLOW_INSTANCE_NOT_FOUND",
            )
        definitions = {
            item.workflow_definition_id: item
            for item in self._uow.workflow_foundation.list_definitions()
        }
        definition_versions = {
            (item.workflow_definition_id, item.version): item
            for definition in definitions.values()
            for item in self._uow.workflow_foundation.list_definition_versions(
                definition.workflow_definition_id
            )
        }
        reports = self._uow.progress_reports.list_for_project(project_id)
        acknowledgements = self._uow.workspace_sync.list_acknowledgements(project_id)
        dependency_bindings = (
            self._uow.artifact_references.list_project_bindings(project_id)
        )
        artifact_total = self._uow.artifact_references.count_artifacts(
            project_id=project_id
        )
        artifacts = {
            item.artifact_id: item
            for item in self._uow.artifact_references.list_artifacts(
                project_id=project_id,
                offset=0,
                limit=max(artifact_total, 1),
            )
        }
        friendly_labels = _friendly_labels(instances, definitions)
        by_instance: dict[str, list[UploadedProgressReport]] = defaultdict(list)
        for report in reports:
            by_instance[report.workflow_instance_id].append(report)
        all_requirements = self._uow.artifact_references.list_requirements()
        projection_items = []
        for instance in instances:
            definition_version = definition_versions.get(
                (instance.workflow_definition_id, instance.workflow_version)
            )
            projection_items.append(self._instance_projection(
                instance=instance,
                definition=definitions.get(instance.workflow_definition_id),
                definition_version=definition_version,
                reports=tuple(by_instance.get(instance.workflow_instance_id, ())),
                current_manifest_revision=project.current_manifest_revision,
                acknowledgements=acknowledgements,
                requirements=tuple(
                    item for item in all_requirements
                    if item.workflow_definition_id == instance.workflow_definition_id
                    and item.workflow_version == instance.workflow_version
                ),
                dependency_bindings=dependency_bindings,
                artifacts=tuple(artifacts.values()),
                friendly_label=friendly_labels[instance.workflow_instance_id],
            ))
        projections = tuple(projection_items)
        selected_history = tuple(
            report
            for report in reports
            if workflow_instance_id is None
            or report.workflow_instance_id == workflow_instance_id
        )
        ordered_history = tuple(
            sorted(selected_history, key=_report_activity_key, reverse=True)
        )
        page = ordered_history[history_offset : history_offset + history_limit]
        status_counts = Counter(item.research_status for item in projections)
        latest_activity = max(
            (item.latest_activity_at for item in projections if item.latest_activity_at),
            default=None,
        )
        recommended = min(
            (item for item in projections if item.lifecycle == "ACTIVE"),
            key=lambda item: (_next_action_priority(item.next_action), _workflow_path_priority(item.workflow_definition_id), item.friendly_instance_label),
            default=None,
        )
        latest_project_output = max(
            (
                item.action.latest_output
                for item in projections
                if item.action.latest_output is not None
            ),
            key=lambda item: (item.produced_at or "", item.artifact_id or ""),
            default=None,
        )
        attention = _project_attention(
            recommended=recommended,
            latest_activity=latest_activity,
            latest_output=latest_project_output,
        )
        return ProjectWorkflowProgressProjection(
            schema_version=PROJECT_WORKFLOW_PROGRESS_SCHEMA_VERSION,
            project_id=project_id,
            project_name=local_project.name,
            research_topic=local_project.research_topic,
            manifest_revision=project.current_manifest_revision,
            cloud_observed_at=_utc_text(self._clock()),
            active_workflow_count=sum(
                item.lifecycle == WorkflowInstanceDesiredState.ACTIVE.value
                for item in projections
            ),
            retired_workflow_count=sum(
                item.lifecycle == WorkflowInstanceDesiredState.RETIRED.value
                for item in projections
            ),
            total_progress_report_count=len(reports),
            latest_project_activity_at=latest_activity,
            status_counts=dict(sorted(status_counts.items())),
            instances=projections,
            history=page,
            history_offset=history_offset,
            history_limit=history_limit,
            history_total=len(ordered_history),
            has_more_history=history_offset + len(page) < len(ordered_history),
            dependency_edges=tuple(
                _dependency_edge(binding, artifacts.get(binding.artifact_id))
                for binding in dependency_bindings
            ),
            recommended_workflow_instance_id=(recommended.workflow_instance_id if recommended else None),
            recommended_next_action=(recommended.next_action if recommended else "REVIEW_RESULT"),
            attention=attention,
        )

    def instance_progress(
        self,
        *,
        project_id: str,
        workflow_instance_id: str,
        history_offset: int = 0,
        history_limit: int = 50,
    ) -> ProjectWorkflowProgressProjection:
        return self.project_progress(
            project_id=project_id,
            workflow_instance_id=workflow_instance_id,
            history_offset=history_offset,
            history_limit=history_limit,
        )

    @staticmethod
    def _instance_projection(
        *,
        instance,
        definition,
        definition_version,
        reports: tuple[UploadedProgressReport, ...],
        current_manifest_revision: int,
        acknowledgements,
        requirements,
        dependency_bindings,
        artifacts,
        friendly_label: str,
    ) -> WorkflowInstanceProgressProjection:
        if definition_version is None:
            raise ValueError("Workflow Definition Version authority is missing")
        accepted = tuple(
            item
            for item in reports
            if item.accepted_for_projection and item.normalized_record is not None
        )
        latest = max(accepted, key=_report_activity_key) if accepted else None
        record = latest.normalized_record if latest is not None else None
        acknowledged_revisions = tuple(
            acknowledgement.manifest_revision
            for acknowledgement in acknowledgements
            if any(
                item.get("workflow_instance_id") == instance.workflow_instance_id
                for item in acknowledgement.installed_capsules
            )
        )
        if current_manifest_revision in acknowledged_revisions:
            installation_state = "ACKNOWLEDGED_CURRENT"
            installation_revision = current_manifest_revision
        elif acknowledged_revisions:
            installation_state = "ACKNOWLEDGED_STALE"
            installation_revision = max(acknowledged_revisions)
        else:
            installation_state = "UNKNOWN"
            installation_revision = None
        activity = tuple(_report_activity_text(item) for item in accepted)
        active_bindings = {
            item.requirement_key: item
            for item in dependency_bindings
            if item.consumer_workflow_instance_id == instance.workflow_instance_id
            and item.state.value == "ACTIVE"
        }
        required = tuple(item for item in requirements if item.required)
        compatible_counts = {
            item.requirement_key: sum(
                artifact.artifact_type == item.artifact_type
                and artifact.artifact_schema_version == item.schema_constraint
                and artifact.state.value in {"LOCAL_AVAILABLE", "EXTERNAL_AVAILABLE"}
                for artifact in artifacts
            )
            for item in required
        }
        missing = tuple(
            item.requirement_key
            for item in required
            if item.requirement_key not in active_bindings
        )
        bound = tuple(
            item.requirement_key
            for item in required
            if item.requirement_key in active_bindings
        )
        result_count = sum(
            artifact.producer_workflow_instance_id == instance.workflow_instance_id
            and artifact.state.value not in {"MISSING", "INCOMPATIBLE"}
            for artifact in artifacts
        )
        readiness, next_action = _readiness(
            lifecycle=instance.desired_state.value,
            installation_state=installation_state,
            missing=missing,
            compatible_counts=compatible_counts,
            report_count=len(accepted),
            research_status=(record.status.value if record is not None else "NOT_STARTED"),
            result_count=result_count,
            stable_key=(definition.workflow_definition_id if definition is not None else ""),
        )
        latest_artifact = max(
            (
                artifact
                for artifact in artifacts
                if artifact.producer_workflow_instance_id
                == instance.workflow_instance_id
                and artifact.state.value not in {"MISSING", "INCOMPATIBLE"}
            ),
            key=lambda item: (item.produced_at, item.artifact_id),
            default=None,
        )
        action = _workflow_action(
            project_id=instance.project_id,
            workflow_definition_id=(
                definition.workflow_definition_id if definition is not None else ""
            ),
            output_schema_id=definition_version.output_schema_id,
            lifecycle=instance.desired_state.value,
            research_status=(record.status.value if record is not None else "NOT_STARTED"),
            latest_summary=(escape(record.current_state) if record is not None else None),
            continuation_reason=(
                escape(record.continuation_reason)
                if record is not None and record.continuation_reason is not None
                else None
            ),
            installation_state=installation_state,
            readiness=readiness,
            next_action=next_action,
            missing=missing,
            latest_artifact=latest_artifact,
        )
        return WorkflowInstanceProgressProjection(
            schema_version=WORKFLOW_INSTANCE_PROJECTION_SCHEMA_VERSION,
            project_id=instance.project_id,
            workflow_instance_id=instance.workflow_instance_id,
            workflow_definition_id=instance.workflow_definition_id,
            workflow_definition_version=instance.workflow_version,
            core_capability_maturity=definition_version.core_capability_maturity.value,
            workflow_display_name=(
                definition.display_name if definition is not None else instance.display_name
            ),
            instance_display_name=instance.display_name,
            friendly_instance_label=friendly_label,
            lifecycle=instance.desired_state.value,
            desired_state=(
                "DESIRED"
                if instance.desired_state is WorkflowInstanceDesiredState.ACTIVE
                else "NOT_DESIRED"
            ),
            capsule_id=instance.capsule_id,
            capsule_version=instance.capsule_version,
            research_status=(record.status.value if record is not None else "NOT_STARTED"),
            latest_report_id=(latest.report_id if latest is not None else None),
            latest_report_checksum=(latest.report_checksum if latest is not None else None),
            latest_execution_round=(record.execution_round if record is not None else None),
            latest_summary=(escape(record.current_state) if record is not None else None),
            next_recommended_action=(
                escape(record.next_recommended_action) if record is not None else None
            ),
            artifact_metadata=(record.output_artifacts if record is not None else ()),
            report_count=len(accepted),
            first_activity_at=min(activity) if activity else None,
            latest_activity_at=max(activity) if activity else None,
            installation_state=installation_state,
            installation_manifest_revision=installation_revision,
            sync_uncertainty="LOCAL_STATE_UNKNOWN",
            readiness=readiness,
            next_action=next_action,
            missing_required_inputs=missing,
            compatible_input_counts=compatible_counts,
            bound_required_inputs=bound,
            result_count=result_count,
            action=action,
        )


def _readiness(*, lifecycle, installation_state, missing, compatible_counts, report_count, research_status, result_count, stable_key):
    if lifecycle == "RETIRED":
        return "RETIRED", "REVIEW_RESULT"
    if installation_state != "ACKNOWLEDGED_CURRENT":
        return "NOT_INSTALLED", "SYNC"
    unavailable = tuple(key for key in missing if compatible_counts.get(key, 0) == 0)
    if unavailable:
        return "WAITING_FOR_INPUT", "WAIT_FOR_UPSTREAM"
    if missing:
        return "WAITING_FOR_INPUT", "SELECT_INPUT"
    if research_status == "COMPLETED" or result_count:
        return (
            "RESULT_READY",
            "REVISE_MANUSCRIPT" if stable_key == "review-local-experimental" else "REVIEW_RESULT",
        )
    if report_count:
        return "IN_PROGRESS", "CONTINUE"
    if compatible_counts:
        # Cloud knows the exact bindings, but local materialization remains local truth.
        return "NEEDS_MATERIALIZATION", "MATERIALIZE"
    return "READY_TO_RUN", "RUN"


_OUTPUT_LABELS = {
    "selected-paper-library/v1": "Selected paper library",
    "selected-research-idea/v1": "Selected research idea",
    "experiment-record/v1": "Experiment record",
    "experiment-record/v2": "Experiment result",
    "manuscript-draft/v1": "Manuscript draft",
    "manuscript-draft/v2": "Initial manuscript draft",
    "manuscript-draft/v3": "Revised manuscript draft",
    "review-report/v1": "Review report",
    "review-report/v2": "Structured review report",
}

_ACTION_CONTENT = {
    "SYNC": ("LOCAL", "Sync Local Workspace", "Bring this Workflow's installed Capsule up to the current Project revision."),
    "WAIT_FOR_UPSTREAM": ("INFORMATIONAL", "Wait for required Output", "Complete the upstream research needed by this Workflow."),
    "SELECT_INPUT": ("BROWSER", "Choose exact input", "Select one exact compatible Output; ReAgent never selects latest implicitly."),
    "MATERIALIZE": ("LOCAL", "Prepare inputs locally", "Materialize verified copies in the Local Workspace before running."),
    "RUN": ("LOCAL", "Start in Local Workspace", "Run this Workflow through the public local Workspace command."),
    "CONTINUE": ("LOCAL", "Continue in Local Workspace", "Continue from the Workflow's durable local state with the qualified Agent."),
    "REVIEW_RESULT": ("BROWSER", "Review Output", "Inspect the exact produced Output and its limitations."),
    "REVISE_MANUSCRIPT": ("BROWSER", "Plan manuscript revision", "Use the exact Review and prior Draft as explicit revision inputs."),
}


def _workflow_action(
    *, project_id, workflow_definition_id, output_schema_id, lifecycle,
    research_status, latest_summary, continuation_reason, installation_state,
    readiness, next_action, missing, latest_artifact,
) -> WorkflowActionProjection:
    del project_id  # Route construction remains a frontend navigation concern.
    expected = _expected_output(output_schema_id)
    latest = _produced_output(latest_artifact)
    owner_checkpoint = _owner_checkpoint(latest_summary, continuation_reason)

    if lifecycle == "RETIRED":
        stage = WorkflowStageProjection("RETIRED", "Retired")
        return WorkflowActionProjection(
            stage=stage,
            actor="NONE",
            attention_state="COMPLETED" if latest is not None else "NORMAL",
            blocker=None,
            next_action=_next_action("REVIEW_RESULT" if latest else "NONE"),
            expected_output=expected,
            latest_output=latest,
        )
    if installation_state == "ACKNOWLEDGED_STALE":
        return WorkflowActionProjection(
            stage=WorkflowStageProjection("LOCAL_SYNC", "Local Workspace out of date"),
            actor="OWNER",
            attention_state="ATTENTION_REQUIRED",
            blocker=WorkflowBlockerProjection(
                "LOCAL_STATE_STALE",
                "The Local Workspace acknowledges an older Project revision.",
            ),
            next_action=_next_action("SYNC"), expected_output=expected,
            latest_output=latest,
        )
    if installation_state != "ACKNOWLEDGED_CURRENT":
        return WorkflowActionProjection(
            stage=WorkflowStageProjection("LOCAL_SETUP", "Local Workspace setup required"),
            actor="OWNER", attention_state="ATTENTION_REQUIRED",
            blocker=WorkflowBlockerProjection(
                "LOCAL_SYNC_REQUIRED",
                "Cloud has not received acknowledgement for the current local installation.",
            ),
            next_action=_next_action("SYNC"), expected_output=expected,
            latest_output=latest,
        )
    if research_status == "FAILED":
        return WorkflowActionProjection(
            stage=WorkflowStageProjection("FAILED", _stage_label(workflow_definition_id, "FAILED")),
            actor="OWNER", attention_state="ATTENTION_REQUIRED",
            blocker=WorkflowBlockerProjection(
                "EXECUTION_FAILED",
                latest_summary or "The latest Workflow attempt failed; preserved evidence requires review.",
            ),
            next_action=_next_action("REVIEW_RESULT" if latest else "CONTINUE"),
            expected_output=expected, latest_output=latest,
        )
    if research_status == "CANCELLED":
        return WorkflowActionProjection(
            stage=WorkflowStageProjection("CANCELLED", "Cancelled"),
            actor="OWNER", attention_state="ATTENTION_REQUIRED",
            blocker=WorkflowBlockerProjection(
                "INVALID_OR_UNSUPPORTED_STATE",
                latest_summary or "The latest Workflow attempt was cancelled.",
            ),
            next_action=_next_action("CONTINUE"), expected_output=expected,
            latest_output=latest,
        )
    if research_status == "BLOCKED" and owner_checkpoint:
        return WorkflowActionProjection(
            stage=WorkflowStageProjection("OWNER_APPROVAL", "Waiting for owner review"),
            actor="OWNER", attention_state="OWNER_ACTION_REQUIRED",
            blocker=WorkflowBlockerProjection(
                "OWNER_APPROVAL_REQUIRED",
                latest_summary or "An explicit owner checkpoint must be completed locally.",
            ),
            next_action=WorkflowNextActionProjection(
                "LOCAL", "CONTINUE", "Continue at owner checkpoint",
                "Open this Workflow in the Local Workspace to review the exact checkpoint.",
            ),
            expected_output=expected, latest_output=latest,
        )
    if research_status == "BLOCKED":
        return WorkflowActionProjection(
            stage=WorkflowStageProjection("BLOCKED", "Blocked"),
            actor="OWNER", attention_state="BLOCKED",
            blocker=WorkflowBlockerProjection(
                "INVALID_OR_UNSUPPORTED_STATE",
                latest_summary or "The Workflow reported a blocker that requires review.",
            ),
            next_action=_next_action("CONTINUE"), expected_output=expected,
            latest_output=latest,
        )
    if readiness == "WAITING_FOR_INPUT" and next_action == "WAIT_FOR_UPSTREAM":
        names = ", ".join(_human_requirement(item) for item in missing)
        return WorkflowActionProjection(
            stage=WorkflowStageProjection("INPUT_READINESS", "Waiting for required Output"),
            actor="NONE", attention_state="BLOCKED",
            blocker=WorkflowBlockerProjection(
                "MISSING_INPUT", f"Required upstream Output unavailable: {names}.",
            ), next_action=_next_action(next_action), expected_output=expected,
            latest_output=latest,
        )
    if readiness == "WAITING_FOR_INPUT":
        return WorkflowActionProjection(
            stage=WorkflowStageProjection("INPUT_REVIEW", "Inputs need attention"),
            actor="OWNER", attention_state="OWNER_ACTION_REQUIRED",
            blocker=WorkflowBlockerProjection(
                "MISSING_INPUT", "Compatible Outputs exist but no exact input is bound.",
            ), next_action=_next_action(next_action), expected_output=expected,
            latest_output=latest,
        )
    if research_status == "COMPLETED" or readiness == "RESULT_READY":
        return WorkflowActionProjection(
            stage=WorkflowStageProjection("COMPLETED", _stage_label(workflow_definition_id, "COMPLETED")),
            actor="OWNER" if latest is not None else "NONE",
            attention_state="COMPLETED", blocker=None,
            next_action=_next_action(next_action if latest is not None else "NONE"),
            expected_output=expected, latest_output=latest,
        )
    if research_status == "IN_PROGRESS" or readiness == "IN_PROGRESS":
        return WorkflowActionProjection(
            stage=_active_stage(workflow_definition_id, latest_summary),
            actor="AGENT", attention_state="NORMAL", blocker=None,
            next_action=_next_action("CONTINUE"), expected_output=expected,
            latest_output=latest,
        )
    labels = {
        "NEEDS_MATERIALIZATION": ("INPUT_PREPARATION", "Inputs selected"),
        "READY_TO_RUN": ("READY", "Ready to start"),
    }
    stage_code, stage_label = labels.get(readiness, ("UNKNOWN", "State needs review"))
    return WorkflowActionProjection(
        stage=WorkflowStageProjection(stage_code, stage_label),
        actor="OWNER" if next_action in _ACTION_CONTENT else "SYSTEM",
        attention_state="NORMAL" if stage_code != "UNKNOWN" else "ATTENTION_REQUIRED",
        blocker=(
            None if stage_code != "UNKNOWN" else WorkflowBlockerProjection(
                "INVALID_OR_UNSUPPORTED_STATE", "No safe user action can be derived from the current Cloud state."
            )
        ),
        next_action=_next_action(next_action if stage_code != "UNKNOWN" else "NONE"),
        expected_output=expected, latest_output=latest,
    )


def _project_attention(*, recommended, latest_activity, latest_output):
    if recommended is None:
        action = WorkflowActionProjection(
            stage=WorkflowStageProjection("NO_ACTIVE_WORKFLOW", "No active Workflow"),
            actor="NONE", attention_state="NORMAL", blocker=None,
            next_action=_next_action("NONE"), expected_output=None,
            latest_output=None,
        )
        return ProjectAttentionProjection(
            recommended_workflow_instance_id=None,
            recommended_workflow_label=None,
            action=action,
            recent_change=ProjectRecentChangeProjection(
                "No active Workflow is available.", latest_activity,
            ),
            latest_output=latest_output,
        )
    return ProjectAttentionProjection(
        recommended_workflow_instance_id=recommended.workflow_instance_id,
        recommended_workflow_label=recommended.friendly_instance_label,
        action=recommended.action,
        recent_change=ProjectRecentChangeProjection(
            recommended.latest_summary or recommended.action.stage.label,
            recommended.latest_activity_at or latest_activity,
        ),
        latest_output=latest_output,
    )


def _next_action(code: str) -> WorkflowNextActionProjection:
    if code == "NONE":
        return WorkflowNextActionProjection(
            "NONE", "NONE", "No action available", "No valid action is available from the current Cloud state."
        )
    surface, label, description = _ACTION_CONTENT[code]
    return WorkflowNextActionProjection(surface, code, label, description)


def _expected_output(output_schema_id: str) -> WorkflowOutputProjection | None:
    if "/v" not in output_schema_id:
        return None
    return WorkflowOutputProjection(
        label=_OUTPUT_LABELS.get(output_schema_id, "Workflow Output"),
        artifact_id=None,
        artifact_type=output_schema_id,
        artifact_schema=output_schema_id,
        checksum=None,
        produced_at=None,
        progress_round=None,
        state="EXPECTED",
    )


def _produced_output(artifact) -> WorkflowOutputProjection | None:
    if artifact is None:
        return None
    return WorkflowOutputProjection(
        label=_OUTPUT_LABELS.get(artifact.artifact_type, "Workflow Output"),
        artifact_id=artifact.artifact_id,
        artifact_type=artifact.artifact_type,
        artifact_schema=artifact.artifact_schema_version,
        checksum=artifact.content_checksum,
        produced_at=_utc_text(artifact.produced_at),
        progress_round=artifact.producer_execution_round,
        state="PRODUCED",
    )


def _owner_checkpoint(summary: str | None, continuation: str | None) -> bool:
    text = " ".join(item or "" for item in (summary, continuation)).upper()
    return any(token in text for token in (
        "AWAITING_OWNER_ACTION", "OWNER ACTION", "OWNER APPROVAL", "OWNER REVIEW",
        "APPROVE", "APPROVAL REQUIRED",
    ))


def _human_requirement(value: str) -> str:
    labels = {
        "paper_library": "selected paper library",
        "research_idea": "selected research idea",
        "experiment_record": "experiment result",
        "prior_manuscript": "prior manuscript",
        "causal_review": "causal review",
        "literature_library": "selected literature",
    }
    return labels.get(value, "required research input")


def _stage_label(workflow_definition_id: str, outcome: str) -> str:
    noun = _workflow_noun(workflow_definition_id)
    return f"{noun} {'completed' if outcome == 'COMPLETED' else 'failed'}"


def _workflow_noun(workflow_definition_id: str) -> str:
    labels = {
        "reproduction-experiment-local-experimental": "Experiment",
        "writing-local-experimental": "Writing",
        "review-local-experimental": "Review",
        "idea-discovery-local-experimental": "Idea Discovery",
        "literature-search-local-experimental": "Literature Search",
    }
    return labels.get(workflow_definition_id, "Workflow")


_REAL_STAGE_LABELS = {
    "INPUT_REVIEW": "Input review",
    "EXPERIMENT_REQUIREMENTS": "Experiment requirements",
    "RESOURCE_READINESS": "Resource readiness",
    "EXPERIMENT_PLAN": "Experiment plan",
    "OWNER_APPROVAL": "Owner approval",
    "PREPARATION": "Execution preparation",
    "LOCAL_EXECUTION": "Local execution",
    "EVALUATION": "Evaluation",
    "RESULT_REVIEW": "Result review",
    "WRITING_BRIEF": "Writing brief",
    "EVIDENCE_MAP": "Evidence map",
    "OUTLINE": "Outline",
    "SECTION_DRAFTING": "Section drafting",
    "CLAIM_CITATION_CHECK": "Claim and citation check",
    "REVIEW_SCOPE": "Review scope",
    "CLAIM_EVIDENCE_AUDIT": "Claim and evidence audit",
    "METHOD_RESULT_AUDIT": "Method and result audit",
    "CITATION_REPRODUCIBILITY_AUDIT": "Citation and reproducibility audit",
    "STRUCTURED_ISSUES": "Structured issues",
    "OWNER_REVIEW": "Owner review",
    "ISSUE_RECONCILIATION": "Issue reconciliation",
    "REVISION_PLAN": "Revision plan",
    "DRAFT_REVISION": "Draft revision",
    "CLAIM_CITATION_RECHECK": "Claim and citation recheck",
}


def _active_stage(workflow_definition_id: str, summary: str | None) -> WorkflowStageProjection:
    normalized = (summary or "").strip().upper().replace(" / ", "_").replace(" ", "_")
    if normalized in _REAL_STAGE_LABELS:
        return WorkflowStageProjection(normalized, _REAL_STAGE_LABELS[normalized])
    return WorkflowStageProjection(
        "IN_PROGRESS", f"{_workflow_noun(workflow_definition_id)} in progress"
    )


def _friendly_labels(instances, definitions) -> dict[str, str]:
    grouped = defaultdict(list)
    for item in instances:
        grouped[item.workflow_definition_id].append(item)
    result = {}
    for definition_id, values in grouped.items():
        values.sort(key=lambda item: (item.created_at, item.workflow_instance_id))
        base = definitions.get(definition_id).display_name if definitions.get(definition_id) else values[0].display_name
        for index, item in enumerate(values, 1):
            result[item.workflow_instance_id] = base if len(values) == 1 else f"{base} #{index}"
    return result


def _next_action_priority(value: str) -> int:
    # Project guidance prefers one actionable step over cards that are waiting.
    return {"SYNC": 10, "SELECT_INPUT": 20, "MATERIALIZE": 30, "RUN": 40, "CONTINUE": 50, "REVISE_MANUSCRIPT": 60, "REVIEW_RESULT": 70, "WAIT_FOR_UPSTREAM": 90}.get(value, 99)


def _workflow_path_priority(definition_id: str) -> int:
    return {
        "literature-search-local-experimental": 10,
        "idea-discovery-local-experimental": 20,
        "writing-local-experimental": 30,
        "reproduction-experiment-local-experimental": 40,
        "review-local-experimental": 50,
    }.get(definition_id, 90)


def _report_activity_key(report: UploadedProgressReport) -> tuple[datetime, datetime, str, str]:
    return (
        _parse_time(_report_activity_text(report)),
        _parse_time(report.received_at),
        report.report_id,
        report.receipt_id,
    )


def _dependency_edge(binding, artifact) -> dict[str, object]:
    if artifact is None or artifact.project_id != binding.project_id:
        raise ValueError("Artifact dependency projection is incomplete")
    return {
        "binding_id": binding.binding_id,
        "consumer_workflow_instance_id": binding.consumer_workflow_instance_id,
        "requirement_key": binding.requirement_key,
        "artifact_id": binding.artifact_id,
        "expected_checksum": binding.expected_checksum,
        "state": binding.state.value,
        "producer_workflow_instance_id": artifact.producer_workflow_instance_id,
        "artifact_type": artifact.artifact_type,
        "artifact_schema_version": artifact.artifact_schema_version,
        "produced_at": _utc_text(artifact.produced_at),
    }


def _report_activity_text(report: UploadedProgressReport) -> str:
    record = report.normalized_record
    return record.completed_at if record is not None else report.received_at


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Progress timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("cloud clock must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
