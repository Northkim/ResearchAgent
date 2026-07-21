"use client";

import Link from "next/link";
import { useState } from "react";

import { formatDateTime, truncateId } from "@/lib/format";
import type { Approval } from "@/types/api";

import { StatusBadge } from "./status-badge";

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
  const stepId = typeof action.step_id === "string" ? action.step_id : approval.step_run_id;

  return (
    <article className="approval-card">
      <div className="approval-heading">
        <div>
          <p className="eyebrow">Human gate</p>
          <h2>{approval.prompt}</h2>
        </div>
        <StatusBadge status={approval.status} />
      </div>

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
