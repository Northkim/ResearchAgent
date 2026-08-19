"""PostgreSQL and production-registry readiness checks."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text


EXPECTED_MIGRATION_HEAD = "20260820_0038"


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    ready: bool
    checks: dict[str, str]


def check_postgres_readiness(engine: Engine) -> ReadinessResult:
    checks: dict[str, str] = {}
    try:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT 1")) != 1:
                return ReadinessResult(False, {"database": "unavailable"})
            checks["database"] = "ok"
            revisions = tuple(
                connection.execute(
                    text("SELECT version_num FROM alembic_version ORDER BY version_num")
                ).scalars()
            )
            if revisions != (EXPECTED_MIGRATION_HEAD,):
                checks["migration"] = "mismatch"
                return ReadinessResult(False, checks)
            checks["migration"] = EXPECTED_MIGRATION_HEAD
            records = connection.execute(
                text(
                    """
                    SELECT
                      EXISTS (
                        SELECT 1 FROM local_workflow_definition_versions
                        WHERE workflow_definition_id = 'literature-search-local-experimental'
                          AND version = '0.4.0' AND review_status = 'REVIEWED'
                          AND core_capability_maturity = 'REVIEWED_CORE'
                      ) AS literature,
                      EXISTS (
                        SELECT 1 FROM local_workflow_definition_versions
                        WHERE workflow_definition_id = 'idea-discovery-local-experimental'
                          AND version = '0.3.0' AND review_status = 'REVIEWED'
                          AND core_capability_maturity = 'REVIEWED_CORE'
                      ) AS idea,
                      EXISTS (
                        SELECT 1 FROM local_workflow_capsule_versions
                        WHERE workflow_definition_id = 'idea-discovery-local-experimental'
                          AND workflow_version = '0.3.0'
                          AND capsule_version = '0.4.0'
                          AND review_status = 'REVIEWED'
                      ) AS idea_interactive_capsule,
                      EXISTS (
                        SELECT 1 FROM workflow_artifact_requirements
                        WHERE workflow_definition_id = 'idea-discovery-local-experimental'
                          AND workflow_version = '0.3.0'
                          AND requirement_key = 'paper_library'
                          AND artifact_type = 'selected-paper-library/v1'
                          AND content_precondition = '{
                            "schema": "reagent.artifact-precondition.selected-paper-library-nonempty/v0.1",
                            "qualification_schema": "reagent.artifact-qualification.selected-paper-library/v0.1",
                            "minimum_selected_count": 1
                          }'::jsonb
                      ) AS dependency
                      ,EXISTS (
                        SELECT 1 FROM local_workflow_definition_versions
                        WHERE workflow_definition_id = 'reproduction-experiment-local-experimental'
                          AND version = '0.3.0' AND review_status = 'REVIEWED'
                          AND core_capability_maturity = 'SCAFFOLD_CORE'
                          AND (
                            SELECT count(*) FROM workflow_resource_requirements r
                            WHERE r.workflow_definition_id = 'reproduction-experiment-local-experimental'
                              AND r.workflow_version = '0.3.0' AND r.required = false
                          ) = 4
                      ) AS experiment_resource_shell
                      ,EXISTS (
                        SELECT 1 FROM local_workflow_capsule_versions
                        WHERE workflow_definition_id = 'reproduction-experiment-local-experimental'
                          AND workflow_version = '0.3.0'
                          AND capsule_version = '0.5.0'
                          AND review_status = 'REVIEWED'
                      ) AS experiment_interactive_capsule
                      ,(
                        SELECT count(*) = 2
                        FROM local_workflow_capsule_versions
                        WHERE workflow_definition_id IN (
                          'writing-local-experimental',
                          'review-local-experimental'
                        )
                          AND workflow_version = '0.2.0'
                          AND capsule_version = '0.4.0'
                          AND review_status = 'REVIEWED'
                      ) AS writing_review_interactive_capsules
                      ,(
                        SELECT count(*) = 3
                        FROM local_workflow_definition_versions
                        WHERE workflow_definition_id IN (
                          'writing-local-experimental',
                          'review-local-experimental',
                          'reproduction-experiment-local-experimental'
                        )
                          AND version = '0.1.0'
                          AND review_status = 'REVIEWED'
                          AND core_capability_maturity = 'SCAFFOLD_CORE'
                      ) AS scaffold_versions
                      ,EXISTS (
                        SELECT 1 FROM local_workflow_capsule_versions
                        WHERE workflow_definition_id = 'reproduction-experiment-local-experimental'
                          AND workflow_version = '0.4.0'
                          AND capsule_version = '0.7.0'
                          AND review_status = 'REVIEWED'
                      ) AS real_experiment
                      ,EXISTS (
                        SELECT 1 FROM local_workflow_capsule_versions
                        WHERE workflow_definition_id = 'reproduction-experiment-local-experimental'
                          AND workflow_version = '0.6.0'
                          AND capsule_version = '0.9.0'
                          AND review_status = 'REVIEWED'
                      ) AS generic_experiment
                      ,EXISTS (
                        SELECT 1 FROM local_workflow_capsule_versions
                        WHERE workflow_definition_id = 'writing-local-experimental'
                          AND workflow_version = '0.3.0'
                          AND capsule_version = '0.5.0'
                          AND review_status = 'REVIEWED'
                      ) AS real_writing
                      ,EXISTS (
                        SELECT 1 FROM local_workflow_capsule_versions
                        WHERE workflow_definition_id = 'review-local-experimental'
                          AND workflow_version = '0.3.0'
                          AND capsule_version = '0.5.0'
                          AND review_status = 'REVIEWED'
                      ) AS real_review
                      ,EXISTS (
                        SELECT 1 FROM local_workflow_capsule_versions
                        WHERE workflow_definition_id = 'writing-local-experimental'
                          AND workflow_version = '0.4.0'
                          AND capsule_version = '0.6.0'
                          AND review_status = 'REVIEWED'
                      ) AS writing_revision
                      ,(
                        SELECT count(*) = 5
                        FROM local_workflow_definitions
                        WHERE lifecycle = 'AVAILABLE'
                      ) AS exact_registry
                    """
                )
            ).one()
            if not all(bool(value) for value in records):
                checks["production_registry"] = "missing"
                return ReadinessResult(False, checks)
            checks["production_registry"] = "ok"
            return ReadinessResult(True, checks)
    except Exception:
        return ReadinessResult(False, {"database": "unavailable"})
