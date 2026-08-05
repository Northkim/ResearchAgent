import type { Metadata } from "next";

import { ApprovalQueue } from "@/components/approval-queue";
import { LegacyHostedBanner } from "@/components/legacy-hosted-banner";

export const metadata: Metadata = { title: "Approvals" };

export default function ApprovalsPage() {
  return <><LegacyHostedBanner /><ApprovalQueue /></>;
}
