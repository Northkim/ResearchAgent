"use client";

import { useState } from "react";

import type { CanonicalArtifactReference } from "@/types/api";

import { CopyCommand } from "./copy-command";

const PAPER_SCHEMA = "reagent.artifact-presentation.selected-paper-library/v0.1";
const IDEA_SCHEMA = "reagent.artifact-presentation.selected-research-idea/v0.1";

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

export function ArtifactPresentationPreview({ artifact, compact = false, selection = false }: { artifact: CanonicalArtifactReference; compact?: boolean; selection?: boolean }) {
  if (artifact.artifact_type === "selected-paper-library/v1") {
    const value = exactPayload(artifact, PAPER_SCHEMA);
    return value ? <PaperLibraryPreview value={value as unknown as PaperPresentation} compact={compact} /> : <MissingPreview selection={selection} />;
  }
  if (artifact.artifact_type === "selected-research-idea/v1") {
    const value = exactPayload(artifact, IDEA_SCHEMA);
    return value ? <IdeaPreview value={value as unknown as IdeaPresentation} compact={compact} /> : <MissingPreview selection={selection} />;
  }
  return null;
}
