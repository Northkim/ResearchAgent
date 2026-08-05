import type { Metadata } from "next";

import { LocalProjectList } from "@/components/local-project-list";

export const metadata: Metadata = { title: "Projects" };

export default function ProjectsPage() {
  return <LocalProjectList />;
}
