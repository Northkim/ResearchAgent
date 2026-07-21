import Link from "next/link";

const navigation = [
  { href: "/", label: "Overview", eyebrow: "01" },
  { href: "/workflows", label: "Workflows", eyebrow: "02" },
  { href: "/approvals", label: "Approvals", eyebrow: "03" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <aside className="app-sidebar">
        <Link href="/" className="brand-lockup" aria-label="ReAgent dashboard">
          <span className="brand-mark">R</span>
          <span>
            <strong>ReAgent</strong>
            <small>Research operations</small>
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
            <strong>Prototype workspace</strong>
            <p>Connected through the stable Phase 7B API.</p>
          </div>
        </div>
      </aside>

      <main className="app-main">{children}</main>
    </div>
  );
}
