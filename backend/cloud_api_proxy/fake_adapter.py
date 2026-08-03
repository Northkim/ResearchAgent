"""Pure deterministic fictional paper search for R3B qualification."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.research.contracts import PaperAuthor, PaperRecord, canonical_hash

from .contracts import ADAPTER_ID, PaperSearchV01Request

_FIXED_TIME = datetime(2026, 8, 4, 0, 0, tzinfo=UTC)


class DeterministicFakePaperSearchAdapter:
    adapter_id = ADAPTER_ID

    def __init__(self) -> None:
        self.invocation_count = 0

    def search(self, request: PaperSearchV01Request) -> dict:
        self.invocation_count += 1
        papers = [self._paper(request.query, index).to_dict() for index in range(1, request.max_results + 1)]
        return {
            "schema_version": "paper-search-result/v0.1",
            "source_classification": "WHOLLY_FICTIONAL_SYNTHETIC_FIXTURE",
            "untrusted_provider_data": True,
            "papers": papers,
        }

    def _paper(self, query: str, index: int) -> PaperRecord:
        provider_id = f"r3b-fictional-{index:02d}"
        doi = f"10.5555/r3b.fictional.{index:02d}"
        raw = {
            "provider_id": provider_id,
            "query": query,
            "index": index,
            "fictional": True,
        }
        return PaperRecord(
            paper_id=PaperRecord.internal_id(provider=self.adapter_id, provider_id=provider_id, doi=doi),
            provider_id=provider_id,
            title=f"Fictional metadata result {index} for {query}",
            authors=(PaperAuthor(name=f"Fictional Author {index}"),),
            abstract=None,
            publication_year=2040 + index,
            publication_venue="Synthetic Proxy Qualification Catalog",
            source_provider=self.adapter_id,
            source_url=f"https://example.invalid/r3b/{provider_id}",
            doi=doi,
            retrieved_at=_FIXED_TIME,
            raw_metadata_hash=canonical_hash(raw),
            metadata_limitations=("Fictional deterministic metadata; not a research source.",),
        )
