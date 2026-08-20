"use client";

import { useState } from "react";

import type { CanonicalArtifactReference } from "@/types/api";

import { CopyCommand } from "./copy-command";

const PAPER_SCHEMA = "reagent.artifact-presentation.selected-paper-library/v0.1";
const IDEA_SCHEMA = "reagent.artifact-presentation.selected-research-idea/v0.1";
const MANUSCRIPT_SCHEMA = "reagent.artifact-presentation.manuscript-draft/v0.1";
const REVIEW_SCHEMA = "reagent.artifact-presentation.review-report/v0.1";
const REVIEW_SCHEMA_V2 = "reagent.artifact-presentation.review-report/v0.2";
const EXPERIMENT_SCHEMA = "reagent.artifact-presentation.experiment-record/v0.2";

type PaperPresentation = {
  selected_count: number;
  selection_status: string;
  evidence_basis: string[];
  limitations: string[];
  papers_truncated: boolean;
  papers: Array<{
    title: string;
    authors: string[];
    year: number | null;
    identifier_kind: "DOI" | "PROVIDER_ID";
    identifier: string;
    why_selected: string;
    evidence_availability: string;
    limitation: string;
  }>;
};

type IdeaPresentation = {
  title: string;
  summary: string;
  research_question: string;
  observed_gap: string;
  proposed_direction: string;
  assumptions: string[];
  risks: string[];
  validation_needed: string[];
  literature_basis_count: number;
};

export type ManuscriptPresentation = {
  mode: "INITIAL" | "REVISION";
  title: string;
  summary: string;
  sections: string[];
  evidence_coverage: { claim_count: number; supported_claim_count: number; planned_claim_count: number; unavailable_claim_count: number };
  result_availability: "AVAILABLE" | "UNAVAILABLE";
  limitations: string[];
  owner_review_status: "APPROVED" | "NOT_REPORTED";
  changed_sections: string[];
  change_summary: string | null;
  issue_dispositions: Array<{ issue_id: string; disposition: string }>;
  unresolved_issue_count: number;
};

export type ReviewPresentation = {
  reviewed_manuscript: { artifact_id: string; artifact_type: string; artifact_checksum: string };
  scope: string;
  status: "NO_BLOCKING_ISSUES" | "REVISION_REQUIRED" | "INSUFFICIENT_EVIDENCE";
  summary: string;
  issues: Array<{ issue_id: string; category?: string; severity: "MAJOR" | "MINOR"; blocking: boolean; anchor?: string | null; rationale?: string | null; summary?: string; requested_revision: string | null; status?: "REPORTED" }>;
  requested_revisions?: string[];
  unresolved_evidence_gaps: string[];
  reproducibility_findings: string[];
  limitations: string[];
  owner_review_status: "APPROVED" | "NOT_REPORTED";
};

function exactPayload(artifact: CanonicalArtifactReference, schema: string): Record<string, unknown> | null {
  const presentation = artifact.presentation;
  if (
    !presentation
    || presentation.schema_identity !== schema
    || presentation.artifact_id !== artifact.artifact_id
    || presentation.artifact_checksum !== artifact.content_checksum
    || presentation.payload?.presentation_checksum !== presentation.presentation_checksum
    || presentation.payload?.schema !== schema
  ) return null;
  return presentation.payload;
}

function CopyValue({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return <span><code>{value}</code> <button type="button" className="text-link" aria-label={`Copy ${label}`} onClick={async () => { await navigator.clipboard.writeText(value); setCopied(true); }}>{copied ? "Copied" : "Copy"}</button></span>;
}

function MissingPreview({ selection }: { selection: boolean }) {
  return <div className="boundary-callout"><strong>{selection ? "Preview not yet reported from Local Workspace." : "Local result preview has not yet been reported."}</strong>{selection ? <p>The exact result can still be selected using its verified metadata.</p> : <><p>The research result is complete; only its bounded browser preview is missing.</p><CopyCommand command="python reagent_local.py artifact refresh ." label="Refresh result preview locally" /></>}</div>;
}

function PaperLibraryPreview({ value, compact }: { value: PaperPresentation; compact: boolean }) {
  return <section className="plain-section" aria-label="Selected paper library preview">
    <h3>Selected paper library</h3>
    <p><strong>{value.selected_count}</strong> selected paper{value.selected_count === 1 ? "" : "s"} · {value.selection_status.toLocaleLowerCase()}</p>
    {value.evidence_basis.length ? <p>Evidence available: {value.evidence_basis.map((item) => item.replaceAll("_", " ").toLocaleLowerCase()).join(", ")}.</p> : null}
    <div className="page-stack">
      {value.papers.slice(0, compact ? 3 : value.papers.length).map((paper, index) => <article className="output-highlight" key={`${paper.identifier}-${index}`}>
        <strong>{paper.title}</strong>
        <p>{paper.authors.join(", ")}{paper.year ? ` · ${paper.year}` : ""}</p>
        <p>{paper.identifier_kind === "DOI" ? "DOI" : "Stable identifier"}: <CopyValue value={paper.identifier} label={paper.identifier_kind === "DOI" ? "DOI" : "stable identifier"} /></p>
        {!compact ? <><p><strong>Why selected:</strong> {paper.why_selected}</p><p><strong>Evidence limitation:</strong> {paper.limitation}</p></> : null}
      </article>)}
    </div>
    {(value.papers_truncated || compact && value.papers.length > 3) ? <p className="muted-copy">Showing a bounded preview in the original selected-paper order.</p> : null}
    <div><strong>Evidence limitations</strong><ul>{value.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul></div>
  </section>;
}

function List({ title, values }: { title: string; values: string[] }) {
  if (!values.length) return null;
  return <div><strong>{title}</strong><ul>{values.map((item, index) => <li key={index}>{item}</li>)}</ul></div>;
}

function IdeaPreview({ value, compact }: { value: IdeaPresentation; compact: boolean }) {
  return <section className="plain-section" aria-label="Selected research idea preview">
    <p className="eyebrow">Selected research idea</p><h3>{value.title}</h3>
    <p>{value.summary}</p>
    <div className="input-readiness-list">
      <div><div><strong>Research question</strong><small>{value.research_question}</small></div><span>Selected</span></div>
      {!compact ? <><div><div><strong>Observed gap</strong><small>{value.observed_gap}</small></div><span>To investigate</span></div><div><div><strong>Proposed direction</strong><small>{value.proposed_direction}</small></div><span>In scope</span></div></> : null}
    </div>
    {!compact ? <div className="page-stack"><List title="Assumptions" values={value.assumptions} /><List title="Risks and limitations" values={value.risks} /><List title="Further validation needed" values={value.validation_needed} /><p>Grounded in {value.literature_basis_count} selected literature source{value.literature_basis_count === 1 ? "" : "s"}.</p></div> : <List title="Scope and limitations" values={[...value.risks, ...value.validation_needed].slice(0, 3)} />}
  </section>;
}

function DownstreamMissing({ selection }: { selection: boolean }) {
  return <div className="boundary-callout"><strong>{selection ? "Preview not yet reported from Local Workspace." : "Local preview has not yet been reported."}</strong><p>{selection ? "The exact Artifact remains available for explicit selection." : "The complete research product remains in the Local Workspace."}</p></div>;
}

function ManuscriptPreview({ value, compact }: { value: ManuscriptPresentation; compact: boolean }) {
  const coverage = value.evidence_coverage;
  return <section className="plain-section" aria-label={`${value.mode === "REVISION" ? "Revised" : "Initial"} manuscript preview`}>
    <p className="eyebrow">{value.mode === "REVISION" ? "Revised manuscript" : "Initial manuscript"}</p>
    <h3>{value.title}</h3><p>{value.summary}</p>
    {value.sections.length ? <List title="Sections" values={value.sections.slice(0, compact ? 5 : value.sections.length)} /> : null}
    <div className="input-readiness-list">
      <div><div><strong>Evidence coverage</strong><small>{coverage.supported_claim_count} supported · {coverage.planned_claim_count} planned · {coverage.unavailable_claim_count} unavailable</small></div><span>{coverage.claim_count} claims</span></div>
      <div><div><strong>Experiment result</strong><small>{value.result_availability === "AVAILABLE" ? "Exact experiment evidence is represented." : "No observed experiment result is represented."}</small></div><span>{value.result_availability.toLocaleLowerCase()}</span></div>
    </div>
    {value.mode === "REVISION" && value.change_summary ? <><p><strong>Revision summary:</strong> {value.change_summary}</p><List title="Changed sections" values={value.changed_sections} />{!compact ? <List title="Issue disposition" values={value.issue_dispositions.map((item) => `${item.issue_id}: ${item.disposition.replaceAll("_", " ").toLocaleLowerCase()}`)} /> : null}<p>{value.unresolved_issue_count} unresolved Review issue{value.unresolved_issue_count === 1 ? "" : "s"}.</p></> : null}
    {!compact ? <List title="Unresolved limitations" values={value.limitations} /> : null}
    <p className="muted-copy">The complete {value.mode === "REVISION" ? "revised " : ""}manuscript remains in the Local Workspace.</p>
  </section>;
}

function ReviewPreview({ value, compact }: { value: ReviewPresentation; compact: boolean }) {
  return <section className="plain-section" aria-label="Review report preview">
    <p className="eyebrow">Review report</p><h3>{value.status.replaceAll("_", " ").toLocaleLowerCase()}</h3>
    <p>{value.summary}</p><p><strong>Review scope:</strong> {value.scope}</p>
    {value.issues.length ? <div className="review-issue-list" aria-label="Structured Review issues">{value.issues.slice(0, compact ? 3 : value.issues.length).map((issue) => <article className="review-issue-card" key={issue.issue_id}><div className="review-issue-heading"><strong>{issue.issue_id}</strong><span>{issue.severity.toLocaleLowerCase()} issue{issue.blocking ? " · blocking" : ""} · {issue.category?.replaceAll("_", " ").toLocaleLowerCase() ?? "review issue"}</span></div><p>{issue.summary ?? issue.rationale ?? issue.anchor ?? "Issue details remain in the Local Workspace."}</p>{issue.requested_revision ? <p><strong>Requested revision:</strong> {issue.requested_revision}</p> : null}<small>{issue.status?.toLocaleLowerCase() ?? "reported"}</small></article>)}</div> : <p>No structured issues were reported.</p>}
    {!compact ? <><List title="Requested revisions" values={value.requested_revisions ?? []} /><details className="secondary-control"><summary>Evidence gaps and limitations</summary><List title="Unresolved evidence gaps" values={value.unresolved_evidence_gaps} /><List title="Reproducibility findings" values={value.reproducibility_findings} /><List title="Limitations" values={value.limitations} /></details></> : null}
    <p className="muted-copy">The complete Review remains in the Local Workspace.</p>
  </section>;
}

function ExperimentCandidatePreview({ value }: { value: { blocks?: Array<{ kind: string; label: string; value: unknown }> } }) {
  const scalar = (label: string) => value.blocks?.find((item) => item.label.toLocaleLowerCase() === label)?.value;
  const finding = value.blocks?.find((item) => item.kind === "PROSE" && !["research objective", "limitations"].includes(item.label.toLocaleLowerCase()));
  return <section className="plain-section" aria-label="Experiment result preview"><p className="eyebrow">Experiment result</p><h3>{String(scalar("research objective") ?? "Bounded experiment result")}</h3><div className="input-readiness-list"><div><div><strong>Process outcome</strong></div><span>{String(scalar("process outcome") ?? "Not reported")}</span></div><div><div><strong>Evaluation validity</strong></div><span>{String(scalar("evaluation validity") ?? "Not reported")}</span></div><div><div><strong>Evidence status</strong></div><span>{String(scalar("scientific evidence status") ?? "Not reported")}</span></div></div>{finding ? <p><strong>{finding.label}:</strong> {String(finding.value)}</p> : null}</section>;
}

export function ArtifactPresentationPreview({ artifact, compact = false, selection = false }: { artifact: CanonicalArtifactReference; compact?: boolean; selection?: boolean }) {
  if (artifact.artifact_type === "selected-paper-library/v1") {
    const value = exactPayload(artifact, PAPER_SCHEMA);
    return value ? <PaperLibraryPreview value={value as unknown as PaperPresentation} compact={compact} /> : <MissingPreview selection={selection} />;
  }
  if (artifact.artifact_type === "selected-research-idea/v1") {
    const value = exactPayload(artifact, IDEA_SCHEMA);
    return value ? <IdeaPreview value={value as unknown as IdeaPresentation} compact={compact} /> : <MissingPreview selection={selection} />;
  }
  if (artifact.artifact_type === "manuscript-draft/v4" || artifact.artifact_type === "manuscript-draft/v5") {
    const value = exactPayload(artifact, MANUSCRIPT_SCHEMA);
    return value ? <ManuscriptPreview value={value as unknown as ManuscriptPresentation} compact={compact} /> : <DownstreamMissing selection={selection} />;
  }
  if (artifact.artifact_type === "review-report/v3") {
    const schema = artifact.presentation?.schema_identity === REVIEW_SCHEMA_V2 ? REVIEW_SCHEMA_V2 : REVIEW_SCHEMA;
    const value = exactPayload(artifact, schema);
    return value ? <ReviewPreview value={value as unknown as ReviewPresentation} compact={compact} /> : <DownstreamMissing selection={selection} />;
  }
  if (artifact.artifact_type === "experiment-record/v4" || artifact.artifact_type === "experiment-record/v5") {
    const value = exactPayload(artifact, EXPERIMENT_SCHEMA);
    return value ? <ExperimentCandidatePreview value={value as { blocks?: Array<{ kind: string; label: string; value: unknown }> }} /> : <DownstreamMissing selection={selection} />;
  }
  return null;
}
