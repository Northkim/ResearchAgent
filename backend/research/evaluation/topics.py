"""Versioned evaluation-topic loading."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.research.contracts import canonical_hash

from .contracts import EvaluationTopic, TOPIC_SET_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class EvaluationTopicSet:
    topic_set_id: str
    version: str
    description: str
    topics: tuple[EvaluationTopic, ...]
    schema_version: str = TOPIC_SET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.topic_set_id.strip() or not self.version.strip():
            raise ValueError("Topic-set identity and version must be non-empty")
        if not self.description.strip():
            raise ValueError("Topic-set description must be non-empty")
        if not self.topics:
            raise ValueError("Topic set must contain at least one topic")
        ids = [topic.topic_id for topic in self.topics]
        if len(ids) != len(set(ids)):
            raise ValueError("Topic IDs must be unique")

    @property
    def canonical_hash(self) -> str:
        return canonical_hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "topic_set_id": self.topic_set_id,
            "version": self.version,
            "description": self.description,
            "topics": [topic.to_dict() for topic in self.topics],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> EvaluationTopicSet:
        if value.get("schema_version") != TOPIC_SET_SCHEMA_VERSION:
            raise ValueError("Unsupported evaluation topic-set schema")
        raw_topics = value.get("topics")
        if not isinstance(raw_topics, list):
            raise ValueError("Evaluation topic set requires a topics array")
        if any(not isinstance(item, Mapping) for item in raw_topics):
            raise ValueError("Every evaluation topic must be an object")
        return cls(
            topic_set_id=str(value["topic_set_id"]),
            version=str(value["version"]),
            description=str(value["description"]),
            topics=tuple(EvaluationTopic.from_dict(item) for item in raw_topics),
            schema_version=str(value["schema_version"]),
        )


def load_topic_set(path: str | Path) -> EvaluationTopicSet:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("Evaluation topic-set file must contain an object")
    return EvaluationTopicSet.from_dict(value)
