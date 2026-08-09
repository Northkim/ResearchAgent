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
    commands.add_parser(
        "skill-list", help="list reviewed built-in Skill assets (operator read-only)"
    )
    show = commands.add_parser(
        "skill-show", help="inspect one reviewed built-in Skill version"
    )
    show.add_argument("skill_id")
    show.add_argument("--version", default="0.1.0")
    verify = commands.add_parser(
        "skill-verify", help="verify reviewed built-in Skill manifests and checksums"
    )
    verify.add_argument("skill_id", nargs="?")
    verify.add_argument("--version", default="0.1.0")
    return parser


def _skill_value(asset) -> dict[str, object]:
    return {
        "skill_id": asset.skill_id,
        "display_name": asset.display_name,
        "version": asset.version,
        "trust": "BUILT_IN_REVIEWED",
        "content_checksum": asset.content_checksum,
        "manifest_schema_version": "local-skill/v0.1",
        "content_source_identity": asset.content_source_identity,
    }


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
    elif args.command == "validate":
        result = validate_archive(args.path, pristine=args.pristine) if args.archive else validate_package(args.path, pristine=args.pristine)
        value = {
            "package_id": result.package_id,
            "package_checksum": result.package_checksum,
            "manifest_checksum": result.manifest_checksum,
            "validation_result": "PASS",
            "harness_acceptance_status": result.harness_acceptance_status,
        }
    else:
        from backend.project_workspaces.skills import (
            PRODUCTION_SKILLS,
            production_skill_asset,
            validate_skill_content_files,
        )

        if args.command == "skill-list":
            value = {
                "skills": [
                    _skill_value(asset)
                    for asset in sorted(PRODUCTION_SKILLS, key=lambda item: item.skill_id)
                ],
                "mutation_supported": False,
            }
        elif args.command == "skill-show":
            value = _skill_value(production_skill_asset(args.skill_id, args.version))
        else:
            assets = (
                (production_skill_asset(args.skill_id, args.version),)
                if args.skill_id else PRODUCTION_SKILLS
            )
            verified = []
            for asset in assets:
                validate_skill_content_files(asset.content_files())
                verified.append(_skill_value(asset))
            value = {"validation_result": "PASS", "skills": verified}
    print(json.dumps(value, sort_keys=True))
    return 0
