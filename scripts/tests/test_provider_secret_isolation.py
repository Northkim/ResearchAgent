from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


PROVIDER_SECRETS = (
    "REAGENT_OPENALEX_API_KEY",
    "OPENALEX_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "REAGENT_PROXY_TOKEN",
    "REAGENT_LOCAL_SESSION_TOKEN",
)


def test_frontend_launcher_removes_provider_secrets_from_child_environment() -> None:
    repo = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    for key in PROVIDER_SECRETS:
        environment[key] = "synthetic-secret-sentinel"
    result = subprocess.run(
        [
            str(repo / "scripts/run-without-provider-secrets.sh"),
            sys.executable,
            "-c",
            (
                "import json, os; "
                "print(json.dumps({key: key in os.environ for key in "
                f"{PROVIDER_SECRETS!r}"
                "}))"
            ),
        ],
        cwd=repo,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == {key: False for key in PROVIDER_SECRETS}


def test_dev_start_uses_scrubbed_launcher_for_every_frontend_process() -> None:
    repo = Path(__file__).resolve().parents[2]
    source = (repo / "scripts/dev-start.sh").read_text(encoding="utf-8")
    assert source.count('"${task_frontend_launcher}"') == 4
    assert "REAGENT_OPENALEX_API_KEY=\"${REAGENT_OPENALEX_API_KEY:-}\"" in source
