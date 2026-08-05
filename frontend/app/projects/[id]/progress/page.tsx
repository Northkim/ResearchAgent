import type { Metadata } from "next";

import { ProgressProductPanel } from "@/components/progress-product-panel";

export const metadata: Metadata = { title: "Project progress" };

export default async function ProgressPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return <ProgressProductPanel projectId={id} />;
}
