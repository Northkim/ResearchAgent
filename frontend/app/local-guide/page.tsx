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
          <li>From the extracted folder run <code>python reagent_local.py run .</code>.</li>
          <li>The launcher validates the Package, starts a short-lived exact-Package session, and invokes Codex for one planning and synthesis round.</li>
          <li>Normal mode searches real OpenAlex metadata only through the ReAgent Proxy; explicit <code>--mode demo</code> uses labelled fictional results.</li>
          <li>The launcher validates the four outputs and one report, uploads it idempotently, verifies the projection, revokes the session, and stops.</li>
          <li>Return to the project Progress page to view the bounded summary and immutable receipt history.</li>
        </ol>
        <div className="boundary-callout">
          <strong>Current limits</strong>
          <p>OpenAlex is experimental and disabled by default. Fake Provider mode must be selected explicitly and is suitable only for fictional demonstrations. Progress upload is automatic after a successful round and supports upload-only retry. Claude Code is untested. Public deployment is unsupported.</p>
        </div>
      </section>
    </div>
  );
}
