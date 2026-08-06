import type { Metadata } from "next";

import { ProjectGuide } from "@/components/project-guide";

export const metadata: Metadata = { title: "Literature Search guide" };

export default async function ProjectGuidePage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return <ProjectGuide projectId={id} />;
}
