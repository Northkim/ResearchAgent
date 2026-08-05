import type { Metadata } from "next";

import { LocalProjectDetail } from "@/components/local-project-detail";

export const metadata: Metadata = { title: "Project" };

export default async function ProjectPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return <LocalProjectDetail projectId={id} />;
}
