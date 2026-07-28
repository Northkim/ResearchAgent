from __future__ import annotations

import csv
import io
import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from backend.research.contracts import canonical_hash
from backend.research.evaluation.contracts import (
    AdjudicatedJudgment,
    EvaluationCandidate,
    EvaluationTopic,
    RelevanceLabel,
)
from backend.research.evaluation.cli import _load_adjudications
from backend.research.evaluation.judgments import (
    adjudicate,
    export_review_csv,
    export_review_json,
    import_review_csv,
    import_review_json,
)
from backend.research.evaluation.topics import load_topic_set

NOW = datetime(2026, 7, 28, 9, 0, tzinfo=UTC)


def _candidate(index: int = 1) -> EvaluationCandidate:
    return EvaluationCandidate(
        topic_id="topic-1",
        topic_title="Synthetic review topic",
        topic="synthetic review query",
        research_question="Which synthetic result is relevant?",
        candidate_id=f"candidate-{index}",
        rank=index,
        paper_id=f"paper-{index}",
        openalex_id=f"W{index}",
        title=f"Synthetic candidate {index}",
        authors=("Reviewer Safe",),
        year=2025,
        venue="Synthetic Venue",
        doi=f"10.1234/synthetic-{index}",
        abstract_available=True,
        normalized_metadata_hash=canonical_hash({"candidate": index}),
        search_execution_id=canonical_hash({"execution": 1}),
        provider="openalex",
        adapter_version="1.0.0",
        abstract_preview="Synthetic preview only.",
    )


def _completed_json(candidates, reviewer_id: str = "reviewer-a") -> bytes:
    value = json.loads(export_review_json(candidates))
    for row in value["rows"]:
        row.update(
            {
                "reviewer_id": reviewer_id,
                "relevance_label": "RELEVANT",
                "confidence": 4,
                "identity_ambiguity": False,
                "judged_at": NOW.isoformat(),
            }
        )
    return json.dumps(value, ensure_ascii=False).encode()


def test_contracts_are_immutable_and_hash_deterministic() -> None:
    topic = EvaluationTopic(
        topic_id="immutable-topic",
        title="Immutable topic",
        topic="paper discovery",
        research_question=None,
        keywords=("discovery",),
        year_from=2020,
        year_to=2026,
        language_policy="No hard filter.",
        document_type_policy="Research outputs.",
        intended_discipline="information science",
        difficulty_tags=("broad_query",),
        rationale="Contract test.",
        expected_ambiguity_cases=("generic terminology",),
    )
    assert topic.canonical_hash() == EvaluationTopic.from_dict(topic.to_dict()).canonical_hash()
    with pytest.raises(FrozenInstanceError):
        topic.title = "changed"  # type: ignore[misc]


def test_versioned_topic_set_loads_twelve_unique_topics() -> None:
    topic_set = load_topic_set("evaluation/topics/openalex_v1.json")
    assert topic_set.version == "1.0.0"
    assert len(topic_set.topics) == 12
    assert len({item.topic_id for item in topic_set.topics}) == 12
    assert topic_set.canonical_hash.startswith("sha256:")


def test_json_export_import_round_trip_records_checksum_without_filling_labels() -> None:
    candidates = (_candidate(1), _candidate(2))
    template = json.loads(export_review_json(candidates))
    assert all(row["relevance_label"] == "" for row in template["rows"])
    result = import_review_json(_completed_json(candidates), candidates)
    assert result.reviewer_id == "reviewer-a"
    assert result.complete is True
    assert len(result.judgments) == 2
    assert result.file_checksum.startswith("sha256:")


def test_csv_export_import_round_trip() -> None:
    candidates = (_candidate(1), _candidate(2))
    rows = list(csv.DictReader(io.StringIO(export_review_csv(candidates).decode())))
    for row in rows:
        row.update(
            {
                "reviewer_id": "reviewer-csv",
                "relevance_label": "PARTIALLY_RELEVANT",
                "confidence": "3",
                "identity_ambiguity": "false",
                "metadata_error_flags": "[]",
                "judged_at": NOW.isoformat(),
            }
        )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=rows[0].keys(), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    result = import_review_csv(output.getvalue().encode(), candidates)
    assert len(result.judgments) == 2
    assert result.judgments[0].relevance_label is RelevanceLabel.PARTIALLY_RELEVANT


def test_import_rejects_unknown_altered_duplicate_invalid_and_missing_values() -> None:
    candidates = (_candidate(1), _candidate(2))
    base = json.loads(_completed_json(candidates))

    unknown = json.loads(json.dumps(base))
    unknown["rows"][0]["candidate_id"] = "unknown"
    with pytest.raises(ValueError, match="Unknown candidate"):
        import_review_json(json.dumps(unknown).encode(), candidates)

    altered = json.loads(json.dumps(base))
    altered["rows"][0]["candidate_identity_hash"] = canonical_hash("changed")
    with pytest.raises(ValueError, match="identity changed"):
        import_review_json(json.dumps(altered).encode(), candidates)

    altered_metadata = json.loads(json.dumps(base))
    altered_metadata["rows"][0]["title"] = "Changed title"
    with pytest.raises(ValueError, match="review metadata changed"):
        import_review_json(json.dumps(altered_metadata).encode(), candidates)

    duplicate = json.loads(json.dumps(base))
    duplicate["rows"].append(dict(duplicate["rows"][0]))
    with pytest.raises(ValueError, match="Duplicate reviewer"):
        import_review_json(json.dumps(duplicate).encode(), candidates)

    invalid = json.loads(json.dumps(base))
    invalid["rows"][0]["relevance_label"] = "AUTO_RELEVANT"
    with pytest.raises(ValueError, match="Invalid relevance"):
        import_review_json(json.dumps(invalid).encode(), candidates)

    missing_reviewer = json.loads(json.dumps(base))
    missing_reviewer["rows"][0]["reviewer_id"] = ""
    with pytest.raises(ValueError, match="Reviewer ID"):
        import_review_json(json.dumps(missing_reviewer).encode(), candidates)

    partial = json.loads(json.dumps(base))
    partial["rows"] = partial["rows"][:1]
    with pytest.raises(ValueError, match="incomplete"):
        import_review_json(
            json.dumps(partial).encode(),
            candidates,
            require_complete=True,
        )


def test_adjudication_requires_consistent_candidate_and_two_humans() -> None:
    candidate = _candidate()
    first = import_review_json(
        _completed_json((candidate,), "reviewer-a"),
        (candidate,),
    ).judgments[0]
    second_value = json.loads(_completed_json((candidate,), "reviewer-b"))
    second_value["rows"][0]["relevance_label"] = "NOT_RELEVANT"
    second = import_review_json(
        json.dumps(second_value).encode(),
        (candidate,),
    ).judgments[0]
    result = adjudicate(
        candidate=candidate,
        source_judgments=(first, second),
        final_relevance_label=RelevanceLabel.RELEVANT,
        adjudicator_id="adjudicator-1",
        disagreement_reason="Different interpretation of the topic boundary.",
        final_notes="Human decision.",
        adjudicated_at=NOW,
    )
    assert result.candidate_id == candidate.candidate_id
    with pytest.raises(ValueError, match="distinct reviewer"):
        adjudicate(
            candidate=candidate,
            source_judgments=(first, first),
            final_relevance_label=RelevanceLabel.RELEVANT,
            adjudicator_id="adjudicator-1",
            disagreement_reason=None,
            final_notes=None,
            adjudicated_at=NOW,
        )


def test_adjudication_file_rejects_source_hashes_for_another_candidate(
    tmp_path,
) -> None:
    first_candidate = _candidate(1)
    second_candidate = _candidate(2)
    reviewers = tuple(
        import_review_json(
            _completed_json((first_candidate,), reviewer_id),
            (first_candidate,),
        ).judgments[0]
        for reviewer_id in ("reviewer-a", "reviewer-b")
    )
    invalid = AdjudicatedJudgment(
        topic_id=second_candidate.topic_id,
        candidate_id=second_candidate.candidate_id,
        final_relevance_label=RelevanceLabel.RELEVANT,
        adjudicator_id="adjudicator-1",
        source_judgment_hashes=tuple(
            judgment.canonical_hash() for judgment in reviewers
        ),
        disagreement_reason=None,
        final_notes=None,
        adjudicated_at=NOW,
    )
    path = tmp_path / "adjudicated.json"
    path.write_text(
        json.dumps({"judgments": [invalid.to_dict()]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="another candidate"):
        _load_adjudications(
            path,
            (first_candidate, second_candidate),
            reviewers,
        )
