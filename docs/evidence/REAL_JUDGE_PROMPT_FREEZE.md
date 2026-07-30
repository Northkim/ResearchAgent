# Real Judge Prompt Freeze

Freeze ID: `reagent-real-judge-prompt-freeze/v1-proposed`
Date: 2026-07-29
Status: Proposed; records current source prompts without modifying them

The hashes below were derived read-only from the current
`JudgePromptRegistry` canonical serialization. No prompt source changed.

## Frozen registry

| Purpose | Version | SHA-256 | Language | Rubric | Interpretation |
|---|---|---|---|---|---|
| pointwise A | `relevance-pointwise-a/v1` | `sha256:aa3adfa637b510ff90da5a3885cc5092ccd798d7e4efd87c15e3b2f0c77345e0` | `en` instructions; candidate text may be original-language | `reagent-topic-relevance/v1` | direct topical-relevance instruction |
| pointwise B | `relevance-pointwise-b/v1` | `sha256:da33134eda1397604c442fd1d76a8c9dcd34453da8a26c97a7acf91326a5a918` | `en` instructions; candidate text may be original-language | `reagent-topic-relevance/v1` | semantically equivalent category-structured paraphrase |
| mirrored pairwise | `relevance-pairwise-mirrored/v1` | `sha256:440b5a34c29a4802226b3f4e315b5259751c48a4c668d2d3f56263abb7dfbb92` | `en` instructions; candidate text may be original-language | `reagent-topic-relevance/v1` | local relevance comparison only |

Registry schema: `reagent-judge-prompt-registry/v1`.

## Pointwise contract

Input fields: topic/evaluation/candidate identities, topic description, optional
research question, inclusion/exclusion rubric, title, bounded abstract preview,
year, venue, content scope, metadata checksum, prompt/rubric/schema versions,
and request checksum.

Prohibited fields: OpenAlex/provider rank, rank, deterministic rank score,
citation count, provider relevance score, another judgment, and an existing
human label.

Output fields: label, confidence, short supporting spans, concise reason,
uncertainties, and insufficient-information flag under the implemented
`AutomatedJudgment` contract.

Both prompts:

- restrict the task to topical relevance;
- prohibit scientific-quality/truth/novelty/venue inference;
- require `CANNOT_JUDGE` when evidence is insufficient;
- restrict supporting spans to short exact excerpts from the supplied preview.

A and B are **semantically equivalent paraphrases with different reasoning
structures**. They are correlated checks from one model, not independent
evidence. A emphasizes direct label selection and prohibited assessment; B
maps the rubric categories into a decision structure. Agreement is interpreted
as tested prompt stability only.

Known risks: instruction-language effects on non-English content, category-order
anchoring, provider-added structured-output instructions, model serving drift,
and correlated errors.

## Pairwise contract

Inputs are topic, two pseudonymous candidate IDs, two titles/previews, rubric,
prompt version/hash, and order identity. Rank, citations, venue quality, prior
labels, and another result are prohibited. Output is one candidate ID or `TIE`
and a topical-relevance reason.

Each pair is evaluated twice with candidate order reversed. A prompt/hash change
or a one-sided invocation invalidates the pairwise consistency result.

## Provider adaptation rule

A future provider adapter may wrap the canonical prompt in the provider's
required role/schema envelope, but it must record:

- canonical ReAgent prompt hash;
- exact rendered provider request hash;
- provider-added schema/system behavior where documented;
- adapter and SDK versions;
- model ID and fixed effort/sampling configuration.

It may not silently rewrite the semantic instructions or use an SDK
schema-transform that changes constraints. If the current schema is unsupported,
calibration stops for a new reviewed prompt/schema version.

## Freeze conditions

This record becomes executable only through owner approval of ADR 0006 and all
blocking data/budget decisions. Any source prompt, rubric, schema, language
instruction, prohibited-field set, or output-shape change creates a new freeze
ID and invalidates direct comparison.

