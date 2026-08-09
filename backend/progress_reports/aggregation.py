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
    UploadedProgressReport,
    WorkflowInstanceProgressProjection,
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
