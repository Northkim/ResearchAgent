"use client";

import Link from "next/link";
import { useState } from "react";

import { formatDateTime, truncateId } from "@/lib/format";
import type { Approval } from "@/types/api";

import { StatusBadge } from "./status-badge";

interface CandidatePreview {
  paper_id: string;
  title: string;
  authors: Array<{ name: string }>;
  publication_year: number | null;
  publication_venue: string | null;
  abstract: string | null;
  relevance_score: number;
  ranking_explanation: string;
  inclusion_status: string;
  source_provider: string;
  abstract_only: boolean;
}

function candidates(action: Record<string, unknown>): CandidatePreview[] {
  const resolved = action.resolved_inputs;
  if (!resolved || typeof resolved !== "object") return [];
  const preview = (resolved as Record<string, unknown>).approval_preview;
  return Array.isArray(preview) ? preview as CandidatePreview[] : [];
}

export function ApprovalCard({
  approval,
  busy = false,
  onApprove,
  onReject,
}: {
  approval: Approval;
  busy?: boolean;
  onApprove: (approval: Approval, reason: string) => void;
  onReject: (approval: Approval, reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  const action = approval.requested_action;
  const stepId = typeof action.approval_step_id === "string"
    ? action.approval_step_id
    : approval.step_run_id;
  const candidatePapers = candidates(action);

  return (
    <article className="approval-card">
      <div className="approval-heading">
        <div>
          <p className="eyebrow">Human gate</p>
          <h2>{approval.prompt}</h2>
        </div>
        <StatusBadge status={approval.status} />
      </div>

      {candidatePapers.length ? (
        <section className="candidate-preview" aria-labelledby={`candidates-${approval.id}`}>
          <div>
            <p className="eyebrow">Exact candidate set</p>
            <h3 id={`candidates-${approval.id}`}>
              Review {candidatePapers.length} selected synthetic papers
            </h3>
            <p className="candidate-warning">
              Abstract-only: approval binds these paper IDs and the immutable
              selected_papers.json checksum. It does not approve full text.
            </p>
          </div>
          <ol>
            {candidatePapers.map((paper, index) => (
              <li key={paper.paper_id}>
                <div className="candidate-title">
                  <span>[P{index + 1}]</span>
                  <div>
                    <strong>{paper.title}</strong>
                    <small>
                      {paper.authors.map((author) => author.name).join(", ")} ·{" "}
                      {paper.publication_year ?? "n.d."} ·{" "}
                      {paper.publication_venue ?? "Synthetic venue"}
                    </small>
                  </div>
                  <b>{Math.round(paper.relevance_score * 100)}%</b>
                </div>
                <p>{paper.abstract}</p>
                <dl>
                  <div><dt>Rank rationale</dt><dd>{paper.ranking_explanation}</dd></div>
                  <div><dt>Inclusion</dt><dd>{paper.inclusion_status}</dd></div>
                  <div><dt>Provider</dt><dd>{paper.source_provider}</dd></div>
                  <div><dt>Scope</dt><dd>{paper.abstract_only ? "abstract-only" : "invalid"}</dd></div>
                </dl>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <div className="approval-context">
        <div><span>Run</span><Link href={`/runs/${approval.workflow_run_id}`}>{truncateId(approval.workflow_run_id)} →</Link></div>
        <div><span>Step</span><strong>{String(stepId).replaceAll("_", " ")}</strong></div>
        <div><span>Policy</span><strong>{approval.policy_key}</strong></div>
        <div><span>Expires</span><strong>{approval.expires_at ? formatDateTime(approval.expires_at) : "No expiry"}</strong></div>
      </div>

      <details className="action-preview">
        <summary>Inspect fingerprinted action</summary>
        <pre>{JSON.stringify(approval.requested_action, null, 2)}</pre>
        <p className="mono">Fingerprint · {approval.request_fingerprint}</p>
      </details>

      {approval.status === "PENDING" ? (
        <div className="approval-decision">
          <label>
            Decision note <span>optional</span>
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Add context for the execution record…"
            />
          </label>
          <div className="approval-actions">
            <button
              type="button"
              className="button button-danger"
              onClick={() => onReject(approval, reason)}
              disabled={busy}
            >
              Reject & cancel
            </button>
            <button
              type="button"
              className="button button-primary"
              onClick={() => onApprove(approval, reason)}
              disabled={busy}
            >
              {busy ? "Recording decision…" : "Approve & continue"}
            </button>
          </div>
        </div>
      ) : null}
    </article>
  );
}
