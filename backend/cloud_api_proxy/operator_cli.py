"""Operator-only digest-backed capability token issue/revoke CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from backend.database.engine import create_postgres_engine, create_session_factory

from .fake_adapter import DeterministicFakePaperSearchAdapter
from .contracts import ADAPTER_ID, OPENALEX_ADAPTER_ID
from .package_identity import read_validated_package_identity
from .service import CloudAPIProxyService
from .sql import SQLProxyUnitOfWork


def _service_from_environment() -> tuple[CloudAPIProxyService, object]:
    database_url = os.environ.get("REAGENT_DATABASE_URL")
    if not database_url:
        raise ValueError("REAGENT_DATABASE_URL is required")
    engine = create_postgres_engine(database_url)
    session_factory = create_session_factory(engine)
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapter=DeterministicFakePaperSearchAdapter(),
    )
    return service, engine


def _validate_output_path(output: str | Path, package_root: Path) -> Path:
    path = Path(output)
    if not path.is_absolute():
        raise ValueError("token output must be an absolute operator-selected path outside Git")
    if path.exists() or path.is_symlink():
        raise FileExistsError("token output already exists; refusing overwrite")
    parent = path.parent.resolve(strict=True)
    resolved = parent / path.name
    repository_root = Path(__file__).resolve().parents[2]
    for prohibited, label in ((repository_root, "Git repository"), (package_root, "Workflow Package")):
        try:
            resolved.relative_to(prohibited)
        except ValueError:
            continue
        raise ValueError(f"token output must be outside the {label}")
    return resolved


def _write_once(path: Path, plaintext: str) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise
    except OSError as error:
        raise ValueError("token output could not be created safely") from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", closefd=True) as stream:
            stream.write(plaintext + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o600)
    except BaseException as error:
        path.unlink(missing_ok=True)
        if isinstance(error, OSError):
            raise ValueError("token output could not be written safely") from error
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Issue or revoke an experimental Proxy capability token.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    issue = subcommands.add_parser("issue")
    issue.add_argument("--project-id", required=True)
    issue.add_argument("--package-root", required=True)
    issue.add_argument("--tenant-id", required=True)
    issue.add_argument("--subject-id", required=True)
    issue.add_argument("--output-file", required=True)
    issue.add_argument("--lifetime-minutes", type=int, default=60)
    issue.add_argument("--maximum-operations", type=int)
    issue.add_argument(
        "--adapter-id",
        choices=(ADAPTER_ID, OPENALEX_ADAPTER_ID),
        default=ADAPTER_ID,
    )
    revoke = subcommands.add_parser("revoke")
    revoke.add_argument("--token-id", required=True)
    args = parser.parse_args(argv)
    engine = None
    try:
        service, engine = _service_from_environment()
        if args.command == "revoke":
            token = service.revoke_token(args.token_id)
            result = {"token_id": token.scope.token_id, "revoked": token.revoked, "revoked_at": token.revoked_at}
        else:
            identity = read_validated_package_identity(args.package_root)
            if identity.project_id != args.project_id:
                raise ValueError("operator project identity does not match the Package")
            output = _validate_output_path(args.output_file, identity.root)
            token, plaintext = service.issue_token(
                tenant_id=args.tenant_id,
                subject_id=args.subject_id,
                project_id=identity.project_id,
                package_id=identity.package_id,
                package_checksum=identity.package_checksum,
                workflow_id=identity.workflow_id,
                workflow_version=identity.workflow_version,
                workflow_checksum=identity.workflow_checksum,
                lifetime_minutes=args.lifetime_minutes,
                maximum_operations=args.maximum_operations,
                adapter_id=args.adapter_id,
            )
            try:
                _write_once(output, plaintext)
            except BaseException:
                service.revoke_token(token.scope.token_id)
                raise
            result = {
                "token_id": token.scope.token_id,
                "expires_at": token.expires_at,
                "project_id": token.scope.project_id,
                "package_id": token.scope.package_id,
                "workflow_id": token.scope.workflow_id,
                "maximum_operations": token.scope.maximum_operations,
                "adapter_id": token.scope.adapter_id,
                "maximum_provider_calls": token.scope.maximum_provider_calls,
                "maximum_provider_cost_microusd": token.scope.maximum_provider_cost_microusd,
                "output_file_created": True,
            }
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (ValueError, FileExistsError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
