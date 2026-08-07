import type { Metadata } from "next";

import { ProgressProductPanel } from "@/components/progress-product-panel";

export const metadata: Metadata = { title: "Project progress" };

export default async function ProgressPage(props: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ workflow_instance_id?: string }>;
}) {
  const { id } = await props.params;
  const { workflow_instance_id } = await props.searchParams;
  return <ProgressProductPanel projectId={id} initialWorkflowInstanceId={workflow_instance_id} />;
}
