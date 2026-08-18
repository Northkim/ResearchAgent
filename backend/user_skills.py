"""Owner-managed Agent Skills, separate from reviewed Capsule Skill publication."""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Callable, Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.application.errors import (
    ApplicationCodedConflictError,
    ApplicationCodedNotFoundError,
    ApplicationCodedUnavailableError,
    ApplicationCodedValidationError,
)
from backend.workflow_packages.serialization import canonical_hash

_ID = re.compile(r"^skill-[0-9a-f]{32}$")
_PROJECT_ID = re.compile(r"^project-[0-9a-f]{32}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
_GITHUB_PART = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
_MAX_FILES = 64
_MAX_BYTES = 1_048_576
_MAX_RESPONSE = 2_097_152
CONTROLLED_SOURCE = "https://github.com/reagent-controlled/sample-research-skill"
CONTROLLED_REVISION = "c" * 40
CONTROLLED_CHECKSUM = "sha256:e304d87ca41f5031f8e65607bfe7d013bfde26bbd118a7592c5077faa248c9fd"


@dataclass(frozen=True, slots=True)
class UserSkill:
    skill_id: str
    name: str
    slug: str
    description: str
    source_locator: str
    source_revision: str
    source_checksum: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.skill_id) or not _SLUG.fullmatch(self.slug):
            raise ValueError("User Skill identity is invalid")
        if not 1 <= len(self.name.strip()) <= 120:
            raise ValueError("User Skill name is invalid")
        if not 1 <= len(self.description.strip()) <= 500:
            raise ValueError("User Skill description is invalid")
        parse_github_skill_locator(self.source_locator)
        if not _REVISION.fullmatch(self.source_revision):
            raise ValueError("User Skill source revision must be an exact commit")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.source_checksum):
            raise ValueError("User Skill source checksum is invalid")
        if any(value.tzinfo is None for value in (self.created_at, self.updated_at)):
            raise ValueError("User Skill timestamps must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ProjectUserSkill:
    project_id: str
    skill_id: str
    reported_source_checksum: str | None
    attached_at: datetime
    reported_at: datetime | None

    def __post_init__(self) -> None:
        if not _PROJECT_ID.fullmatch(self.project_id) or not _ID.fullmatch(self.skill_id):
            raise ValueError("Project Skill identity is invalid")
        if self.attached_at.tzinfo is None:
            raise ValueError("Project Skill timestamp must be timezone-aware")
        if (self.reported_source_checksum is None) != (self.reported_at is None):
            raise ValueError("Project Skill sync report is incomplete")
        if self.reported_source_checksum is not None:
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.reported_source_checksum):
                raise ValueError("Project Skill sync checksum is invalid")
            if self.reported_at is None or self.reported_at.tzinfo is None:
                raise ValueError("Project Skill report timestamp must be timezone-aware")

    @property
    def ready(self) -> bool:
        return self.reported_source_checksum is not None


@dataclass(frozen=True, slots=True)
class GitHubSkillLocator:
    owner: str
    repository: str
    directory: str
    url_revision: str | None


@dataclass(frozen=True, slots=True)
class VerifiedSkillSource:
    exact_revision: str
    source_checksum: str


class UserSkillRepository(Protocol):
    def add_skill(self, value: UserSkill) -> None: ...
    def get_skill(self, skill_id: str) -> UserSkill | None: ...
    def get_skill_by_slug(self, slug: str) -> UserSkill | None: ...
    def list_skills(self) -> tuple[UserSkill, ...]: ...
    def delete_skill(self, skill_id: str) -> None: ...
    def add_project_skill(self, value: ProjectUserSkill) -> None: ...
    def get_project_skill(self, project_id: str, skill_id: str) -> ProjectUserSkill | None: ...
    def list_project_skills(self, project_id: str) -> tuple[ProjectUserSkill, ...]: ...
    def list_skill_projects(self, skill_id: str) -> tuple[ProjectUserSkill, ...]: ...
    def save_project_skill(self, value: ProjectUserSkill) -> None: ...
    def delete_project_skill(self, project_id: str, skill_id: str) -> None: ...


def parse_github_skill_locator(value: str) -> GitHubSkillLocator:
    if not isinstance(value, str) or len(value) > 500:
        raise ValueError("Enter a valid GitHub URL")
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme != "https" or parsed.hostname != "github.com"
        or parsed.username or parsed.password or parsed.port
        or parsed.query or parsed.fragment
    ):
        raise ValueError("Enter a valid GitHub URL")
    parts = [urllib.parse.unquote(item) for item in parsed.path.split("/") if item]
    if len(parts) < 2 or any(not _GITHUB_PART.fullmatch(item) for item in parts[:2]):
        raise ValueError("Enter a valid GitHub URL")
    owner, repository = parts[:2]
    if repository.endswith(".git"):
        repository = repository[:-4]
    url_revision = None
    directory_parts: list[str] = []
    if len(parts) > 2:
        if len(parts) < 5 or parts[2] != "tree" or not _GITHUB_PART.fullmatch(parts[3]):
            raise ValueError("GitHub URL must identify a repository or Skill directory")
        url_revision = parts[3]
        directory_parts = parts[4:]
    directory = PurePosixPath(*directory_parts).as_posix() if directory_parts else ""
    if any(part in {"", ".", ".."} for part in directory_parts):
        raise ValueError("GitHub Skill directory is invalid")
    return GitHubSkillLocator(owner, repository, directory, url_revision)


def _github_json(url: str) -> object:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "ReAgent-Skill-M1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status != 200 or urllib.parse.urlsplit(response.geturl()).hostname != "api.github.com":
                raise OSError("unexpected GitHub response")
            body = response.read(_MAX_RESPONSE + 1)
    except (OSError, urllib.error.HTTPError, urllib.error.URLError) as error:
        raise ApplicationCodedUnavailableError(
            "Could not find SKILL.md at this source.", code="USER_SKILL_SOURCE_UNAVAILABLE"
        ) from error
    if len(body) > _MAX_RESPONSE:
        raise ApplicationCodedValidationError(
            "Skill source is too large.", code="USER_SKILL_SOURCE_TOO_LARGE"
        )
    try:
        return json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ApplicationCodedUnavailableError(
            "Could not read this Skill source.", code="USER_SKILL_SOURCE_UNAVAILABLE"
        ) from error


def resolve_github_skill_source(
    source_locator: str, source_revision: str | None = None
) -> VerifiedSkillSource:
    """Resolve one public GitHub directory without retaining its package bytes."""

    locator = parse_github_skill_locator(source_locator)
    if (
        os.environ.get("REAGENT_AUTOMATED_QUALIFICATION") == "1"
        and source_locator == CONTROLLED_SOURCE
        and source_revision in {None, "main", CONTROLLED_REVISION}
    ):
        return VerifiedSkillSource(CONTROLLED_REVISION, CONTROLLED_CHECKSUM)
    requested = source_revision or locator.url_revision or "HEAD"
    if source_revision is not None and not 1 <= len(source_revision) <= 128:
        raise ApplicationCodedValidationError(
            "Revision is invalid.", code="USER_SKILL_REVISION_INVALID"
        )
    quoted = urllib.parse.quote(requested, safe="")
    root = f"https://api.github.com/repos/{locator.owner}/{locator.repository}"
    commit = _github_json(f"{root}/commits/{quoted}")
    exact = commit.get("sha") if isinstance(commit, dict) else None
    if not isinstance(exact, str) or not _REVISION.fullmatch(exact):
        raise ApplicationCodedUnavailableError(
            "Could not resolve this Skill revision.", code="USER_SKILL_SOURCE_UNAVAILABLE"
        )
    entries: list[dict[str, object]] = []

    def visit(directory: str) -> None:
        path = urllib.parse.quote(directory, safe="/")
        suffix = f"/contents/{path}" if path else "/contents"
        document = _github_json(f"{root}{suffix}?ref={exact}")
        values = document if isinstance(document, list) else [document]
        for item in values:
            if not isinstance(item, dict):
                raise ApplicationCodedUnavailableError(
                    "Could not read this Skill source.", code="USER_SKILL_SOURCE_UNAVAILABLE"
                )
            kind, full_path = item.get("type"), item.get("path")
            if not isinstance(full_path, str):
                raise ApplicationCodedUnavailableError(
                    "Could not read this Skill source.", code="USER_SKILL_SOURCE_UNAVAILABLE"
                )
            if kind == "dir":
                visit(full_path)
                continue
            if kind != "file":
                raise ApplicationCodedValidationError(
                    "Skill source contains an unsupported entry.", code="USER_SKILL_SOURCE_UNSAFE"
                )
            relative = PurePosixPath(full_path).relative_to(
                PurePosixPath(locator.directory) if locator.directory else PurePosixPath(".")
            ).as_posix()
            size, blob = item.get("size"), item.get("sha")
            if (
                not relative or any(part in {"", ".", ".."} for part in PurePosixPath(relative).parts)
                or isinstance(size, bool) or not isinstance(size, int) or size < 0
                or not isinstance(blob, str) or not re.fullmatch(r"[0-9a-f]{40}", blob)
            ):
                raise ApplicationCodedValidationError(
                    "Skill source contains an unsafe path.", code="USER_SKILL_SOURCE_UNSAFE"
                )
            entries.append({"path": relative, "size": size, "blob": blob})
            if len(entries) > _MAX_FILES or sum(int(value["size"]) for value in entries) > _MAX_BYTES:
                raise ApplicationCodedValidationError(
                    "Skill source is too large.", code="USER_SKILL_SOURCE_TOO_LARGE"
                )

    visit(locator.directory)
    if not any(item["path"] == "SKILL.md" for item in entries):
        raise ApplicationCodedValidationError(
            "Could not find SKILL.md at this source.", code="USER_SKILL_DOCUMENT_MISSING"
        )
    entries.sort(key=lambda item: str(item["path"]))
    return VerifiedSkillSource(exact, canonical_hash({"files": entries}))


class UserSkillService:
    def __init__(
        self,
        *,
        repository: UserSkillRepository,
        project_exists: Callable[[str], bool],
        commit: Callable[[], None],
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        source_resolver: Callable[[str, str | None], VerifiedSkillSource] = resolve_github_skill_source,
        id_factory: Callable[[], str] = lambda: "skill-" + uuid.uuid4().hex,
    ) -> None:
        self._repository = repository
        self._project_exists = project_exists
        self._commit = commit
        self._clock = clock
        self._source_resolver = source_resolver
        self._id_factory = id_factory

    def create(self, *, name: str, description: str, source_locator: str, source_revision: str | None = None) -> UserSkill:
        name, description, source_locator = name.strip(), description.strip(), source_locator.strip()
        if not name:
            raise ApplicationCodedValidationError("Skill name is required.", code="USER_SKILL_NAME_REQUIRED")
        if not description:
            raise ApplicationCodedValidationError("Skill purpose is required.", code="USER_SKILL_DESCRIPTION_REQUIRED")
        try:
            parse_github_skill_locator(source_locator)
        except ValueError as error:
            raise ApplicationCodedValidationError(str(error), code="USER_SKILL_SOURCE_INVALID") from error
        verified = self._source_resolver(source_locator, source_revision)
        skill_id = self._id_factory()
        slug = _slug(name)
        if self._repository.get_skill_by_slug(slug) is not None:
            slug = f"{slug[:70]}-{skill_id[-8:]}"
        now = self._clock()
        value = UserSkill(
            skill_id, name, slug, description, source_locator,
            verified.exact_revision, verified.source_checksum, now, now,
        )
        self._repository.add_skill(value)
        self._commit()
        return value

    def list(self) -> tuple[UserSkill, ...]:
        return self._repository.list_skills()

    def get(self, skill_id: str) -> UserSkill:
        value = self._repository.get_skill(skill_id)
        if value is None:
            raise ApplicationCodedNotFoundError("Skill not found.", code="USER_SKILL_NOT_FOUND")
        return value

    def usage_count(self, skill_id: str) -> int:
        return len(self._repository.list_skill_projects(skill_id))

    def delete(self, skill_id: str) -> None:
        self.get(skill_id)
        count = self.usage_count(skill_id)
        if count:
            raise ApplicationCodedConflictError(
                f"This skill is used by {count} project{'s' if count != 1 else ''}. Remove it from those projects first.",
                code="USER_SKILL_IN_USE",
            )
        self._repository.delete_skill(skill_id)
        self._commit()

    def list_project(self, project_id: str) -> tuple[tuple[UserSkill, ProjectUserSkill], ...]:
        self._require_project(project_id)
        return tuple((self.get(item.skill_id), item) for item in self._repository.list_project_skills(project_id))

    def attach(self, project_id: str, skill_id: str) -> ProjectUserSkill:
        self._require_project(project_id)
        self.get(skill_id)
        existing = self._repository.get_project_skill(project_id, skill_id)
        if existing is not None:
            return existing
        value = ProjectUserSkill(project_id, skill_id, None, self._clock(), None)
        self._repository.add_project_skill(value)
        self._commit()
        return value

    def detach(self, project_id: str, skill_id: str) -> None:
        self._require_project(project_id)
        if self._repository.get_project_skill(project_id, skill_id) is not None:
            self._repository.delete_project_skill(project_id, skill_id)
            self._commit()

    def acknowledge(self, project_id: str, installed: tuple[dict[str, str], ...]) -> None:
        selected = self.list_project(project_id)
        expected = {skill.skill_id: skill.source_checksum for skill, _ in selected}
        if any(set(item) != {"skill_id", "source_checksum"} for item in installed):
            raise ApplicationCodedConflictError(
                "Local Skill report does not match the Project selection.",
                code="USER_SKILL_SYNC_CONFLICT",
            )
        supplied = {item.get("skill_id"): item.get("source_checksum") for item in installed}
        if supplied != expected or len(supplied) != len(installed):
            raise ApplicationCodedConflictError(
                "Local Skill report does not match the Project selection.", code="USER_SKILL_SYNC_CONFLICT"
            )
        now = self._clock()
        for skill, association in selected:
            self._repository.save_project_skill(replace(
                association, reported_source_checksum=skill.source_checksum, reported_at=now
            ))
        self._commit()

    def _require_project(self, project_id: str) -> None:
        if not _PROJECT_ID.fullmatch(project_id) or not self._project_exists(project_id):
            raise ApplicationCodedNotFoundError("Project not found.", code="PROJECT_NOT_FOUND")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:80]
    return slug or "skill"


class InMemoryUserSkillRepository:
    def __init__(self, unit_of_work) -> None:
        self._uow = unit_of_work

    @property
    def skills(self): return self._uow._user_skills
    @property
    def project_skills(self): return self._uow._project_user_skills

    def add_skill(self, value): self.skills[value.skill_id] = value
    def get_skill(self, skill_id): return self.skills.get(skill_id)
    def get_skill_by_slug(self, slug): return next((v for v in self.skills.values() if v.slug == slug), None)
    def list_skills(self): return tuple(sorted(self.skills.values(), key=lambda v: (v.name.casefold(), v.skill_id)))
    def delete_skill(self, skill_id): self.skills.pop(skill_id, None)
    def add_project_skill(self, value): self.project_skills[(value.project_id, value.skill_id)] = value
    def get_project_skill(self, project_id, skill_id): return self.project_skills.get((project_id, skill_id))
    def list_project_skills(self, project_id): return tuple(sorted((v for v in self.project_skills.values() if v.project_id == project_id), key=lambda v: v.skill_id))
    def list_skill_projects(self, skill_id): return tuple(v for v in self.project_skills.values() if v.skill_id == skill_id)
    def save_project_skill(self, value): self.add_project_skill(value)
    def delete_project_skill(self, project_id, skill_id): self.project_skills.pop((project_id, skill_id), None)


class SQLAlchemyUserSkillRepository:
    def __init__(self, session: Session) -> None:
        from backend.database.orm.models import ProjectUserSkillORM, UserManagedSkillORM

        self.session = session
        self.ProjectUserSkillORM = ProjectUserSkillORM
        self.UserManagedSkillORM = UserManagedSkillORM

    def add_skill(self, value: UserSkill) -> None:
        self.session.add(self.UserManagedSkillORM(
            skill_id=value.skill_id, name=value.name, slug=value.slug,
            description=value.description, source_locator=value.source_locator,
            source_revision=value.source_revision, source_checksum=value.source_checksum,
            created_at=value.created_at, updated_at=value.updated_at,
        ))

    def get_skill(self, skill_id):
        row = self.session.get(self.UserManagedSkillORM, skill_id)
        return None if row is None else _skill(row)

    def get_skill_by_slug(self, slug):
        row = self.session.scalar(select(self.UserManagedSkillORM).where(
            self.UserManagedSkillORM.slug == slug
        ))
        return None if row is None else _skill(row)

    def list_skills(self):
        rows = self.session.scalars(select(self.UserManagedSkillORM).order_by(
            self.UserManagedSkillORM.name, self.UserManagedSkillORM.skill_id
        ))
        return tuple(_skill(row) for row in rows)

    def delete_skill(self, skill_id):
        self.session.execute(delete(self.UserManagedSkillORM).where(
            self.UserManagedSkillORM.skill_id == skill_id
        ))

    def add_project_skill(self, value):
        self.session.add(self.ProjectUserSkillORM(
            project_id=value.project_id, skill_id=value.skill_id,
            reported_source_checksum=value.reported_source_checksum,
            attached_at=value.attached_at, reported_at=value.reported_at,
        ))

    def get_project_skill(self, project_id, skill_id):
        row = self.session.get(self.ProjectUserSkillORM, (project_id, skill_id))
        return None if row is None else _project_skill(row)

    def list_project_skills(self, project_id):
        rows = self.session.scalars(select(self.ProjectUserSkillORM).where(
            self.ProjectUserSkillORM.project_id == project_id
        ).order_by(self.ProjectUserSkillORM.skill_id))
        return tuple(_project_skill(row) for row in rows)

    def list_skill_projects(self, skill_id):
        rows = self.session.scalars(select(self.ProjectUserSkillORM).where(
            self.ProjectUserSkillORM.skill_id == skill_id
        ).order_by(self.ProjectUserSkillORM.project_id))
        return tuple(_project_skill(row) for row in rows)

    def save_project_skill(self, value):
        row = self.session.get(
            self.ProjectUserSkillORM, (value.project_id, value.skill_id)
        )
        if row is None:
            self.add_project_skill(value)
        else:
            row.reported_source_checksum, row.reported_at = value.reported_source_checksum, value.reported_at

    def delete_project_skill(self, project_id, skill_id):
        self.session.execute(delete(self.ProjectUserSkillORM).where(
            self.ProjectUserSkillORM.project_id == project_id,
            self.ProjectUserSkillORM.skill_id == skill_id,
        ))


def _skill(row) -> UserSkill:
    return UserSkill(row.skill_id, row.name, row.slug, row.description, row.source_locator,
                     row.source_revision, row.source_checksum, row.created_at, row.updated_at)


def _project_skill(row) -> ProjectUserSkill:
    return ProjectUserSkill(row.project_id, row.skill_id, row.reported_source_checksum,
                            row.attached_at, row.reported_at)
