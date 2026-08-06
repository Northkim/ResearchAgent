from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.workspace_cli import WorkspaceCLIError
from backend.workflow_packages import validate_package


@pytest.fixture
def workspace_fixture(tmp_path: Path):
    database = InMemoryDatabase()
    package_root = tmp_path / "cloud-packages"
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(package_root),
    )
    client = TestClient(create_app(container))
    project = client.post(
        "/projects",
        json={
            "name": "Workspace qualification",
            "research_topic": "Fictional portable research continuity",
            "selected_workflow": "LITERATURE_SEARCH",
        },
    )
    assert project.status_code == 201
    project_id = project.json()["project_id"]
    generated = client.post(f"/projects/{project_id}/packages")
    assert generated.status_code == 201
    descriptor = client.get(f"/projects/{project_id}/workspace-bootstrap")
    assert descriptor.status_code == 200
    source = package_root / project_id / "literature-search-v0.5" / "package"
    archive = package_root / project_id / "literature-search-v0.5" / (
        generated.json()["package_id"] + ".zip"
    )
    assert source.is_dir() and archive.is_file()
    return {
        "client": client,
        "project_id": project_id,
        "descriptor": descriptor.json(),
        "source": source,
        "archive": archive,
    }


def test_bootstrap_creates_frozen_minimal_layout_and_is_idempotent(
    tmp_path: Path,
    workspace_fixture,
) -> None:
    target = tmp_path / "workspace"
    first = workspace_cli.bootstrap_workspace(
        target=target,
        descriptor=workspace_fixture["descriptor"],
        now=datetime(2026, 8, 7, tzinfo=timezone.utc),
    )
    assert first.status == "CREATED"
    assert (target / "project.json").is_file()
    assert (target / "AGENT.md").is_file()
    assert (target / "reagent_local.py").is_file()
    assert (target / ".reagent/bootstrap.json").is_file()
    assert (target / ".reagent/desired-manifest.json").is_file()
    assert (target / ".reagent/capsule-registry.json").is_file()
    assert (target / "capsules").is_dir()
    assert not (target / ".reagent/installed-lock.json").exists()
    assert not (target / ".reagent/acknowledgements").exists()
    assert not (target / ".reagent/sync").exists()
    descriptor = workspace_cli.validate_workspace_descriptor(
        json.loads((target / "project.json").read_text())
    )
    assert descriptor["project_id"] == workspace_fixture["project_id"]
    assert descriptor["workspace_id"] == workspace_fixture["descriptor"]["workspace_id"]

    second = workspace_cli.bootstrap_workspace(
        target=target,
        descriptor=workspace_fixture["descriptor"],
    )
    assert second.status == "ALREADY_BOOTSTRAPPED"
    assert json.loads((target / "project.json").read_text()) == descriptor
    status = subprocess.run(
        [sys.executable, str(target / "reagent_local.py"), "workspace", "status", str(target), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert status.returncode == 0
    assert json.loads(status.stdout)["workspace_id"] == descriptor["workspace_id"]


def test_bootstrap_conflict_corruption_and_interrupted_write_are_fail_closed(
    tmp_path: Path,
    workspace_fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=target, descriptor=workspace_fixture["descriptor"])
    second_project = workspace_fixture["client"].post(
        "/projects",
        json={
            "name": "Other",
            "research_topic": "Other fictional topic",
            "selected_workflow": "LITERATURE_SEARCH",
        },
    ).json()["project_id"]
    conflicting = workspace_fixture["client"].get(
        f"/projects/{second_project}/workspace-bootstrap"
    ).json()
    with pytest.raises(WorkspaceCLIError, match="another Project Workspace") as error:
        workspace_cli.bootstrap_workspace(target=target, descriptor=conflicting)
    assert error.value.code == "WORKSPACE_IDENTITY_CONFLICT"

    (target / "project.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.bootstrap_workspace(target=target, descriptor=workspace_fixture["descriptor"])
    assert error.value.code == "WORKSPACE_DESCRIPTOR_INVALID"

    failed_target = tmp_path / "failed-workspace"
    original = workspace_cli._atomic_write_bytes

    def fail_descriptor(path: Path, content: bytes, *, mode: int) -> None:
        if path.name == "project.json":
            raise OSError("injected")
        original(path, content, mode=mode)

    monkeypatch.setattr(workspace_cli, "_atomic_write_bytes", fail_descriptor)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.bootstrap_workspace(
            target=failed_target,
            descriptor=workspace_fixture["descriptor"],
        )
    assert error.value.code == "FILESYSTEM_OPERATION_FAILED"
    assert not (failed_target / "project.json").exists()
    assert not list(tmp_path.glob(".reagent-bootstrap-*"))


def test_adoption_preserves_source_mutable_state_and_legacy_launcher(
    tmp_path: Path,
    workspace_fixture,
) -> None:
    source = workspace_fixture["source"]
    (source / ".DS_Store").write_bytes(b"harmless metadata")
    (source / "outputs/search_plan.md").write_text(
        """# Search plan
## Interpreted topic
Portable research state.
## Concepts and synonyms
Continuity and handoff.
## Query variants
One bounded query.
## Search bounds
One call.
## Screening rules
Direct relevance.
## Evidence limitations
Metadata and abstracts only.
""",
        encoding="utf-8",
    )
    source_hash = workspace_cli._tree_checksum(source)
    target = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=target, descriptor=workspace_fixture["descriptor"])
    adopted = workspace_cli.adopt_legacy_package(
        source=source,
        workspace_root=target,
        now=datetime(2026, 8, 7, 1, tzinfo=timezone.utc),
    )
    assert adopted.status == "ADOPTED"
    capsule = target / str(adopted.capsule_relative_path)
    assert workspace_cli._tree_checksum(source) == source_hash
    assert workspace_cli._tree_checksum(capsule) == source_hash
    assert (capsule / "memory/context.md").read_bytes() == (source / "memory/context.md").read_bytes()
    assert (capsule / "memory/progress/report-draft.json").read_bytes() == (
        source / "memory/progress/report-draft.json"
    ).read_bytes()
    assert (capsule / ".DS_Store").read_bytes() == b"harmless metadata"
    assert (capsule / "outputs/search_plan.md").read_bytes() == (
        source / "outputs/search_plan.md"
    ).read_bytes()
    assert validate_package(capsule).valid is True
    launcher = subprocess.run(
        [sys.executable, str(capsule / "reagent_local.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert launcher.returncode == 0
    assert "run" in launcher.stdout
    package_manifest = json.loads((capsule / "package-manifest.json").read_text())
    project_input = json.loads((capsule / "inputs/project.json").read_text())
    assert package_manifest["experimental_project_identity"] == workspace_fixture["project_id"]
    assert project_input["project_id"] == workspace_fixture["project_id"]

    repeated = workspace_cli.adopt_legacy_package(source=source, workspace_root=target)
    assert repeated.status == "ALREADY_ADOPTED"
    assert workspace_cli._tree_checksum(capsule) == source_hash


def test_archive_adoption_and_identity_checksum_conflicts(
    tmp_path: Path,
    workspace_fixture,
) -> None:
    target = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=target, descriptor=workspace_fixture["descriptor"])
    adopted = workspace_cli.adopt_legacy_package(
        source=workspace_fixture["archive"],
        workspace_root=target,
    )
    assert adopted.status == "ADOPTED"

    repacked = tmp_path / "repacked.zip"
    repacked.write_bytes(workspace_fixture["archive"].read_bytes() + b"different archive")
    fresh_archive_workspace = tmp_path / "fresh-archive"
    workspace_cli.bootstrap_workspace(
        target=fresh_archive_workspace,
        descriptor=workspace_fixture["descriptor"],
    )
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.adopt_legacy_package(
            source=repacked,
            workspace_root=fresh_archive_workspace,
        )
    assert error.value.code == "LEGACY_PACKAGE_CHECKSUM_MISMATCH"

    other_project = workspace_fixture["client"].post(
        "/projects",
        json={
            "name": "Other",
            "research_topic": "Other fictional topic",
            "selected_workflow": "LITERATURE_SEARCH",
        },
    ).json()["project_id"]
    other_descriptor = workspace_fixture["client"].get(
        f"/projects/{other_project}/workspace-bootstrap"
    ).json()
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.adopt_legacy_package(
            source=workspace_fixture["source"],
            workspace_root=target,
            bootstrap_descriptor=other_descriptor,
        )
    assert error.value.code == "WORKSPACE_IDENTITY_CONFLICT"

    source = workspace_fixture["source"]
    agent = source / "AGENT.md"
    original = agent.read_bytes()
    agent.write_bytes(original + b"\nchanged")
    fresh = tmp_path / "fresh"
    workspace_cli.bootstrap_workspace(target=fresh, descriptor=workspace_fixture["descriptor"])
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.adopt_legacy_package(source=source, workspace_root=fresh)
    assert error.value.code == "LEGACY_PACKAGE_CHECKSUM_MISMATCH"
    agent.write_bytes(original)


def test_filesystem_attacks_and_copy_failure_do_not_publish_capsule(
    tmp_path: Path,
    workspace_fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=target, descriptor=workspace_fixture["descriptor"])
    source = workspace_fixture["source"]
    escape = tmp_path / "outside.txt"
    escape.write_text("outside", encoding="utf-8")
    (source / "escape-link").symlink_to(escape)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.adopt_legacy_package(source=source, workspace_root=target)
    assert error.value.code == "UNSAFE_PACKAGE_PATH"
    (source / "escape-link").unlink()

    hardlink = source / "hardlink"
    os.link(source / "AGENT.md", hardlink)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.adopt_legacy_package(source=source, workspace_root=target)
    assert error.value.code == "UNSAFE_PACKAGE_PATH"
    hardlink.unlink()

    malicious = tmp_path / "malicious.zip"
    with zipfile.ZipFile(malicious, "w") as archive:
        archive.writestr("../escape", b"unsafe")
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.adopt_legacy_package(source=malicious, workspace_root=target)
    assert error.value.code == "UNSAFE_PACKAGE_PATH"
    assert escape.read_text() == "outside"

    original_copy = workspace_cli._copy_file
    calls = 0

    def fail_copy(input_path: Path, output_path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected")
        original_copy(input_path, output_path)

    monkeypatch.setattr(workspace_cli, "_copy_file", fail_copy)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.adopt_legacy_package(source=source, workspace_root=target)
    assert error.value.code == "FILESYSTEM_OPERATION_FAILED"
    assert not list((target / "capsules").rglob(".reagent-adopt-*"))
    registry = json.loads((target / ".reagent/capsule-registry.json").read_text())
    assert registry["entries"] == []


def test_descriptor_pin_tampering_and_workspace_target_symlinks_fail_closed(
    tmp_path: Path,
    workspace_fixture,
) -> None:
    tampered = json.loads(json.dumps(workspace_fixture["descriptor"]))
    tampered["workflow_capsules"][0]["workflow_instance_id"] = "wfi-" + "a" * 32
    payload = dict(tampered)
    payload.pop("descriptor_checksum")
    tampered["descriptor_checksum"] = workspace_cli.canonical_hash(payload)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.validate_bootstrap_descriptor(tampered)
    assert error.value.code == "WORKSPACE_DESCRIPTOR_INVALID"

    outside = tmp_path / "outside"
    outside.mkdir()
    target_link = tmp_path / "workspace-link"
    target_link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.bootstrap_workspace(
            target=target_link,
            descriptor=workspace_fixture["descriptor"],
        )
    assert error.value.code == "UNSAFE_PACKAGE_PATH"
    assert list(outside.iterdir()) == []

    target = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=target, descriptor=workspace_fixture["descriptor"])
    workflow_root = target / "capsules" / workspace_cli.WORKFLOW_ID
    workflow_root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.adopt_legacy_package(
            source=workspace_fixture["source"],
            workspace_root=target,
        )
    assert error.value.code == "UNSAFE_PACKAGE_PATH"
    assert list(outside.iterdir()) == []


def test_malformed_missing_duplicate_and_special_character_package_paths(
    tmp_path: Path,
    workspace_fixture,
) -> None:
    target = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=target, descriptor=workspace_fixture["descriptor"])

    special = tmp_path / "special"
    shutil.copytree(workspace_fixture["source"], special)
    special_path = special / "memory/search/operations/结果.json"
    special_path.write_text("{}", encoding="utf-8")
    adopted = workspace_cli.adopt_legacy_package(source=special, workspace_root=target)
    assert (target / str(adopted.capsule_relative_path) / "memory/search/operations/结果.json").is_file()

    for name, mutate, code in (
        (
            "malformed",
            lambda root: (root / "package-manifest.json").write_text("{", encoding="utf-8"),
            "LEGACY_PACKAGE_UNSUPPORTED",
        ),
        (
            "missing",
            lambda root: (root / "AGENT.md").unlink(),
            "LEGACY_PACKAGE_UNSUPPORTED",
        ),
        (
            "duplicate",
            lambda root: _duplicate_manifest_entry(root),
            "UNSAFE_PACKAGE_PATH",
        ),
    ):
        source = tmp_path / name
        shutil.copytree(workspace_fixture["source"], source)
        mutate(source)
        fresh = tmp_path / f"workspace-{name}"
        workspace_cli.bootstrap_workspace(target=fresh, descriptor=workspace_fixture["descriptor"])
        with pytest.raises(WorkspaceCLIError) as error:
            workspace_cli.adopt_legacy_package(source=source, workspace_root=fresh)
        assert error.value.code == code


def _duplicate_manifest_entry(root: Path) -> None:
    path = root / "package-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["files"].append(dict(manifest["files"][0]))
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_archive_absolute_case_collision_and_nested_symlink_are_rejected(
    tmp_path: Path,
    workspace_fixture,
) -> None:
    target = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=target, descriptor=workspace_fixture["descriptor"])
    archives = {
        "absolute.zip": [("/absolute", b"x")],
        "case.zip": [("Foo", b"x"), ("foo", b"y")],
        "windows.zip": [("C:/escape", b"x")],
    }
    for filename, entries in archives.items():
        archive_path = tmp_path / filename
        with zipfile.ZipFile(archive_path, "w") as archive:
            for path, content in entries:
                archive.writestr(path, content)
        with pytest.raises(WorkspaceCLIError) as error:
            workspace_cli.adopt_legacy_package(source=archive_path, workspace_root=target)
        assert error.value.code == "UNSAFE_PACKAGE_PATH"

    nested = tmp_path / "nested"
    shutil.copytree(workspace_fixture["source"], nested)
    (nested / "memory/search/nested-link").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.adopt_legacy_package(source=nested, workspace_root=target)
    assert error.value.code == "UNSAFE_PACKAGE_PATH"


def test_existing_different_capsule_and_registry_recovery_are_explicit(
    tmp_path: Path,
    workspace_fixture,
) -> None:
    target = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=target, descriptor=workspace_fixture["descriptor"])
    manifest = json.loads((workspace_fixture["source"] / "package-manifest.json").read_text())
    capsule_pin = workspace_fixture["descriptor"]["workflow_capsules"][0]
    relative = (
        f"capsules/{capsule_pin['workflow_definition_id']}/"
        f"{capsule_pin['workflow_instance_id']}/{capsule_pin['capsule_version']}"
    )
    destination = target / relative
    destination.mkdir(parents=True)
    (destination / "different.txt").write_text("different", encoding="utf-8")
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.adopt_legacy_package(
            source=workspace_fixture["source"],
            workspace_root=target,
        )
    assert error.value.code in {"LEGACY_PACKAGE_UNSUPPORTED", "CAPSULE_ADOPTION_CONFLICT"}

    shutil.rmtree(destination)
    shutil.copytree(workspace_fixture["source"], destination)
    recovered = workspace_cli.adopt_legacy_package(
        source=workspace_fixture["source"],
        workspace_root=target,
    )
    assert recovered.status == "ALREADY_ADOPTED"
    registry = json.loads((target / ".reagent/capsule-registry.json").read_text())
    assert registry["entries"][0]["package_id"] == manifest["package_id"]


def test_runtime_schema_documents_parse_and_reject_unknown_major(tmp_path: Path, workspace_fixture) -> None:
    schema_root = Path(workspace_cli.__file__).with_name("schemas")
    assert len(list(schema_root.glob("*.schema.json"))) == 3
    for path in schema_root.glob("*.schema.json"):
        assert json.loads(path.read_text())["$schema"].endswith("2020-12/schema")
    unsupported = dict(workspace_fixture["descriptor"])
    unsupported["workspace_schema_version"] = "reagent.project-workspace/v1.0"
    payload = dict(unsupported)
    payload.pop("descriptor_checksum")
    unsupported["descriptor_checksum"] = workspace_cli.canonical_hash(payload)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.bootstrap_workspace(target=tmp_path / "unsupported", descriptor=unsupported)
    assert error.value.code == "WORKSPACE_SCHEMA_UNSUPPORTED"


def test_bootstrap_rejects_file_target_nonempty_partial_and_bad_descriptor(
    tmp_path: Path,
    workspace_fixture,
) -> None:
    file_target = tmp_path / "file-target"
    file_target.write_text("not a workspace", encoding="utf-8")
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.bootstrap_workspace(
            target=file_target,
            descriptor=workspace_fixture["descriptor"],
        )
    assert error.value.code == "FILESYSTEM_OPERATION_FAILED"

    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "unrelated.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.bootstrap_workspace(
            target=partial,
            descriptor=workspace_fixture["descriptor"],
        )
    assert error.value.code == "WORKSPACE_PARTIAL_STATE"
    assert (partial / "unrelated.txt").read_text() == "preserve"

    bad = dict(workspace_fixture["descriptor"])
    bad["unexpected"] = True
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.bootstrap_workspace(target=tmp_path / "bad", descriptor=bad)
    assert error.value.code == "WORKSPACE_DESCRIPTOR_INVALID"


def test_cli_json_output_and_stable_validation_exit_code(
    tmp_path: Path,
    workspace_fixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    descriptor_path = tmp_path / "bootstrap.json"
    descriptor_path.write_text(json.dumps(workspace_fixture["descriptor"]), encoding="utf-8")
    target = tmp_path / "workspace"
    assert workspace_cli.main(
        ["bootstrap", str(target), "--descriptor", str(descriptor_path), "--json"]
    ) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "CREATED"

    broken = tmp_path / "broken.json"
    broken.write_text("{}", encoding="utf-8")
    assert workspace_cli.main(
        ["bootstrap", str(tmp_path / "bad"), "--descriptor", str(broken)]
    ) == workspace_cli.EXIT_IDENTITY
    error_output = capsys.readouterr().err
    assert "WORKSPACE_DESCRIPTOR_INVALID" in error_output
    assert "token" not in error_output.casefold()
