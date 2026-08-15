import Link from "next/link";

const items = [
  { label: "Overview", suffix: "" },
  { label: "Workflows", suffix: "/workflows" },
  { label: "Outputs", suffix: "/outputs" },
  { label: "Activity", suffix: "/progress" },
] as const;

export function ProjectNavigation({ projectId, active }: {
  projectId: string;
  active: "Overview" | "Workflows" | "Outputs" | "Activity" | "Help";
}) {
  const root = `/projects/${projectId}`;

  return (
    <nav className="project-navigation" aria-label="Project">
      {items.map((item) => {
        const href = `${root}${item.suffix}`;
        const current = item.label === active;
        return (
          <Link key={item.label} href={href} aria-current={current ? "page" : undefined}>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
