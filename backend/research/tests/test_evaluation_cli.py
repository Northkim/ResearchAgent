from __future__ import annotations

from backend.research.evaluation.cli import main


def test_cli_initializes_ignored_style_root_without_network(tmp_path, capsys) -> None:
    root = tmp_path / "evaluations"
    exit_code = main(
        [
            "--root",
            str(root),
            "initialize",
            "cli-evaluation",
        ]
    )
    assert exit_code == 0
    assert "initialized" in capsys.readouterr().out
    assert (
        tmp_path / "evaluations" / "cli-evaluation" / "evaluation_config.json"
    ).is_file()
    status_exit = main(
        [
            "--root",
            str(root),
            "status",
            "cli-evaluation",
        ]
    )
    assert status_exit == 0
    status = capsys.readouterr().out
    assert '"completion_state": "INITIALIZED"' in status
    assert '"human_labels_generated_by_system": false' in status


def test_cli_candidate_generation_refuses_missing_live_opt_in(tmp_path, capsys) -> None:
    exit_code = main(
        [
            "--root",
            str(tmp_path / "evaluations"),
            "generate",
            "cli-evaluation",
            "--topic",
            "cs-persistent-agents",
        ]
    )
    assert exit_code == 1
    assert "explicit --live" in capsys.readouterr().err


def test_cli_live_generation_requires_frozen_initialization(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    monkeypatch.setenv("REAGENT_OPENALEX_API_KEY", "synthetic-cli-only")
    exit_code = main(
        [
            "--root",
            str(tmp_path / "evaluations"),
            "generate",
            "not-initialized",
            "--live",
            "--topic",
            "cs-persistent-agents",
        ]
    )
    assert exit_code == 1
    error = capsys.readouterr().err
    assert "FileNotFoundError" in error
    assert "synthetic-cli-only" not in error


def test_cli_live_generation_refuses_implicit_full_topic_set(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    monkeypatch.setenv("REAGENT_OPENALEX_API_KEY", "synthetic-cli-only")
    exit_code = main(
        [
            "--root",
            str(tmp_path / "evaluations"),
            "generate",
            "implicit-full-set",
            "--live",
        ]
    )
    assert exit_code == 1
    error = capsys.readouterr().err
    assert "one to three explicit --topic" in error
    assert "synthetic-cli-only" not in error
