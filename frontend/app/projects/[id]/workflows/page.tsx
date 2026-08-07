import { WorkflowBoard } from "@/components/workflow-board";

export default async function ProjectWorkflowsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <WorkflowBoard projectId={id} />;
}
