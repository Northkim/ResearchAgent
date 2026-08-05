"use client";

import Link from "next/link";

import { apiClient } from "@/api/client";
import { useGeneratePackage, useProject } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";

import { PageHeader } from "./page-header";
import { ErrorState, LoadingState } from "./query-state";

export function PackageProductPanel({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  const generate = useGeneratePackage(projectId);
  if (project.isLoading) return <LoadingState label="Loading Package metadata" />;
  if (project.isError || !project.data) return <ErrorState title="Project unavailable" />;
  const pkg = project.data.current_package;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Portable Workflow Package"
        title="Move the task, not the credential."
        description="This deterministic ZIP carries the Literature Search topic, pinned instructions, local context, output contracts, and Progress Report tooling. It never carries an API key or database URL."
        action={<Link href={`/projects/${projectId}`} className="button button-ghost">Project overview</Link>}
      />
      {!pkg ? (
        <section className="package-empty">
          <p className="eyebrow">Ready to compile</p>
          <h2>Generate the local Codex workspace</h2>
          <p>The backend compiles and validates files only. It does not execute the Workflow or contact a Provider.</p>
          {generate.isError ? <p className="form-error" role="alert">{generate.error.message}</p> : null}
          <button className="button button-primary" onClick={() => generate.mutate()} disabled={generate.isPending}>
            {generate.isPending ? "Generating and validating…" : "Generate Workflow Package"}
          </button>
        </section>
      ) : (
        <>
          <section className="package-identity" aria-label="Package identity">
            <div><span>Package ID</span><code>{pkg.package_id}</code></div>
            <div><span>Package checksum</span><code>{pkg.package_checksum}</code></div>
            <div><span>ZIP checksum</span><code>{pkg.zip_checksum}</code></div>
            <div><span>Workflow</span><code>{pkg.workflow_id}@{pkg.workflow_version}</code></div>
            <div><span>Workflow checksum</span><code>{pkg.workflow_checksum}</code></div>
            <div><span>Generated</span><strong>{formatDateTime(pkg.generated_at)}</strong></div>
          </section>
          <div className="package-download-row">
            <a
              className="button button-primary"
              href={apiClient.packageDownloadUrl(projectId, pkg.package_id)}
              download={`${pkg.package_id}.zip`}
            >
              Download Package ZIP
            </a>
            <button className="button button-ghost" onClick={() => generate.mutate()} disabled={generate.isPending}>
              Verify deterministic build
            </button>
          </div>
          <section className="instruction-card">
            <p className="eyebrow">Codex local execution</p>
            <ol>
              <li>Save and extract the ZIP outside this repository.</li>
              <li>Run <code>python validate_package.py --root .</code>.</li>
              <li>Open the folder with Codex and tell it to follow <code>AGENT.md</code>.</li>
              <li>Keep inputs immutable; Codex writes only declared outputs, context, and one append-only Progress Report.</li>
              <li>Validate again, then upload the report explicitly with the committed local client.</li>
            </ol>
            <p><strong>Credentials are not included.</strong> OpenAlex is experimental and disabled by default; deterministic demonstrations may use the fake Proxy.</p>
          </section>
        </>
      )}
    </div>
  );
}
