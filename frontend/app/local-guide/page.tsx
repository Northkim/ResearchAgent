import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = { title: "Local execution guide" };

export default function LocalGuidePage() {
  return (
    <div className="page-stack page-narrow">
      <PageHeader
        eyebrow="Supported V0.1 path"
        title="Work locally with Codex."
        description="The downloaded folder—not a cloud runtime—holds the concrete research task, outputs, context, and continuation state."
        action={<Link href="/projects" className="button button-ghost">Projects</Link>}
      />
      <section className="instruction-card instruction-card-large">
        <ol>
          <li>Create a Literature Search project using a fictional or public topic.</li>
          <li>Generate and download the Package ZIP, then extract it outside the repository.</li>
          <li>Run the bundled validator and stop if integrity checks fail.</li>
          <li>Open that folder with Codex CLI and ask Codex to follow <code>AGENT.md</code>.</li>
          <li>Let Codex write only declared outputs, local context, and an append-only Progress Report.</li>
          <li>Validate the Package again.</li>
          <li>Use <code>python -m backend.progress_reports.client validate</code>, then the explicit <code>upload</code> command from the repository.</li>
          <li>Return to the project Progress page to view projection and history.</li>
        </ol>
        <div className="boundary-callout">
          <strong>Current limits</strong>
          <p>OpenAlex is experimental and disabled by default. Fake Provider mode is suitable for deterministic demonstrations. Progress upload is manual. Claude Code is untested. Public deployment is unsupported.</p>
        </div>
      </section>
    </div>
  );
}
