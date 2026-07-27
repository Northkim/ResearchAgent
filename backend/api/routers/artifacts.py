"""Artifact metadata and integrity-checked content endpoints."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Response

from ..dependencies import ServicesDependency
from ..schemas import ArtifactResponse

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: str,
    services: ServicesDependency,
) -> ArtifactResponse:
    return ArtifactResponse.from_view(services.get_artifact.execute(artifact_id))


@router.get("/{artifact_id}/content")
async def read_artifact_content(
    artifact_id: str,
    services: ServicesDependency,
) -> Response:
    view = services.read_artifact_content.execute(artifact_id)
    media_type = view.artifact.media_type.split(";", 1)[0]
    disposition = (
        "inline" if media_type in {"application/json", "text/markdown"} else "attachment"
    )
    return Response(
        content=view.content,
        media_type=view.artifact.media_type,
        headers={
            "ETag": f'"{view.artifact.checksum}"',
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": (
                f"{disposition}; filename*=UTF-8''"
                f"{quote(view.artifact.logical_name, safe='')}"
            ),
        },
    )
