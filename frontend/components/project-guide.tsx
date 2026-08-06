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
      <section><p className="eyebrow">Exact command</p><h2>Start one interactive round</h2><pre><code>python reagent_local.py run .</code></pre><p>Codex opens in the current terminal—no graphical window is expected. ReAgent prints six launcher stages, then returns control after Codex exits to validate, upload, verify the receipt and Progress projection, revoke the session, and stop.</p></section>
      <section><h2>Three owner checkpoints</h2><ol><li><strong>Search plan:</strong> review topic interpretation, query variants, bounds, screening criteria, and evidence limits. No search occurs until you confirm.</li><li><strong>Candidate screening:</strong> inspect bounded counts and themes, ask why a paper was included or excluded, and revise criteria within budget.</li><li><strong>Finalization:</strong> review selected count and cloud/local boundaries, then type <code>finish</code>. Outputs and the report are not finalized earlier.</li></ol></section>
      <section><h2>Normal mode versus demo mode</h2><div className="guide-columns"><article><h3>Interactive normal</h3><pre><code>python reagent_local.py run .</code></pre><p>Uses real OpenAlex Works metadata only through the ReAgent Proxy. It stops fail-closed if OpenAlex is disabled or unavailable. There is no fake fallback.</p></article><article><h3>Interactive demo</h3><pre><code>python reagent_local.py run . --mode demo</code></pre><p>Uses the deterministic fake Proxy. Every result and output is labelled fictional and cannot serve as normal research evidence.</p></article></div><details><summary>Advanced / unattended mode</summary><pre><code>python reagent_local.py run . --auto{"\n"}python reagent_local.py run . --mode demo --auto</code></pre><p>Auto mode preserves the fixed bounded LS1 policy for CI and explicitly requested batch work; it is never selected silently.</p></details></section>
      <section><h2>Files generated locally</h2><ul><li><code>outputs/search_plan.md</code></li><li><code>outputs/candidate_papers.json</code></li><li><code>outputs/selected_papers.json</code></li><li><code>outputs/literature_search_report.md</code></li><li>one append-only report under <code>memory/progress/reports/</code></li><li>one verified safe receipt under <code>memory/progress/receipts/</code></li></ul></section>
      <section><h2>Cloud and privacy boundary</h2><p>The uploaded Progress Report contains the round/status, query and paper counts, a concise result summary, evidence limitation, output names/checksums, warnings, and next action. Full candidate records, query text, complete report content, local context, Provider token, OpenAlex key, and database URL remain outside the cloud summary.</p></section>
      <section><h2>Interruption and recovery</h2><p>Ctrl+C is forwarded to Codex, the scoped session is revoked, no incomplete report is uploaded, and valid files remain. The next plain run stops on partial state so nothing is overwritten.</p><dl className="guide-definitions"><div><dt>Resume partial work</dt><dd><code>python reagent_local.py run . --resume</code> preserves valid artifacts and opens interactive Codex with recovery context.</dd></div><div><dt>Restart unreported round</dt><dd><code>python reagent_local.py run . --restart-round</code> requires an exact terminal confirmation and removes only declared round-1 mutable artifacts.</dd></div><div><dt>Upload pending</dt><dd>A valid report without a verified receipt triggers upload-only recovery on the same command; search and Codex do not rerun.</dd></div><div><dt>Round completed</dt><dd>A verified receipt prevents repetition and links back to the Project Progress page.</dd></div></dl></section>
      <section><h2>Common errors</h2><ul><li><strong>Codex CLI missing or unsupported:</strong> install a supported CLI and confirm <code>codex --version</code>.</li><li><strong>Codex not authenticated:</strong> run <code>codex login</code>; no OpenAlex credential belongs in the Package.</li><li><strong>No interactive terminal:</strong> run from a terminal, or choose <code>--auto</code> only intentionally.</li><li><strong>Package validation failed:</strong> remove only unintended files; bounded <code>.DS_Store</code> metadata is already handled.</li><li><strong>Local session or backend unavailable:</strong> confirm <code>make dev</code> is healthy on literal <code>127.0.0.1</code>.</li><li><strong>OpenAlex disabled:</strong> enable the accepted experimental backend path while keeping its key only in the backend environment.</li><li><strong>Upload outcome unknown:</strong> rerun the same command for idempotent upload-only verification.</li></ul></section>
      <div className="guide-actions"><Link href={`/projects/${projectId}/package`} className="button button-primary">Open Package page</Link><Link href={`/projects/${projectId}/progress`} className="button button-secondary">View progress</Link></div>
    </div>
  );
}
