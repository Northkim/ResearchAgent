"""Immutable provider-independent prompt and rubric registry."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Mapping
from typing import Any

from backend.research.contracts import canonical_hash
from backend.research.contracts._serialization import SerializableContract


RUBRIC_VERSION = "reagent-topic-relevance/v1"
REGISTRY_SCHEMA_VERSION = "reagent-judge-prompt-registry/v1"
POINTWISE_A_VERSION = "relevance-pointwise-a/v1"
POINTWISE_B_VERSION = "relevance-pointwise-b/v1"
PAIRWISE_VERSION = "relevance-pairwise-mirrored/v1"

PROHIBITED_INPUT_FIELDS = (
    "openalex_rank",
    "rank",
    "deterministic_rank_score",
    "citation_count",
    "provider_relevance_score",
    "another_judgment",
    "existing_human_label",
)

_OUTPUT_SCHEMA = MappingProxyType(
    {
        "label": "HIGHLY_RELEVANT|RELEVANT|PARTIALLY_RELEVANT|NOT_RELEVANT|CANNOT_JUDGE",
        "confidence": "number in [0,1]",
        "supporting_spans": "short excerpts from supplied preview only",
        "concise_reason": "string",
        "uncertainties": "string[]",
        "insufficient_information": "boolean",
    }
)


@dataclass(frozen=True, slots=True)
class JudgePrompt(SerializableContract):
    version: str
    language: str
    template: str
    rubric_version: str
    prohibited_input_fields: tuple[str, ...]
    output_schema: Mapping[str, str]
    schema_version: str = REGISTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "prohibited_input_fields", tuple(self.prohibited_input_fields))
        object.__setattr__(self, "output_schema", MappingProxyType(dict(self.output_schema)))

    @property
    def prompt_hash(self) -> str:
        return canonical_hash(self)


_POINTWISE_A = JudgePrompt(
    version=POINTWISE_A_VERSION,
    language="en",
    rubric_version=RUBRIC_VERSION,
    prohibited_input_fields=PROHIBITED_INPUT_FIELDS,
    output_schema=_OUTPUT_SCHEMA,
    template=(
        "Assess topical relevance using only the supplied title and bounded abstract "
        "preview. Choose one rubric label. Do not assess scientific correctness, "
        "method quality, novelty, venue, credibility, truth, or overall merit. "
        "Return CANNOT_JUDGE when evidence is insufficient. Any supporting span must "
        "be a short exact excerpt from the supplied abstract preview."
    ),
)
_POINTWISE_B = JudgePrompt(
    version=POINTWISE_B_VERSION,
    language="en",
    rubric_version=RUBRIC_VERSION,
    prohibited_input_fields=PROHIBITED_INPUT_FIELDS,
    output_schema=_OUTPUT_SCHEMA,
    template=(
        "Using only title and bounded preview, decide whether the stated topic is the "
        "paper's central contribution, a substantial necessary component, secondary "
        "context, absent/incidental, or not decidable. Judge topical relevance only; "
        "never infer research quality, factual truth, novelty, venue quality, or "
        "causal validity. Cite only short preview spans and use CANNOT_JUDGE if the "
        "provided evidence cannot support a label."
    ),
)
_PAIRWISE = JudgePrompt(
    version=PAIRWISE_VERSION,
    language="en",
    rubric_version=RUBRIC_VERSION,
    prohibited_input_fields=PROHIBITED_INPUT_FIELDS,
    output_schema=MappingProxyType(
        {
            "preferred_candidate_id": "left candidate ID|right candidate ID|TIE",
            "reason": "topical-relevance comparison only",
        }
    ),
    template=(
        "Compare which supplied candidate more directly addresses the stated topic. "
        "Use only titles and bounded previews. Return TIE if no supported preference "
        "exists. Ignore rank, citations, venue, scientific quality, truth, novelty, "
        "and all prior judgments. The mirrored order must be evaluated independently."
    ),
)


@dataclass(frozen=True, slots=True)
class JudgePromptRegistry:
    """Fixed registry; callers receive immutable prompt values."""

    prompts: tuple[JudgePrompt, ...] = (_POINTWISE_A, _POINTWISE_B, _PAIRWISE)
    rubric_version: str = RUBRIC_VERSION
    schema_version: str = REGISTRY_SCHEMA_VERSION

    def get(self, version: str) -> JudgePrompt:
        matches = tuple(item for item in self.prompts if item.version == version)
        if len(matches) != 1:
            raise KeyError(version)
        return matches[0]

    def validate_input_fields(self, values: Mapping[str, Any]) -> None:
        present = sorted(set(values).intersection(PROHIBITED_INPUT_FIELDS))
        if present:
            raise ValueError(f"Prohibited judge input fields: {present}")

    @property
    def pointwise_versions(self) -> tuple[str, str]:
        return (POINTWISE_A_VERSION, POINTWISE_B_VERSION)

    @property
    def pairwise_version(self) -> str:
        return PAIRWISE_VERSION
