"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiClient, type UserSkillDetail } from "@/api/client";
import { PageHeader } from "@/components/page-header";
import { ErrorState, LoadingState } from "@/components/query-state";

export default function SkillDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [skill, setSkill] = useState<UserSkillDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    void apiClient.getUserSkill(id).then(setSkill).catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Skill unavailable");
    });
  }, [id]);

  async function deleteSkill() {
    setDeleting(true);
    setError(null);
    try {
      await apiClient.deleteUserSkill(id);
      router.push("/skills");
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Skill could not be deleted");
      setDeleting(false);
    }
  }

  if (!skill && !error) return <LoadingState label="Loading Skill" />;
  if (!skill) return <ErrorState title={error ?? "Skill unavailable"} />;

  return (
    <div className="page-stack page-narrow">
      <Link href="/skills" className="back-link">← Skills</Link>
      <PageHeader eyebrow="Skill" title={skill.name} description={skill.description} />

      <section className="plain-section" aria-labelledby="skill-projects-title">
        <h2 id="skill-projects-title">Used in Projects</h2>
        {skill.projects.length ? (
          <div className="overview-workflow-list">
            {skill.projects.map((project) => <div key={project.project_id}><strong><Link href={`/projects/${project.project_id}`}>{project.name}</Link></strong></div>)}
          </div>
        ) : <p className="muted-copy">Not used in a Project yet.</p>}
      </section>

      <section className="plain-section">
        <h2>Source</h2>
        <a href={skill.source_locator} target="_blank" rel="noreferrer" className="text-link">Open GitHub source ↗</a>
      </section>

      <details className="technical-details">
        <summary>Technical details</summary>
        <dl><div><dt>Exact revision</dt><dd><code>{skill.source_revision}</code></dd></div><div><dt>Source checksum</dt><dd><code>{skill.source_checksum}</code></dd></div></dl>
      </details>

      <details className="technical-details">
        <summary>Skill settings</summary>
        {!confirmDelete ? <button className="button button-ghost" type="button" onClick={() => setConfirmDelete(true)}>Delete skill</button> : (
          <div className="plain-section" role="alert">
            <p>{skill.projects.length ? `This Skill is used by ${skill.projects.length} Project${skill.projects.length === 1 ? "" : "s"}. Remove it from those Projects first.` : "Delete this Skill from your library?"}</p>
            <div className="button-row"><button className="button button-ghost" type="button" onClick={() => setConfirmDelete(false)} disabled={deleting}>Cancel</button><button className="button button-primary" type="button" onClick={deleteSkill} disabled={deleting || skill.projects.length > 0}>{deleting ? "Deleting…" : "Delete skill"}</button></div>
          </div>
        )}
        {error ? <p className="form-error" role="status">{error}</p> : null}
      </details>
    </div>
  );
}
