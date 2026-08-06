"use client";

import Link from "next/link";
import { useState } from "react";

import { apiClient } from "@/api/client";
import { useGeneratePackage, useProject } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";

import { PageHeader } from "./page-header";
import { ErrorState, LoadingState } from "./query-state";

const launchCommand = "python reagent_local.py run .";

export function PackageProductPanel({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  const generate = useGeneratePackage(projectId);
  const [copied, setCopied] = useState(false);
  if (project.isLoading) return <LoadingState label="Loading Package metadata" />;
  if (project.isError || !project.data) return <ErrorState title="Project unavailable" />;
  const pkg = project.data.current_package;

  async function copyCommand() {
    await navigator.clipboard.writeText(launchCommand);
    setCopied(true);
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Portable local workspace"
        title="Download once. Run one complete Literature Search round."
        description="The Package contains the public topic, pinned Codex workflow, local state, output contracts, and automatic Progress upload tooling—never credentials."
        action={<Link href={`/projects/${projectId}`} className="button button-ghost">Project overview</Link>}
      />
      {!pkg ? (
        <section className="package-empty">
          <p className="eyebrow">Step 1 · Package not generated</p>
          <h2>Generate the credential-free local workspace</h2>
          <p>The backend compiles and validates files only. It does not execute research or contact OpenAlex.</p>
          {generate.isError ? <p className="form-error" role="alert">{generate.error.message}</p> : null}
          <button className="button button-primary" onClick={() => generate.mutate()} disabled={generate.isPending}>
            {generate.isPending ? "Generating and validating…" : "Generate Package"}
          </button>
        </section>
      ) : (
        <>
          <section className="package-primary-action">
            <div><p className="eyebrow">Step 1 · Package ready</p><h2>Download and extract outside this repository</h2><p>The ZIP remains movable and its immutable identity is verified before execution.</p></div>
            <div className="package-primary-buttons">
              <a className="button button-primary" href={apiClient.packageDownloadUrl(projectId, pkg.package_id)} download={`${pkg.package_id}.zip`}>Download Package ZIP</a>
              <button className="button button-ghost" onClick={() => generate.mutate()} disabled={generate.isPending}>{generate.isPending ? "Regenerating…" : "Regenerate current Package"}</button>
            </div>
          </section>
          <section className="launch-command-card">
            <div><p className="eyebrow">Step 2–3 · Extract, then launch</p><h2>Run from the extracted Package</h2></div>
            <div className="copy-command"><code>{launchCommand}</code><button className="button button-secondary" onClick={copyCommand}>{copied ? "Copied" : "Copy command"}</button></div>
            <p>This validates the Package, opens a short-lived exact-Package local session, launches Codex for one bounded round, uploads one Progress Report, verifies the receipt, revokes the session, and stops.</p>
          </section>
          <section className="expected-output-card">
            <div><p className="eyebrow">What remains local</p><h2>Four research artifacts</h2></div>
            <ul>
              <li><code>outputs/search_plan.md</code> — search strategy</li>
              <li><code>outputs/candidate_papers.json</code> — deduplicated candidate library</li>
              <li><code>outputs/selected_papers.json</code> — relevance decisions</li>
              <li><code>outputs/literature_search_report.md</code> — metadata/abstract synthesis</li>
            </ul>
            <p>Only a bounded Progress summary and artifact checksums are uploaded. The complete libraries and report remain in this folder.</p>
          </section>
          <section className="package-next-row">
            <div><strong>Step 4</strong><p>Return after the command finishes to view the uploaded summary and immutable receipt history.</p></div>
            <Link href={`/projects/${projectId}/progress`} className="button button-secondary">View progress</Link>
            <Link href={`/projects/${projectId}/guide`} className="text-link">Read full guide →</Link>
          </section>
          <aside className="boundary-note"><strong>Credentials are not included.</strong> Tokens stay process-local. Normal mode requires the explicitly enabled OpenAlex Proxy and never falls back to fake data. A bounded <code>.DS_Store</code> file is safely ignored; other undeclared files remain rejected.</aside>
          <details className="technical-details">
            <summary>Technical Package metadata</summary>
            <dl>
              <div><dt>Package ID</dt><dd><code>{pkg.package_id}</code></dd></div>
              <div><dt>Package checksum</dt><dd><code>{pkg.package_checksum}</code></dd></div>
              <div><dt>ZIP checksum</dt><dd><code>{pkg.zip_checksum}</code></dd></div>
              <div><dt>Workflow</dt><dd><code>{pkg.workflow_id}@{pkg.workflow_version}</code></dd></div>
              <div><dt>Workflow checksum</dt><dd><code>{pkg.workflow_checksum}</code></dd></div>
              <div><dt>Generated</dt><dd>{formatDateTime(pkg.generated_at)}</dd></div>
            </dl>
          </details>
        </>
      )}
    </div>
  );
}
