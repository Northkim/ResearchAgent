"use client";

import Link from "next/link";

import { useProject } from "@/api/hooks";

import { PageHeader } from "./page-header";
import { ErrorState, LoadingState } from "./query-state";

export function ProjectGuide({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  if (project.isLoading) return <LoadingState label="Loading project guide" />;
  if (project.isError || !project.data) return <ErrorState title="Project unavailable" />;

  return (
    <div className="page-stack guide-page">
      <PageHeader
        eyebrow="Project operation guide"
        title={`Run ${project.data.name} locally`}
        description="Literature Search turns one public topic into a bounded, transparent metadata-and-abstract synthesis. Codex performs the research in your Package; ReAgent transports metadata and displays a compact uploaded summary."
        action={<Link href={`/projects/${projectId}`} className="button button-ghost">Project overview</Link>}
      />

      <section><h2>Prerequisites</h2><ul><li>ReAgent is running on localhost with <code>make dev</code>.</li><li>Codex CLI is installed and available as <code>codex</code>.</li><li>Generate and extract the current Package outside this repository.</li><li>For normal mode, explicitly enable the experimental OpenAlex Proxy and provide the credential only to the backend process.</li></ul></section>
      <section><p className="eyebrow">Exact command</p><h2>Start one complete round</h2><pre><code>python reagent_local.py run .</code></pre><p>The command validates identities, obtains bounded capabilities, invokes Codex for planning and synthesis, performs at most three five-result searches, writes four outputs, finalizes exactly one report, uploads it idempotently, verifies the projection, revokes the session, and stops.</p></section>
      <section><h2>Normal mode versus demo mode</h2><div className="guide-columns"><article><h3>Normal</h3><p>Uses real OpenAlex Works metadata only through the ReAgent Proxy. It stops fail-closed if OpenAlex is disabled or unavailable. There is no fake fallback.</p></article><article><h3>Explicit demo</h3><pre><code>python reagent_local.py run . --mode demo</code></pre><p>Uses the deterministic fake Proxy. Every result and output is labelled fictional and cannot serve as normal research evidence.</p></article></div></section>
      <section><h2>Files generated locally</h2><ul><li><code>outputs/search_plan.md</code></li><li><code>outputs/candidate_papers.json</code></li><li><code>outputs/selected_papers.json</code></li><li><code>outputs/literature_search_report.md</code></li><li>one append-only report under <code>memory/progress/reports/</code></li><li>one verified safe receipt under <code>memory/progress/receipts/</code></li></ul></section>
      <section><h2>Cloud and privacy boundary</h2><p>The uploaded Progress Report contains the round/status, query and paper counts, a concise result summary, evidence limitation, output names/checksums, warnings, and next action. Full candidate records, query text, complete report content, local context, Provider token, OpenAlex key, and database URL remain outside the cloud summary.</p></section>
      <section><h2>Completion and recovery states</h2><dl className="guide-definitions"><div><dt>Round completed</dt><dd>The receipt and Progress projection both verify. A repeat command reports that the round is already uploaded.</dd></div><div><dt>Upload pending</dt><dd>A valid report exists without a receipt. Run the same command; it performs upload-only retry and does not rerun search or Codex.</dd></div><div><dt>Partial local state</dt><dd>Outputs or operations exist without a valid report. The launcher stops without overwriting them; preserve the folder and inspect the last completed stage.</dd></div><div><dt>OpenAlex unavailable</dt><dd>Enable the experimental normal-mode adapter in the local backend session or explicitly choose demo mode for fictional demonstration only.</dd></div></dl></section>
      <section><h2>Common errors</h2><ul><li><strong>Package validation failed:</strong> remove only unintended files; bounded <code>.DS_Store</code> metadata is already handled.</li><li><strong>Local session unavailable:</strong> confirm the backend uses literal <code>127.0.0.1</code> and V0.1 local mode is enabled.</li><li><strong>Codex stage failed:</strong> preserve the Package and follow the partial-state message; do not delete or overwrite outputs.</li><li><strong>Upload outcome unknown:</strong> rerun the same command for an idempotent upload-only verification.</li></ul></section>
      <div className="guide-actions"><Link href={`/projects/${projectId}/package`} className="button button-primary">Open Package page</Link><Link href={`/projects/${projectId}/progress`} className="button button-secondary">View progress</Link></div>
    </div>
  );
}
