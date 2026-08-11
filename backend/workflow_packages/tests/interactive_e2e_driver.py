#!/usr/bin/env python3
"""Drive the deterministic Codex fixture through a real controlling PTY."""

from __future__ import annotations

import argparse
import errno
import os
import pty
import select
import signal
import sys
import time
from pathlib import Path


RESPONSES = (
    (b"CHECKPOINT: SEARCH PLAN", b"proceed\n"),
    (b"CHECKPOINT: CANDIDATE SCREENING", b"continue\n"),
    (b"CHECKPOINT: FINALIZATION", b"finish\n"),
)


def drive(
    command: list[str],
    *,
    cwd: Path,
    package_root: Path,
    timeout: float,
    interrupt_at: str | None,
    resume: bool,
) -> int:
    pid, descriptor = pty.fork()
    if pid == 0:
        os.chdir(cwd)
        os.execvpe(command[0], command, os.environ)
    buffer = b""
    responses = RESPONSES[1:] if resume else RESPONSES
    next_response = 0
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([descriptor], [], [], 0.2)
            if ready:
                try:
                    chunk = os.read(descriptor, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                os.write(sys.stdout.fileno(), chunk)
                buffer = (buffer + chunk)[-262144:]
                if next_response < len(responses):
                    marker, response = responses[next_response]
                    if marker in buffer:
                        response_index = next_response + (1 if resume else 0)
                        stage = ("search-plan", "candidate", "finalization")[response_index]
                        results = list(
                            (package_root / "memory/search/operations").glob("query-*.result.json")
                        )
                        final_outputs = (
                            package_root / "outputs/candidate_papers.json",
                            package_root / "outputs/selected_papers.json",
                            package_root / "outputs/literature_search_report.md",
                        )
                        if stage == "search-plan" and results:
                            raise AssertionError(
                                "Provider result existed before plan confirmation"
                            )
                        if stage in {"candidate", "finalization"} and not results:
                            raise AssertionError(
                                "candidate checkpoint started without normalized results"
                            )
                        if stage in {"candidate", "finalization"} and any(
                            path.exists() for path in final_outputs
                        ):
                            raise AssertionError(
                                "final output existed before explicit finalization"
                            )
                        if interrupt_at == stage:
                            os.kill(pid, signal.SIGINT)
                        else:
                            os.write(descriptor, response)
                        next_response += 1
                        buffer = b""
            waited, status = os.waitpid(pid, os.WNOHANG)
            if waited == pid:
                return os.waitstatus_to_exitcode(status)
        else:
            os.kill(pid, 2)
            time.sleep(0.5)
            os.kill(pid, 9)
            raise TimeoutError("interactive E2E driver timed out")
        _, status = os.waitpid(pid, 0)
        return os.waitstatus_to_exitcode(status)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--package-root", type=Path)
    target.add_argument("--workspace-root", type=Path)
    parser.add_argument(
        "--capsule-root",
        type=Path,
        help="installed Capsule root when driving the generic Workspace command",
    )
    parser.add_argument(
        "--workflow",
        default="literature-search-local-experimental",
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument(
        "--interrupt-at",
        choices=("search-plan", "candidate", "finalization"),
    )
    parser.add_argument("--expect-exit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.workspace_root is not None:
        if args.capsule_root is None:
            parser.error("--capsule-root is required with --workspace-root")
        cwd = args.workspace_root.resolve()
        package_root = args.capsule_root.resolve()
        command = [
            sys.executable,
            "reagent_local.py",
            "run",
            ".",
            "--workflow",
            args.workflow,
            "--api-url",
            args.base_url,
        ]
    else:
        assert args.package_root is not None
        cwd = args.package_root.resolve()
        package_root = cwd
        command = [
            sys.executable,
            "reagent_local.py",
            "run",
            ".",
            "--mode",
            "demo",
            "--base-url",
            args.base_url,
        ]
        if args.resume:
            command.append("--resume")
    result = drive(
        command,
        cwd=cwd,
        package_root=package_root,
        timeout=args.timeout,
        interrupt_at=args.interrupt_at,
        resume=args.resume,
    )
    if result != args.expect_exit:
        print(
            f"interactive fixture exit mismatch: expected {args.expect_exit}, received {result}",
            file=sys.stderr,
        )
        return 1
    print(f"interactive fixture observed expected exit {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
