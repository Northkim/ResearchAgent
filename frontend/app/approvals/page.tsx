import type { Metadata } from "next";

import { ApprovalQueue } from "@/components/approval-queue";

export const metadata: Metadata = { title: "Approvals" };

export default function ApprovalsPage() {
  return <ApprovalQueue />;
}
