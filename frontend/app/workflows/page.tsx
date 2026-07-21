import type { Metadata } from "next";

import { WorkflowCatalog } from "@/components/workflow-catalog";

export const metadata: Metadata = { title: "Workflows" };

export default function WorkflowsPage() {
  return <WorkflowCatalog />;
}
