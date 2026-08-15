import type { Metadata } from "next";

import { WorkflowDetail } from "@/components/workflow-detail";

export const metadata: Metadata = { title: "Workflow Detail" };

export default async function WorkflowDetailPage({ params }: { params: Promise<{ id: string; workflow_instance_id: string }> }) {
  const { id, workflow_instance_id } = await params;
  return <WorkflowDetail projectId={id} workflowInstanceId={workflow_instance_id} />;
}
