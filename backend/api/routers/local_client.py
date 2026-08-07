"""Fixed local Workspace client download; never resolves caller-supplied paths."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, Response


router = APIRouter(tags=["local-client"])


@router.get("/local-client/reagent_local.py")
async def download_local_client() -> Response:
    source = Path(__file__).parents[2] / "project_workspaces" / "workspace_cli.py"
    content = source.read_bytes()
    checksum = hashlib.sha256(content).hexdigest()
    return Response(
        content=content,
        media_type="text/x-python; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="reagent_local.py"',
            "ETag": f'"sha256:{checksum}"',
            "X-ReAgent-CLI-SHA256": f"sha256:{checksum}",
            "X-Content-Type-Options": "nosniff",
        },
    )
