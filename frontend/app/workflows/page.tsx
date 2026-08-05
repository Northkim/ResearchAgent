import type { Metadata } from "next";

import { WorkflowCatalog } from "@/components/workflow-catalog";
import { LegacyHostedBanner } from "@/components/legacy-hosted-banner";

export const metadata: Metadata = { title: "Workflows" };

export default function WorkflowsPage() {
  return <><LegacyHostedBanner /><WorkflowCatalog /></>;
}
