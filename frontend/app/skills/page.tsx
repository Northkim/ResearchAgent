"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { apiClient, UserSkill } from "@/api/client";
import { PageHeader } from "@/components/page-header";

export default function SkillsPage() {
  const [skills, setSkills] = useState<UserSkill[]>([]);
  const [attached, setAttached] = useState<Set<string>>(new Set());
  const [projectId, setProjectId] = useState("");
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [source, setSource] = useState("");
  const [revision, setRevision] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load(targetProject = projectId) {
    const library = await apiClient.listUserSkills();
    if (targetProject) {
      const selected = await apiClient.listProjectUserSkills(targetProject);
      const selectedById = new Map(selected.items.map((skill) => [skill.skill_id, skill]));
      setSkills(library.items.map((skill) => selectedById.get(skill.skill_id) ?? skill));
      setAttached(new Set(selected.items.map((skill) => skill.skill_id)));
    } else setSkills(library.items);
  }

  useEffect(() => {
    const target = new URLSearchParams(window.location.search).get("project") ?? "";
    // The query string selects the one Project-management mode after hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setProjectId(target);
    void load(target).catch((error) => setMessage(error instanceof Error ? error.message : "Skills unavailable"));
    // Initial URL is immutable for this page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function add(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setMessage(null);
    try {
      await apiClient.createUserSkill({
        name, description, source_locator: source,
        ...(revision ? { source_revision: revision } : {}),
      });
      setName(""); setDescription(""); setSource(""); setRevision(""); setAdding(false);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Skill could not be added");
    } finally { setBusy(false); }
  }

  async function saveProjectSkills() {
    setBusy(true); setMessage(null);
    try {
      const current = await apiClient.listProjectUserSkills(projectId);
      const currentIds = new Set(current.items.map((skill) => skill.skill_id));
      await Promise.all([
        ...skills.filter((skill) => attached.has(skill.skill_id) && !currentIds.has(skill.skill_id))
          .map((skill) => apiClient.attachProjectUserSkill(projectId, skill.skill_id)),
        ...skills.filter((skill) => !attached.has(skill.skill_id) && currentIds.has(skill.skill_id))
          .map((skill) => apiClient.detachProjectUserSkill(projectId, skill.skill_id)),
      ]);
      setMessage("Project skills saved. Sync the Local Workspace when you are ready.");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Project skills could not be saved");
    } finally { setBusy(false); }
  }

  return (
    <div className="page-stack page-narrow">
      {projectId ? <Link href={`/projects/${projectId}`} className="back-link">← Project Overview</Link> : null}
      <PageHeader eyebrow={projectId ? "Project skills" : "Reusable Agent instructions"} title="Skills" description={projectId ? "Choose the reusable instructions available to this Project." : "Instructions you can reuse across research projects."} />

      {!projectId && (adding || skills.length) ? <button className="button button-primary" type="button" onClick={() => setAdding((value) => !value)}>{adding ? "Cancel" : "Add skill"}</button> : null}

      {adding ? (
        <form className="product-form" onSubmit={add}>
          <label>Name<input value={name} onChange={(event) => setName(event.target.value)} required maxLength={120} /></label>
          <label>What does it help with?<textarea value={description} onChange={(event) => setDescription(event.target.value)} required maxLength={500} rows={3} /></label>
          <label>GitHub URL<input type="url" value={source} onChange={(event) => setSource(event.target.value)} required /></label>
          <details className="technical-details"><summary>Advanced</summary><label>Revision / ref<input value={revision} onChange={(event) => setRevision(event.target.value)} maxLength={128} /></label></details>
          <div className="form-actions"><button className="button button-primary" disabled={busy}>{busy ? "Checking source…" : "Add skill"}</button></div>
        </form>
      ) : null}

      {!skills.length && !adding ? (
        <section className="plain-section"><h2>No skills yet.</h2><p className="muted-copy">Add reusable instructions that you want to use across research projects.</p>{!projectId ? <button className="button button-primary" onClick={() => setAdding(true)}>Add skill</button> : <Link href="/skills" className="button button-primary">Add a skill</Link>}</section>
      ) : (
        <section className="plain-section" aria-label="My Skills">
          <div className="overview-workflow-list">
            {skills.map((skill) => (
              projectId ? (
                <label key={skill.skill_id} className="artifact-choice">
                  <input type="checkbox" checked={attached.has(skill.skill_id)} onChange={(event) => setAttached((current) => { const next = new Set(current); if (event.target.checked) next.add(skill.skill_id); else next.delete(skill.skill_id); return next; })} />
                  <span><strong>{skill.name}</strong><small>{skill.description}</small></span>
                  <span>{attached.has(skill.skill_id) ? skill.local_status ?? "Needs sync" : `Used in ${skill.usage_count} project${skill.usage_count === 1 ? "" : "s"}`}</span>
                </label>
              ) : (
                <div key={skill.skill_id}>
                  <div><strong><Link href={`/skills/${skill.skill_id}`}>{skill.name}</Link></strong><p>{skill.description}</p></div>
                  <span>Used in {skill.usage_count} project{skill.usage_count === 1 ? "" : "s"}</span>
                </div>
              )
            ))}
          </div>
          {projectId ? <div className="form-actions"><button className="button button-primary" onClick={saveProjectSkills} disabled={busy}>{busy ? "Saving…" : "Save"}</button></div> : null}
        </section>
      )}
      {message ? <p className={message.startsWith("Project skills saved") ? "muted-copy" : "form-error"} role="status">{message}</p> : null}
      <details className="technical-details"><summary>Technical details</summary><p>User Skills are unreviewed Agent instructions from exact GitHub revisions. They do not become Experiment Capabilities.</p></details>
    </div>
  );
}
