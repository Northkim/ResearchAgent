# ReAgent Provider Field Mapping

日期：2026-07-27；状态：**Proposed implementation map**。  
Source of truth: current ReAgent contracts in
`backend/research/contracts/models.py` and official provider schemas:
OpenAlex Developer/OpenAPI, Semantic Scholar Graph API 1.0, Crossref REST API
(all accessed 2026-07-27; URLs in `PAPER_SEARCH_EVIDENCE_REGISTER.md`).

Legend: **R** current `PaperRecord` core/required constructor field; **O** current
optional; **E** proposed enrichment not currently represented. Confidence refers
to cross-provider semantic confidence, not record completeness.

| ReAgent field | OpenAlex path | Semantic Scholar path | Crossref path | R/O/E | Normalization | confidence / conflict | retention & provenance |
|---|---|---|---|---|---|---|---|
| internal paper ID | derived from DOI else `id` | derived from DOI else `paperId` | derived from DOI | R | existing `PaperRecord.internal_id`; namespace IDs | high; never replace after persistence | retain; record rule/version + contributing IDs |
| provider ID | `id` (`W…`) | `paperId`; retain `corpusId` separately | `DOI` for Crossref records | R | strip URL prefix only for display; keep canonical native form | high within provider only | retain provider/version |
| title | `title`/`display_name` | `title` | `title[0]` | R | HTML entity decode, Unicode NFC, trim/collapse whitespace; preserve display form | medium-high; provider disagreement visible | retain normalized minimum + raw-field hash |
| normalized title | derived | derived | derived | E | Unicode NFKC + casefold + safe punctuation/whitespace normalization | advisory identity; never hard merge alone | retain value + normalizer version |
| authors | `authorships[].author.display_name`; IDs/ORCID | `authors[].name/authorId` | `author[].given/family/ORCID` | R | preserve order; display name NFC; comparison key NFKC/casefold; identifiers separate | medium; order/name/completeness differ | retain minimum, per-field provider provenance |
| publication year | `publication_year` | `year` | chosen publication date `date-parts[0][0]` | O | integer, valid range; record chosen date precedence | medium; online/print/issued differ | retain + source field |
| publication date | `publication_date` | `publicationDate` | `published-online`, `published-print`, `published`, `issued` | E | ISO date, preserve precision and date-kind | medium; semantics differ | retain chosen + all non-sensitive alternatives in provenance |
| venue/source | `primary_location.source.display_name` | `venue`, `publicationVenue.name`, `journal.name` | `container-title[0]`, event/publisher where type-specific | O | text sanitization; never infer peer review from venue | low-medium | retain + source path; advisory |
| abstract | reconstruct `abstract_inverted_index` | `abstract` | `abstract` (often JATS) | O | length cap; reconstruct/strip markup safely; NFC/control cleanup | low-medium; missing and content-quality/license risks | owner-controlled private retention; hash + provider/license marker; never public fixture by default |
| DOI | `doi` or `ids.doi` | `externalIds.DOI` | `DOI` | O | existing `normalize_doi`; agency check; syntax + metadata sanity | high when exact, but mismatch/version possible | retain; record every provider assertion and resolution |
| source URL | `primary_location.landing_page_url` else `doi`/`id` | `url` | `URL` / DOI resolver | O | HTTPS allowlist; prefer DOI resolver for citation; no automatic fetch | medium | retain URL + provider |
| language | `language` | no stable core field in current Graph paper schema | `language` | E | BCP-47-ish lowercase only when valid; otherwise raw advisory | low; missing/inferred/different | advisory; never hard gate without provider-specific test |
| document type | `type`, `type_crossref` | `publicationTypes` | `type`, `subtype` | E | versioned provider→ReAgent enum map, preserve raw value | low-medium; taxonomies differ | advisory + mapping version |
| open-access state | `open_access.oa_status`, `is_oa`, locations | `openAccessPdf` (availability object, not identical OA status) | `license[]`, `link[]` (not a normalized OA state) | E | preserve provider-native evidence; do not force common boolean | low; semantics differ | advisory, URLs/licenses retained |
| citation count | `cited_by_count` | `citationCount` | `is-referenced-by-count` | E | non-negative int + retrieval timestamp | low for cross-provider comparison; graph coverage differs | advisory only; **never quality score/hard gate** |
| external IDs | `ids` (DOI/MAG/PMID/PMCID, etc.) | `externalIds` (DOI/ArXiv/MAG/ACL/PMID/DBLP…) | DOI, ORCID/ROR/ISSN and relations | E | namespaced map; validate each namespace | high per exact namespace, missing common | retain allowlisted IDs + assertion provider |
| retraction/correction | `is_retracted`, `is_paratext` and related data | selected fields/corpus signals vary | `update-to`, `relation`, Crossmark-related metadata | E | explicit state/evidence, never infer absence means safe | medium-low | advisory/gate policy separately approved |
| provider updated timestamp | `updated_date` | no guaranteed equivalent in selected paper fields | `indexed.date-time`, `deposited`, `created` | E | UTC timestamp + semantic kind | medium; dates mean different events | retain for cache/revalidation |
| raw metadata hash | SHA-256 canonical selected/raw object | same | same | R | hash exact received bytes plus canonical normalized record separately | high integrity, not semantic correctness | retain hashes; raw bytes default not retained |
| provider retrieval timestamp | local receipt time | local receipt time | local receipt time | R | aware UTC clock from adapter boundary | high | retain ProviderOperation and PaperRecord |

## Hard-validation versus advisory fields

Safe hard validation:

- schema/version, nonempty provider/native ID, nonempty sanitized title;
- aware retrieval timestamp, valid SHA-256;
- DOI syntax if DOI is present (but DOI equality still requires identity sanity checks);
- response structure, pagination invariants, configured maximums.

Conditional hard validation:

- minimum paper count after deterministic dedup;
- publication year when user supplied a year gate and provider guarantees filter
  semantics; missing year must not be silently coerced;
- exact selected identity/checksum before approval.

Advisory only:

- authorship completeness/order, venue, language, document type, OA state,
  citation count, topics/concepts, provider relevance score, retraction absence,
  fuzzy identity score.

Expected missing fields:

- abstracts (especially Crossref/OpenAlex), DOI for non-DOI outputs, venue,
  language, exact date, ORCID, OA license, updated timestamp.

## Deterministic conflict policy

1. Preserve each provider assertion with provider/adapter/contract version and
   response hash.
2. Identity uses DOI/external IDs before names; no “last writer wins”.
3. Crossref field is canonical only for a confirmed Crossref-registered DOI and
   only for deposited DOI metadata; it does not automatically override a
   provider’s abstract or discovery relevance.
4. OpenAlex remains discovery source/ranking provenance.
5. S2 comparison adds verification/enrichment; disagreement yields
   `verified_with_conflict` or `ambiguous`, never silent overwrite.
6. Preferred display title/year/author set is selected by a versioned merge
   policy and records alternatives.
7. Preprint, conference, journal and corrected versions remain separate
   `PaperRecord`s with explicit version relations unless authoritative IDs prove
   the same manifestation.

## Proposed additive contract impact

Do not mutate `paper-record/v1` in place. A future milestone may add:

- `PaperRecordV2` or a separate `PaperEnrichment`/`ProviderAssertion` artifact
  for publication date, language, type, OA, citations, external IDs and update
  timestamp;
- `provider_verification.json` for merge evidence/conflicts;
- field-level provenance rather than an unbounded raw provider object.

The first OpenAlex adapter can map only current `PaperRecord` fields and place
missingness in `metadata_limitations`. No current field requires a migration.

