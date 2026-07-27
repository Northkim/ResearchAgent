"use client";

import { apiClient } from "@/api/client";
import {
  useArtifactContent,
  useProviderUsage,
  useRunArtifacts,
} from "@/api/hooks";
import type { Artifact } from "@/types/api";

import { EmptyState, ErrorState, LoadingState } from "./query-state";

interface ProvenanceReference {
  citation_id: string;
  report_citation_label: string;
  title: string;
  authors: string[];
  year: number | null;
  source_url: string | null;
  doi: string | null;
}

function parseReferences(content: string | undefined): ProvenanceReference[] {
  if (!content) return [];
  try {
    const parsed = JSON.parse(content) as { citations?: unknown };
    if (!Array.isArray(parsed.citations)) return [];
    return parsed.citations.filter(
      (item): item is ProvenanceReference =>
        typeof item === "object" &&
        item !== null &&
        typeof (item as ProvenanceReference).report_citation_label === "string" &&
        typeof (item as ProvenanceReference).title === "string",
    );
  } catch {
    return [];
  }
}

function ArtifactList({ artifacts }: { artifacts: Artifact[] }) {
  if (artifacts.length === 0) {
    return (
      <EmptyState
        title="No research artifacts yet"
        message="Candidate artifacts appear before approval; publication artifacts appear after completion."
      />
    );
  }
  return (
    <ul className="artifact-list" aria-label="Research artifacts">
      {artifacts.map((artifact) => (
        <li key={artifact.id}>
          <div>
            <strong>{artifact.logical_name}</strong>
            <span>{artifact.kind} · {artifact.media_type} · {artifact.size} bytes</span>
            <code>{artifact.checksum}</code>
          </div>
          <a
            className="button button-ghost"
            href={apiClient.artifactContentUrl(artifact.id)}
            target="_blank"
            rel="noreferrer"
          >
            View / download
          </a>
        </li>
      ))}
    </ul>
  );
}

export function ResearchResults({
  runId,
  isResearchV2,
}: {
  runId: string;
  isResearchV2: boolean;
}) {
  const artifacts = useRunArtifacts(runId);
  const usage = useProviderUsage(runId);
  const reportArtifact = artifacts.data?.find((item) => item.logical_name === "report.md");
  const provenanceArtifact = artifacts.data?.find(
    (item) => item.logical_name === "provenance.json",
  );
  const report = useArtifactContent(reportArtifact?.id);
  const provenance = useArtifactContent(provenanceArtifact?.id);
  const references = parseReferences(provenance.data);

  if (!isResearchV2) return null;

  const totalCost = usage.data?.reduce(
    (sum, operation) => sum + (operation.estimated_cost_minor_units ?? 0),
    0,
  ) ?? 0;
  const settled = usage.data?.every(
    (operation) =>
      operation.status === "SUCCEEDED" && operation.settlement_state === "SETTLED",
  ) ?? false;

  return (
    <div className="research-stack">
      <section className="scope-notice" aria-label="Research source limitation">
        <strong>Abstract-only synthetic demonstration</strong>
        <p>
          Every title, author, venue, paper and abstract is an invented fixture.
          No live literature provider, real LLM, credential, network request or
          full text is used.
        </p>
      </section>

      <section className="detail-card report-card" aria-labelledby="report-title">
        <div className="card-heading">
          <div>
            <p className="eyebrow">Published result</p>
            <h2 id="report-title">Grounded Markdown report</h2>
          </div>
          {reportArtifact ? <span>{reportArtifact.checksum.slice(0, 20)}…</span> : null}
        </div>
        {report.isLoading ? <LoadingState label="Loading verified report" /> : null}
        {report.isError ? (
          <ErrorState title="Report integrity check failed" message={report.error.message} />
        ) : null}
        {report.data ? (
          <pre className="markdown-report" aria-label="Generated Markdown report">
            {report.data}
          </pre>
        ) : !report.isLoading ? (
          <EmptyState
            title="Report not published"
            message="The report remains unavailable until approval, synthesis, and the provenance gate all succeed."
          />
        ) : null}
      </section>

      <section className="detail-card" aria-labelledby="citations-title">
        <div className="card-heading">
          <div>
            <p className="eyebrow">Grounding</p>
            <h2 id="citations-title">Citation references</h2>
          </div>
          <span>{references.length} citations</span>
        </div>
        {references.length ? (
          <ol className="citation-list">
            {references.map((reference) => (
              <li key={reference.citation_id}>
                <strong>{reference.report_citation_label} {reference.title}</strong>
                <span>
                  {reference.authors.join(", ")} · {reference.year ?? "n.d."} · synthetic
                </span>
                {reference.source_url ? (
                  <a href={reference.source_url} target="_blank" rel="noreferrer">
                    Open synthetic citation link
                  </a>
                ) : null}
              </li>
            ))}
          </ol>
        ) : (
          <EmptyState
            title="Citations not available"
            message="Citation links are loaded from the integrity-checked provenance artifact after publication."
          />
        )}
      </section>

      <section className="detail-card" aria-labelledby="artifacts-title">
        <div className="card-heading">
          <div>
            <p className="eyebrow">Durable outputs</p>
            <h2 id="artifacts-title">Artifact ledger</h2>
          </div>
          <span>{artifacts.data?.length ?? 0} artifacts</span>
        </div>
        {artifacts.isLoading ? <LoadingState label="Loading artifact ledger" /> : null}
        {artifacts.isError ? (
          <ErrorState title="Artifacts unavailable" message={artifacts.error.message} />
        ) : null}
        {artifacts.data ? <ArtifactList artifacts={artifacts.data} /> : null}
      </section>

      <section className="detail-card" aria-labelledby="usage-title">
        <div className="card-heading">
          <div>
            <p className="eyebrow">Budget ledger</p>
            <h2 id="usage-title">Provider usage</h2>
          </div>
          <span>{totalCost} USD minor units · {settled ? "all settled" : "pending"}</span>
        </div>
        {usage.isLoading ? <LoadingState label="Loading provider usage" /> : null}
        {usage.isError ? (
          <ErrorState title="Usage unavailable" message={usage.error.message} />
        ) : null}
        {usage.data?.length ? (
          <div className="usage-table-wrap">
            <table className="usage-table">
              <thead>
                <tr>
                  <th>Step</th>
                  <th>Provider</th>
                  <th>Operation</th>
                  <th>State</th>
                  <th>Cost</th>
                </tr>
              </thead>
              <tbody>
                {usage.data.map((operation) => (
                  <tr key={operation.id}>
                    <td>{operation.logical_step_id.replaceAll("_", " ")}</td>
                    <td>{operation.provider_identity}</td>
                    <td>{operation.operation_kind.replaceAll("_", " ")}</td>
                    <td>{operation.status.toLowerCase()} / {operation.settlement_state.toLowerCase()}</td>
                    <td>{operation.estimated_cost_minor_units ?? 0} {operation.cost_currency ?? "USD"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No provider usage yet"
            message="Durable zero-cost reservations appear when fake providers execute."
          />
        )}
      </section>
    </div>
  );
}
