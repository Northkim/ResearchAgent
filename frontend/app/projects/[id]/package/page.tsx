import type { Metadata } from "next";

import { PackageProductPanel } from "@/components/package-product-panel";

export const metadata: Metadata = { title: "Workflow Package" };

export default async function PackagePage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return <PackageProductPanel projectId={id} />;
}
