import type { Metadata } from "next";

import { RunDetailClient } from "@/components/run-detail-client";

export const metadata: Metadata = { title: "Run detail" };

export default async function RunDetailPage(props: PageProps<"/runs/[id]">) {
  const { id } = await props.params;
  return <RunDetailClient runId={id} />;
}
