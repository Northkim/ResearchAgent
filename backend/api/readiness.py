"""PostgreSQL and production-registry readiness checks."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text


EXPECTED_MIGRATION_HEAD = "20260806_0015"


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
                          AND version = '0.2.0' AND review_status = 'REVIEWED'
                          AND core_capability_maturity = 'REVIEWED_CORE'
                      ) AS idea,
                      EXISTS (
                        SELECT 1 FROM workflow_artifact_requirements
                        WHERE workflow_definition_id = 'idea-discovery-local-experimental'
                          AND workflow_version = '0.2.0'
                          AND requirement_key = 'paper_library'
                          AND artifact_type = 'selected-paper-library/v1'
                      ) AS dependency
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
