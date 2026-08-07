import type { Metadata } from "next";

import { ProjectHelp } from "@/components/project-help";

export const metadata: Metadata = { title: "Project help" };

export default async function ProjectHelpPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ProjectHelp projectId={id} />;
}
