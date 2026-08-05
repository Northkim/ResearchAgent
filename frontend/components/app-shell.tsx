import Link from "next/link";

const navigation = [
  { href: "/projects", label: "Projects", eyebrow: "01" },
  { href: "/projects/new", label: "New project", eyebrow: "02" },
  { href: "/local-guide", label: "Local guide", eyebrow: "03" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <aside className="app-sidebar">
        <Link href="/projects" className="brand-lockup" aria-label="ReAgent projects">
          <span className="brand-mark">R</span>
          <span>
            <strong>ReAgent</strong>
            <small>Local research workspace</small>
          </span>
        </Link>

        <nav aria-label="Primary navigation" className="sidebar-nav">
          {navigation.map((item) => (
            <Link key={item.href} href={item.href} className="nav-link">
              <span>{item.eyebrow}</span>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="sidebar-note">
          <span className="live-dot" aria-hidden="true" />
          <div>
            <strong>Local V0.1</strong>
            <p>Codex executes research in your downloaded folder. Cloud execution is not the primary path.</p>
          </div>
        </div>
      </aside>

      <main className="app-main">{children}</main>
    </div>
  );
}
