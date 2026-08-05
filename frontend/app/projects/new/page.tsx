import type { Metadata } from "next";

import { ProjectCreateForm } from "@/components/project-create-form";

export const metadata: Metadata = { title: "New project" };

export default function NewProjectPage() {
  return <ProjectCreateForm />;
}
