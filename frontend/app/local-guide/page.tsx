import type { Metadata } from "next";
import Link from "next/link";

import { CopyCommand } from "@/components/copy-command";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = { title: "Local execution guide" };

export default function LocalGuidePage() {
  return (
    <div className="page-stack page-narrow">
      <PageHeader
        eyebrow="Supported local path"
        title="Local Workspace reference"
        description="General setup, safety, and recovery guidance for research that runs locally."
        action={<Link href="/projects" className="button button-ghost">Projects</Link>}
      />
      <section className="instruction-card instruction-card-large">
        <ol>
          <li>Create a Project using a fictional or public topic.</li>
          <li>Open that Project&apos;s Help page for its exact setup downloads and bootstrap command.</li>
          <li>Enter the Local Workspace and run <code>python reagent_local.py sync .</code>.</li>
          <li>Run <code>python reagent_local.py workflow list .</code> and use the displayed Literature Search command.</li>
          <li>The launcher validates the Package, starts a short-lived exact-Package session, and opens interactive Codex in the current terminal.</li>
          <li>Review and confirm the search plan before Provider search, inspect candidate screening, then type <code>finish</code> to finalize.</li>
          <li>Normal mode searches real OpenAlex metadata only through the ReAgent Proxy; explicit <code>--mode demo</code> uses labelled fictional results.</li>
          <li>After finalization, the launcher validates the four outputs and one report, uploads it idempotently, verifies the projection, revokes the session, and stops.</li>
          <li>Return to the Project Progress page to view the bounded summary.</li>
          <li>To use Idea Discovery, add it on the Workflow Board, sync locally, explicitly select a completed paper library, and run the card&apos;s input preparation and run commands.</li>
        </ol>
        <CopyCommand command="python reagent_local.py workflow list ." label="Workflow list command" />
        <div className="boundary-callout">
          <strong>Current limits</strong>
          <p>OpenAlex is experimental and disabled by default. Fake Provider mode must be selected explicitly and is suitable only for fictional demonstrations. Ctrl+C preserves valid local work and uploads nothing incomplete; use <code>--resume</code> for partial work. Progress upload is automatic only after finalization and supports upload-only retry. The browser cannot sync, prepare inputs, or run Codex. Public deployment is unsupported.</p>
        </div>
      </section>
    </div>
  );
}
