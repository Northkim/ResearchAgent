"""Single fail-fast command interface for OpenAlex evaluation."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from backend.research.adapters import (
    LocalFilesystemArtifactStorage,
    OpenAlexConfiguration,
    OpenAlexPaperSearchProvider,
)
from backend.research.contracts._serialization import canonical_json
from backend.research.services import ProviderExecutionPolicy, ProviderOperationService

from .candidate_pool import CandidatePoolGenerator
from .contracts import (
    AdjudicatedJudgment,
    CandidateJudgment,
    EvaluationCandidate,
    EvaluationCompletionState,
    EvaluationRun,
    RelevanceLabel,
)
from .judgments import (
    export_review_csv,
    export_review_json,
    import_review_csv,
    import_review_json,
)
from .metrics import EvaluationMetrics
from .multilingual import (
    MultilingualCandidatePoolGenerator,
    load_multilingual_plan,
)
from .operation_journal import JournaledProviderOperationUnit
from .report import EvaluationReportGenerator
from .topics import load_topic_set

DEFAULT_TOPIC_SET = Path("evaluation/topics/openalex_v1.json")
DEFAULT_MULTILINGUAL_PLAN = Path(
    "evaluation/topics/openalex_chinese_multilingual_v1.json"
)
DEFAULT_EVALUATION_ROOT = Path("runtime_data/evaluations/openalex")
DEFAULT_SYNTHETIC_FIXTURES = Path("evaluation/fixtures/synthetic_silver_v1.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m backend.research.evaluation",
        description="Human-reviewed OpenAlex discovery evaluation harness",
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_EVALUATION_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    initialize = subparsers.add_parser("initialize")
    initialize.add_argument("evaluation_id")
    initialize.add_argument("--topic-set", type=Path, default=DEFAULT_TOPIC_SET)

    generate = subparsers.add_parser("generate")
    generate.add_argument("evaluation_id")
    generate.add_argument("--topic-set", type=Path, default=DEFAULT_TOPIC_SET)
    generate.add_argument("--topic", action="append", dest="topics")
    generate.add_argument("--live", action="store_true")
    generate.add_argument("--include-abstract-preview", action="store_true")

    multilingual = subparsers.add_parser("generate-multilingual")
    multilingual.add_argument("evaluation_id")
    multilingual.add_argument("--topic-set", type=Path, default=DEFAULT_TOPIC_SET)
    multilingual.add_argument(
        "--plan",
        type=Path,
        default=DEFAULT_MULTILINGUAL_PLAN,
    )
    multilingual.add_argument("--live", action="store_true")
    multilingual.add_argument("--include-abstract-preview", action="store_true")

    synthetic = subparsers.add_parser(
        "judge-synthetic",
        help="Run the deterministic Fake Judge on wholly synthetic fixtures only.",
    )
    synthetic.add_argument("evaluation_id")
    synthetic.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_SYNTHETIC_FIXTURES,
    )

    export = subparsers.add_parser("export")
    export.add_argument("evaluation_id")
    export.add_argument("--format", choices=("json", "csv"), required=True)
    export.add_argument("--reviewer-id")

    packets = subparsers.add_parser("packets")
    packets.add_argument("evaluation_id")
    packets.add_argument(
        "--reviewer",
        action="append",
        dest="reviewers",
        required=True,
        help="Exactly two distinct pseudonymous reviewer IDs.",
    )

    import_command = subparsers.add_parser("import")
    import_command.add_argument("evaluation_id")
    import_command.add_argument("review_file", type=Path)
    import_command.add_argument("--format", choices=("json", "csv"), required=True)
    import_command.add_argument("--require-complete", action="store_true")

    adjudicate = subparsers.add_parser("adjudicate")
    adjudicate.add_argument("evaluation_id")
    adjudicate.add_argument("adjudication_file", type=Path)
    adjudicate.add_argument("review_files", nargs="+", type=Path)

    report = subparsers.add_parser("report")
    report.add_argument("evaluation_id")
    report.add_argument("adjudication_file", type=Path)
    report.add_argument("review_files", nargs="+", type=Path)
    report.add_argument("--pooled-relevant-total", type=int)

    status = subparsers.add_parser("status")
    status.add_argument("evaluation_id")

    clean = subparsers.add_parser("clean")
    clean.add_argument("evaluation_id")
    clean.add_argument(
        "--confirm",
        help="Must exactly equal evaluation_id; cleanup is never implicit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = _safe_root(args.root)
        storage = LocalFilesystemArtifactStorage(root)
        if args.command == "judge-synthetic":
            from collections import Counter

            from .fake_judge import FakeAutomatedRelevanceJudge
            from .silver_orchestrator import SyntheticSilverOrchestrator
            from .synthetic_fixtures import load_synthetic_fixture_set

            evaluation_id = _safe_segment(args.evaluation_id)
            fixtures = load_synthetic_fixture_set(args.fixtures)
            judge = FakeAutomatedRelevanceJudge(
                pointwise=fixtures.pointwise_behaviors,
                pairwise=fixtures.pairwise_behaviors,
            )
            operation_unit = JournaledProviderOperationUnit(
                root / evaluation_id / "provider_operations.journal.jsonl"
            )
            service = ProviderOperationService(
                operation_unit.provider_operations,
                commit_callback=operation_unit.commit,
            )
            orchestrator = SyntheticSilverOrchestrator(
                judge=judge,
                provider_operations=service,
                execution_policy=ProviderExecutionPolicy.synthetic_relevance_judge(),
                artifact_storage=storage,
            )
            result = orchestrator.run(
                evaluation_id=evaluation_id,
                fixtures=fixtures,
            )
            before_replay = len(judge.call_log)
            replay = orchestrator.run(
                evaluation_id=evaluation_id,
                fixtures=fixtures,
            )
            dispositions = Counter(
                item.disposition.value for item in result.consensuses
            )
            _print_result(
                {
                    "status": "resumed" if result.resumed else "generated",
                    "evaluation_id": evaluation_id,
                    "synthetic_fixture_count": len(result.candidates),
                    "successful_judgment_count": len(result.judgments),
                    "provider_operation_count": result.provider_operation_count,
                    "consensus_dispositions": dict(sorted(dispositions.items())),
                    "audit_queue_count": len(result.audit_queue.requests),
                    "raw_silver_synthetic_metrics": result.metrics.raw_silver.to_dict(),
                    "audited_silver_available": (
                        result.metrics.audited_silver.precision_at_5.available
                    ),
                    "replay_verified": replay.resumed,
                    "replay_judge_calls": len(judge.call_log) - before_replay,
                    "real_candidate_labels_generated": False,
                    "expert_gold_labels_present": False,
                    "network_called": False,
                }
            )
            return 0
        if args.command == "initialize":
            topic_set = load_topic_set(args.topic_set)
            key = f"{_safe_segment(args.evaluation_id)}/evaluation_config.json"
            value = {
                "schema_version": "openalex-evaluation-config/v1",
                "evaluation_id": args.evaluation_id,
                "topic_set_version": topic_set.version,
                "topic_set_hash": topic_set.canonical_hash,
                "live_generation_requires_explicit_opt_in": True,
                "human_labels_generated": False,
            }
            stored = storage.write_immutable(
                key,
                canonical_json(value).encode("utf-8"),
                media_type="application/json",
            )
            _print_result({"status": "initialized", "storage_key": stored.storage_key})
            return 0
        if args.command == "generate":
            if not args.live:
                raise ValueError(
                    "Candidate generation requires explicit --live; default execution "
                    "must remain network-free"
                )
            api_key = os.environ.get("REAGENT_OPENALEX_API_KEY")
            if not api_key:
                raise ValueError("OpenAlex API key is not configured")
            if not args.topics or len(args.topics) > 3:
                raise ValueError(
                    "Live evaluation requires one to three explicit --topic values"
                )
            topic_set = load_topic_set(args.topic_set)
            evaluation_id = _safe_segment(args.evaluation_id)
            config = _load_json(
                storage,
                f"{evaluation_id}/evaluation_config.json",
            )
            if (
                config.get("evaluation_id") != evaluation_id
                or config.get("topic_set_version") != topic_set.version
                or config.get("topic_set_hash") != topic_set.canonical_hash
            ):
                raise ValueError(
                    "Evaluation configuration does not match the requested topic set"
                )
            operation_unit = JournaledProviderOperationUnit(
                root / evaluation_id / "provider_operations.journal.jsonl"
            )
            service = ProviderOperationService(
                operation_unit.provider_operations,
                commit_callback=operation_unit.commit,
            )
            generator = CandidatePoolGenerator(
                provider=OpenAlexPaperSearchProvider(
                    OpenAlexConfiguration(api_key=api_key)
                ),
                provider_operations=service,
                execution_policy=ProviderExecutionPolicy.supervised_openalex(),
                artifact_storage=storage,
                include_abstract_preview=args.include_abstract_preview,
            )
            result = asyncio.run(
                generator.generate(
                    evaluation_id=evaluation_id,
                    topic_set=topic_set,
                    topic_ids=tuple(args.topics),
                )
            )
            _print_result(
                {
                    "status": "resumed" if result.resumed else "generated",
                    "evaluation_id": result.evaluation_run.evaluation_id,
                    "candidate_count": len(result.candidates),
                    "request_count": result.evaluation_run.request_count,
                    "api_key": "configured and redacted",
                }
            )
            return 0
        if args.command == "generate-multilingual":
            if not args.live:
                raise ValueError(
                    "Multilingual candidate generation requires explicit --live; "
                    "default execution remains network-free"
                )
            api_key = os.environ.get("REAGENT_OPENALEX_API_KEY")
            if not api_key:
                raise ValueError("OpenAlex API key is not configured")
            topic_set = load_topic_set(args.topic_set)
            plan = load_multilingual_plan(args.plan)
            matches = tuple(
                item
                for item in topic_set.topics
                if item.topic == plan.original_query.topic
            )
            if len(matches) != 1:
                raise ValueError(
                    "Multilingual plan must match exactly one evaluation topic"
                )
            topic = matches[0]
            evaluation_id = _safe_segment(args.evaluation_id)
            config = _load_json(
                storage,
                f"{evaluation_id}/evaluation_config.json",
            )
            if (
                config.get("evaluation_id") != evaluation_id
                or config.get("topic_set_version") != topic_set.version
                or config.get("topic_set_hash") != topic_set.canonical_hash
            ):
                raise ValueError(
                    "Evaluation configuration does not match the requested topic set"
                )
            operation_unit = JournaledProviderOperationUnit(
                root / evaluation_id / "provider_operations.journal.jsonl"
            )
            service = ProviderOperationService(
                operation_unit.provider_operations,
                commit_callback=operation_unit.commit,
            )
            generator = MultilingualCandidatePoolGenerator(
                provider=OpenAlexPaperSearchProvider(
                    OpenAlexConfiguration(
                        api_key=api_key,
                        retries_after_initial=0,
                        max_discovery_requests=1,
                    )
                ),
                provider_operations=service,
                execution_policy=(
                    ProviderExecutionPolicy.supervised_multilingual_openalex()
                ),
                artifact_storage=storage,
                include_abstract_preview=args.include_abstract_preview,
            )
            result = asyncio.run(
                generator.generate(
                    evaluation_id=evaluation_id,
                    topic=topic,
                    plan=plan,
                    topic_set_version=topic_set.version,
                )
            )
            _print_result(
                {
                    "status": "resumed" if result.resumed else "generated",
                    "evaluation_id": result.evaluation_run.evaluation_id,
                    "candidate_count": len(result.candidates),
                    "request_count": result.evaluation_run.request_count,
                    "diagnostic_count": len(result.diagnostics),
                    "api_key": "configured and redacted",
                    "relevance_labels_generated": False,
                }
            )
            return 0
        if args.command == "export":
            candidates = _load_candidates(storage, args.evaluation_id)
            content = (
                export_review_json(
                    candidates,
                    reviewer_id=args.reviewer_id or "",
                )
                if args.format == "json"
                else export_review_csv(
                    candidates,
                    reviewer_id=args.reviewer_id or "",
                )
            )
            extension = args.format
            reviewer_segment = (
                _safe_segment(args.reviewer_id)
                if args.reviewer_id
                else "template"
            )
            stored = storage.write_immutable(
                (
                    f"{_safe_segment(args.evaluation_id)}/reviews/"
                    f"{reviewer_segment}.{extension}"
                ),
                content,
                media_type=(
                    "application/json"
                    if extension == "json"
                    else "text/csv; charset=utf-8"
                ),
            )
            _print_result({"status": "exported", "storage_key": stored.storage_key})
            return 0
        if args.command == "packets":
            evaluation_id = _safe_segment(args.evaluation_id)
            reviewers = tuple(_safe_segment(item) for item in args.reviewers)
            if len(reviewers) != 2 or len(set(reviewers)) != 2:
                raise ValueError(
                    "Review packet generation requires exactly two distinct reviewers"
                )
            candidates = _load_candidates(storage, evaluation_id)
            run = _load_run(storage, evaluation_id)
            candidate_identity = [
                {
                    "candidate_id": item.candidate_id,
                    "identity_hash": item.identity_hash,
                }
                for item in candidates
            ]
            from backend.research.contracts import canonical_hash

            candidate_set_checksum = canonical_hash(candidate_identity)
            created_at = run.completed_at.astimezone(UTC)
            candidate_expiry = created_at + timedelta(days=30)
            preview_expiry = created_at + timedelta(days=14)
            packet_artifacts: list[dict[str, Any]] = []
            for reviewer in reviewers:
                for extension, content, media_type in (
                    (
                        "json",
                        export_review_json(candidates, reviewer_id=reviewer),
                        "application/json",
                    ),
                    (
                        "csv",
                        export_review_csv(candidates, reviewer_id=reviewer),
                        "text/csv; charset=utf-8",
                    ),
                ):
                    stored = storage.write_immutable(
                        (
                            f"{evaluation_id}/reviews/{reviewer}/"
                            f"review.{extension}"
                        ),
                        content,
                        media_type=media_type,
                    )
                    packet_artifacts.append(
                        {
                            "reviewer_id": reviewer,
                            "format": extension,
                            "storage_key": stored.storage_key,
                            "checksum": stored.checksum,
                            "size": stored.size,
                            "media_type": stored.media_type,
                        }
                    )
            adjudication_document = {
                "schema_version": "openalex-adjudication-template/v1",
                "evaluation_id": evaluation_id,
                "candidate_set_checksum": candidate_set_checksum,
                "instructions": (
                    "Human adjudicator completes this only after two independent "
                    "review files have been imported."
                ),
                "judgments": [
                    {
                        "topic_id": item.topic_id,
                        "candidate_id": item.candidate_id,
                        "candidate_identity_hash": item.identity_hash,
                        "final_relevance_label": "",
                        "adjudicator_id": "",
                        "source_judgment_hashes": [],
                        "disagreement_reason": "",
                        "final_notes": "",
                        "adjudicated_at": "",
                    }
                    for item in candidates
                ],
            }
            adjudication = storage.write_immutable(
                f"{evaluation_id}/reviews/adjudication_template.json",
                canonical_json(adjudication_document).encode("utf-8"),
                media_type="application/json",
            )
            packet_artifacts.append(
                {
                    "reviewer_id": None,
                    "format": "json",
                    "storage_key": adjudication.storage_key,
                    "checksum": adjudication.checksum,
                    "size": adjudication.size,
                    "media_type": adjudication.media_type,
                    "purpose": "blank_adjudication_template",
                }
            )
            packet_manifest = {
                "schema_version": "openalex-review-packet-manifest/v1",
                "evaluation_id": evaluation_id,
                "candidate_count": len(candidates),
                "candidate_set_checksum": candidate_set_checksum,
                "reviewer_ids": list(reviewers),
                "created_at": created_at.isoformat(),
                "normalized_metadata_expires_at": candidate_expiry.isoformat(),
                "abstract_previews_expire_at": preview_expiry.isoformat(),
                "judgment_fields_prefilled": False,
                "relevance_labels_prefilled": False,
                "human_review_required": True,
                "artifacts": packet_artifacts,
            }
            manifest = storage.write_immutable(
                f"{evaluation_id}/reviews/review_packet_manifest.json",
                canonical_json(packet_manifest).encode("utf-8"),
                media_type="application/json",
            )
            _print_result(
                {
                    "status": "review_packets_generated",
                    "evaluation_id": evaluation_id,
                    "candidate_count": len(candidates),
                    "candidate_set_checksum": candidate_set_checksum,
                    "manifest_storage_key": manifest.storage_key,
                    "manifest_checksum": manifest.checksum,
                    "human_labels_generated": False,
                }
            )
            return 0
        if args.command == "import":
            candidates = _load_candidates(storage, args.evaluation_id)
            content = args.review_file.read_bytes()
            result = (
                import_review_json(
                    content,
                    candidates,
                    require_complete=args.require_complete,
                )
                if args.format == "json"
                else import_review_csv(
                    content,
                    candidates,
                    require_complete=args.require_complete,
                )
            )
            document = {
                "schema_version": "openalex-imported-judgments/v1",
                "reviewer_id": result.reviewer_id,
                "source_file_checksum": result.file_checksum,
                "complete": result.complete,
                "missing_candidate_ids": list(result.missing_candidate_ids),
                "judgments": [item.to_dict() for item in result.judgments],
            }
            stored = storage.write_immutable(
                (
                    f"{_safe_segment(args.evaluation_id)}/judgments/"
                    f"{_safe_segment(result.reviewer_id)}.json"
                ),
                canonical_json(document).encode("utf-8"),
                media_type="application/json",
            )
            _print_result(
                {
                    "status": "imported",
                    "reviewer_id": result.reviewer_id,
                    "judgment_count": len(result.judgments),
                    "complete": result.complete,
                    "storage_key": stored.storage_key,
                }
            )
            return 0
        if args.command == "adjudicate":
            candidates = _load_candidates(storage, args.evaluation_id)
            reviewers = _load_reviewer_files(args.review_files)
            adjudicated = _load_adjudications(
                args.adjudication_file,
                candidates,
                reviewers,
            )
            stored = storage.write_immutable(
                f"{_safe_segment(args.evaluation_id)}/judgments/adjudicated.json",
                canonical_json(
                    {
                        "schema_version": "openalex-adjudication-set/v1",
                        "judgments": [item.to_dict() for item in adjudicated],
                    }
                ).encode("utf-8"),
                media_type="application/json",
            )
            _print_result(
                {
                    "status": "adjudicated_imported",
                    "count": len(adjudicated),
                    "storage_key": stored.storage_key,
                }
            )
            return 0
        if args.command == "report":
            candidates = _load_candidates(storage, args.evaluation_id)
            reviewers = _load_reviewer_files(args.review_files)
            adjudicated = _load_adjudications(
                args.adjudication_file,
                candidates,
                reviewers,
            )
            if {item.candidate_id for item in adjudicated} != {
                item.candidate_id for item in candidates
            }:
                raise ValueError(
                    "Evaluation report requires one adjudication for every candidate"
                )
            run = _load_run(storage, args.evaluation_id)
            metrics = EvaluationMetrics().calculate(
                candidates=candidates,
                adjudicated=adjudicated,
                reviewer_judgments=reviewers,
                evaluation_run=run,
                pooled_relevant_total=args.pooled_relevant_total,
            )
            artifacts = EvaluationReportGenerator(storage).generate(
                evaluation_run=run,
                candidates=candidates,
                reviewer_judgments=reviewers,
                adjudicated=adjudicated,
                metrics=metrics,
            )
            _print_result(
                {
                    "status": "report_generated",
                    "artifacts": [item.to_dict() for item in artifacts],
                }
            )
            return 0
        if args.command == "status":
            _print_result(
                _status_document(
                    root,
                    storage,
                    _safe_segment(args.evaluation_id),
                )
            )
            return 0
        if args.command == "clean":
            evaluation_id = _safe_segment(args.evaluation_id)
            if args.confirm != evaluation_id:
                raise ValueError("--confirm must exactly match evaluation_id")
            target = (root / evaluation_id).resolve()
            if target.parent != root:
                raise ValueError("Cleanup target escapes the evaluation root")
            if not target.exists():
                raise ValueError("Evaluation run does not exist")
            shutil.rmtree(target)
            _print_result({"status": "cleaned", "evaluation_id": evaluation_id})
            return 0
    except Exception as error:
        print(f"Evaluation command failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 2


def _load_candidates(
    storage: LocalFilesystemArtifactStorage,
    evaluation_id: str,
) -> tuple[EvaluationCandidate, ...]:
    manifest = _load_json(
        storage,
        f"{_safe_segment(evaluation_id)}/evaluation_manifest.json",
    )
    candidates: list[EvaluationCandidate] = []
    for artifact in manifest["artifacts"]:
        if artifact["logical_name"] != "topic_manifest.json":
            continue
        receipt = _load_json(storage, str(artifact["storage_key"]))
        candidates.extend(
            EvaluationCandidate.from_dict(item) for item in receipt["candidates"]
        )
    return tuple(sorted(candidates, key=lambda item: (item.topic_id, item.rank)))


def _load_run(
    storage: LocalFilesystemArtifactStorage,
    evaluation_id: str,
) -> EvaluationRun:
    manifest = _load_json(
        storage,
        f"{_safe_segment(evaluation_id)}/evaluation_manifest.json",
    )
    value = manifest["evaluation_run"]
    return EvaluationRun(
        evaluation_id=str(value["evaluation_id"]),
        topic_set_version=str(value["topic_set_version"]),
        provider=str(value["provider"]),
        adapter_version=str(value["adapter_version"]),
        api_contract_snapshot=str(value["api_contract_snapshot"]),
        query_fingerprints=dict(value["query_fingerprints"]),
        candidate_pool_checksums=dict(value["candidate_pool_checksums"]),
        started_at=datetime.fromisoformat(str(value["started_at"])),
        completed_at=datetime.fromisoformat(str(value["completed_at"])),
        request_count=int(value["request_count"]),
        latency_ms=int(value["latency_ms"]),
        retry_count=int(value["retry_count"]),
        provider_usage=tuple(value["provider_usage"]),
        completion_state=EvaluationCompletionState(str(value["completion_state"])),
        schema_version=str(value["schema_version"]),
    )


def _load_reviewer_files(paths: list[Path]) -> tuple[CandidateJudgment, ...]:
    result: list[CandidateJudgment] = []
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        rows = value.get("judgments") if isinstance(value, Mapping) else None
        if not isinstance(rows, list):
            raise ValueError(f"Reviewer file has no judgments array: {path}")
        result.extend(CandidateJudgment.from_dict(item) for item in rows)
    keys = [(item.candidate_id, item.reviewer_id) for item in result]
    if len(keys) != len(set(keys)):
        raise ValueError("Reviewer files contain duplicate judgments")
    return tuple(result)


def _load_adjudications(
    path: Path,
    candidates: tuple[EvaluationCandidate, ...],
    reviewers: tuple[CandidateJudgment, ...],
) -> tuple[AdjudicatedJudgment, ...]:
    value = json.loads(path.read_text(encoding="utf-8"))
    rows = value.get("judgments") if isinstance(value, Mapping) else None
    if not isinstance(rows, list):
        raise ValueError("Adjudication file has no judgments array")
    candidates_by_id = {item.candidate_id: item for item in candidates}
    reviewers_by_hash = {item.canonical_hash(): item for item in reviewers}
    result: list[AdjudicatedJudgment] = []
    for row in rows:
        item = AdjudicatedJudgment(
            topic_id=str(row["topic_id"]),
            candidate_id=str(row["candidate_id"]),
            final_relevance_label=RelevanceLabel(str(row["final_relevance_label"])),
            adjudicator_id=str(row["adjudicator_id"]),
            source_judgment_hashes=tuple(row["source_judgment_hashes"]),
            disagreement_reason=(
                None
                if row.get("disagreement_reason") in {None, ""}
                else str(row["disagreement_reason"])
            ),
            final_notes=(
                None if row.get("final_notes") in {None, ""} else str(row["final_notes"])
            ),
            adjudicated_at=datetime.fromisoformat(str(row["adjudicated_at"])),
        )
        candidate = candidates_by_id.get(item.candidate_id)
        if candidate is None:
            raise ValueError("Adjudication references an unknown candidate")
        if item.topic_id != candidate.topic_id:
            raise ValueError("Adjudication topic does not match its candidate")
        if not set(item.source_judgment_hashes).issubset(reviewers_by_hash):
            raise ValueError("Adjudication references unknown reviewer judgments")
        sources = tuple(
            reviewers_by_hash[source_hash]
            for source_hash in item.source_judgment_hashes
        )
        if any(source.candidate_id != item.candidate_id for source in sources):
            raise ValueError(
                "Adjudication source judgment belongs to another candidate"
            )
        if any(
            source.candidate_identity_hash != candidate.identity_hash
            for source in sources
        ):
            raise ValueError("Adjudication source candidate identity has changed")
        reviewer_ids = {source.reviewer_id for source in sources}
        if len(reviewer_ids) < 2:
            raise ValueError("Adjudication requires two distinct reviewers")
        if item.adjudicator_id in reviewer_ids:
            raise ValueError("Adjudicator must be independent from source reviewers")
        source_labels = {source.relevance_label for source in sources}
        if len(source_labels) > 1 and not item.disagreement_reason:
            raise ValueError("Disagreement adjudication requires a reason")
        result.append(item)
    if len({item.candidate_id for item in result}) != len(result):
        raise ValueError("Adjudication file contains duplicate candidates")
    return tuple(result)


def _load_json(
    storage: LocalFilesystemArtifactStorage,
    storage_key: str,
) -> Mapping[str, Any]:
    value = json.loads(storage.read(storage_key))
    if not isinstance(value, Mapping):
        raise ValueError(f"Stored JSON is not an object: {storage_key}")
    return value


def _status_document(
    root: Path,
    storage: LocalFilesystemArtifactStorage,
    evaluation_id: str,
) -> Mapping[str, Any]:
    try:
        manifest = _load_json(
            storage,
            f"{evaluation_id}/evaluation_manifest.json",
        )
    except FileNotFoundError:
        config = _load_json(
            storage,
            f"{evaluation_id}/evaluation_config.json",
        )
        return {
            "evaluation_id": config["evaluation_id"],
            "completion_state": EvaluationCompletionState.INITIALIZED.value,
            "candidate_count": 0,
            "imported_reviewer_files": 0,
            "adjudication_present": False,
            "adjudicated_count": 0,
            "report_present": False,
            "human_labels_generated_by_system": False,
        }
    run = manifest["evaluation_run"]
    judgment_root = root / evaluation_id / "judgments"
    reviewer_files = (
        tuple(
            path
            for path in judgment_root.glob("*.json")
            if path.name != "adjudicated.json"
        )
        if judgment_root.is_dir()
        else ()
    )
    adjudication_path = judgment_root / "adjudicated.json"
    adjudication_present = adjudication_path.is_file()
    adjudicated_count = 0
    if adjudication_present:
        adjudication_document = json.loads(
            adjudication_path.read_text(encoding="utf-8")
        )
        judgments = (
            adjudication_document.get("judgments")
            if isinstance(adjudication_document, Mapping)
            else None
        )
        adjudicated_count = len(judgments) if isinstance(judgments, list) else 0
    report_present = (root / evaluation_id / "evaluation_report.md").is_file()
    state = str(run["completion_state"])
    if report_present:
        state = EvaluationCompletionState.COMPLETE.value
    elif adjudication_present and adjudicated_count == manifest["candidate_count"]:
        state = EvaluationCompletionState.ADJUDICATED.value
    elif len(reviewer_files) >= 2:
        state = EvaluationCompletionState.READY_FOR_ADJUDICATION.value
    elif reviewer_files:
        state = EvaluationCompletionState.JUDGMENTS_PARTIAL.value
    return {
        "evaluation_id": run["evaluation_id"],
        "completion_state": state,
        "candidate_count": manifest["candidate_count"],
        "imported_reviewer_files": len(reviewer_files),
        "adjudication_present": adjudication_present,
        "adjudicated_count": adjudicated_count,
        "report_present": report_present,
        "human_labels_generated_by_system": False,
    }


def _safe_root(value: Path) -> Path:
    root = value.expanduser().resolve()
    if root in {Path("/"), Path.home().resolve(), Path.cwd().resolve()}:
        raise ValueError("Evaluation root is too broad")
    return root


def _safe_segment(value: str) -> str:
    if (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\/" in value
        or "\\" in value
        or not all(character.isalnum() or character in "-_." for character in value)
    ):
        raise ValueError("Evaluation identifiers must be safe path segments")
    return value


def _print_result(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
