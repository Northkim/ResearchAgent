import type { Metadata } from "next";

import { RunDetailClient } from "@/components/run-detail-client";
import { LegacyHostedBanner } from "@/components/legacy-hosted-banner";

export const metadata: Metadata = { title: "Run detail" };

export default async function RunDetailPage(props: PageProps<"/runs/[id]">) {
  const { id } = await props.params;
  return <><LegacyHostedBanner /><RunDetailClient runId={id} /></>;
}
