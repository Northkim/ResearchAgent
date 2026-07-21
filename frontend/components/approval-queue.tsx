"use client";

import { useApprovalDecision, useApprovals } from "@/api/hooks";
import type { Approval } from "@/types/api";

import { ApprovalCard } from "./approval-card";
import { PageHeader } from "./page-header";
import { EmptyState, ErrorState, LoadingState } from "./query-state";

export function ApprovalQueue() {
  const approvals = useApprovals("PENDING");
  const decision = useApprovalDecision();

  function decide(approval: Approval, action: "approve" | "reject", reason: string) {
    decision.mutate({ approval, decision: action, reason });
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Approval desk"
        title="Put judgment where it matters."
        description="Every request is bound to one workflow version, step attempt, and action fingerprint. Approval resumes that exact plan; rejection safely cancels it."
        action={<span className="count-pill">{approvals.data?.total ?? 0} pending</span>}
      />

      {decision.isError ? (
        <ErrorState title="Decision was not recorded" message={decision.error.message} />
      ) : null}
      {decision.isSuccess ? (
        <div className="success-banner" role="status">
          Decision recorded. The run is now {decision.data.workflow_run.status.toLowerCase().replaceAll("_", " ")}.
        </div>
      ) : null}
      {approvals.isLoading ? <LoadingState label="Loading pending approvals" /> : null}
      {approvals.isError ? <ErrorState message={approvals.error.message} /> : null}
      {approvals.data?.approvals.length === 0 ? (
        <EmptyState
          title="No approvals are waiting"
          message="The agent can continue without reviewer intervention for now."
        />
      ) : null}
      <div className="approval-list">
        {approvals.data?.approvals.map((approval) => (
          <ApprovalCard
            key={approval.id}
            approval={approval}
            busy={decision.isPending}
            onApprove={(item, reason) => decide(item, "approve", reason)}
            onReject={(item, reason) => decide(item, "reject", reason)}
          />
        ))}
      </div>
    </div>
  );
}
