import type { Metadata } from "next";

import { ProjectOutputs } from "@/components/project-outputs";

export const metadata: Metadata = { title: "Project Outputs" };

export default async function ProjectOutputsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ProjectOutputs projectId={id} />;
}
