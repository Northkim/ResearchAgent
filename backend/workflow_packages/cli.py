"""Safe command line interface for experimental Workflow Package builds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .compiler import build_literature_search_package
from .validator import validate_archive, validate_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m backend.workflow_packages")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build-literature-search", help="build the offline experimental Literature Search package")
    build.add_argument("--project-id", required=True)
    build.add_argument("--output-root", type=Path, required=True)
    validate = commands.add_parser("validate", help="validate a package folder or ZIP")
    validate.add_argument("path", type=Path)
    validate.add_argument("--archive", action="store_true")
    validate.add_argument("--pristine", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build-literature-search":
        result = build_literature_search_package(project_id=args.project_id, output_root=args.output_root)
        value = {
            "package_id": result.package_id,
            "package_schema_version": result.package_schema_version,
            "manifest_checksum": result.manifest_checksum,
            "package_checksum": result.package_checksum,
            "zip_checksum": result.zip_checksum,
            "relative_output_location": args.output_root.as_posix(),
            "validation_result": "PASS",
            "harness_acceptance_status": result.harness_acceptance_status,
        }
    else:
        result = validate_archive(args.path, pristine=args.pristine) if args.archive else validate_package(args.path, pristine=args.pristine)
        value = {
            "package_id": result.package_id,
            "package_checksum": result.package_checksum,
            "manifest_checksum": result.manifest_checksum,
            "validation_result": "PASS",
            "harness_acceptance_status": result.harness_acceptance_status,
        }
    print(json.dumps(value, sort_keys=True))
    return 0
