import { execFileSync } from "node:child_process";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { requireIsolatedQualification } from "./qualification-safety";

type JsonObject = Record<string, unknown>;
type Fixture = {
  project_id: string;
  instances: { literature: string[]; consolidation: string; idea: string };
  artifacts: Array<{
    artifact_id: string;
    artifact_checksum: string;
    producer_workflow_instance_id: string;
    relative_path: string;
    content: string;
  }>;
};

const backendUrl = process.env.REAGENT_E2E_BACKEND_URL!;
const frontendUrl = process.env.REAGENT_E2E_BASE_URL!;
const repoRoot = resolve(process.cwd(), "..");

test.beforeAll(() => requireIsolatedQualification());

function commandJson(command: string, args: string[], env: NodeJS.ProcessEnv = process.env) {
  const output = execFileSync(command, args, { env, encoding: "utf8" });
  const line = output.replaceAll("\r", "").trim().split("\n").reverse().find((item) => item.startsWith("{"));
  if (!line) throw new Error(`command did not return JSON: ${output}`);
  return JSON.parse(line) as JsonObject;
}

function workspaceCommand(workspace: string, args: string[], env: NodeJS.ProcessEnv = process.env) {
  return commandJson("python3", [join(workspace, "reagent_local.py"), ...args, "--json"], env);
}

function installedCapsules(workspace: string) {
  const lock = JSON.parse(readFileSync(join(workspace, ".reagent/installed-lock.json"), "utf8")) as {
    installed_capsules: Array<Record<string, string>>;
  };
  return lock.installed_capsules;
}

test("qualifies explicit exact Literature composition through browser and Local Workspace", async ({ page, request }) => {
  const temporary = mkdtempSync(join(tmpdir(), "reagent-r4-e2e-"));
  const workspace = join(temporary, "workspace");
  const manifestPath = join(temporary, "fixture.json");
  const screenshotRoot = resolve(repoRoot, ".agent_read/tmp/post-d1-r4-literature");
  const runId = crypto.randomUUID().replaceAll("-", "");
  const pageErrors: string[] = [];
  const externalRequests: string[] = [];
  const allowedPorts = new Set([new URL(frontendUrl).port, new URL(backendUrl).port]);
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (event) => {
    const url = new URL(event.url());
    if (!["data:", "blob:", "about:"].includes(url.protocol)) {
      const allowed = ["http:", "https:", "ws:", "wss:"].includes(url.protocol)
        && ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)
        && allowedPorts.has(url.port);
      if (!allowed) externalRequests.push(event.url());
    }
  });

  try {
    rmSync(screenshotRoot, { recursive: true, force: true });
    mkdirSync(screenshotRoot, { recursive: true });
    const created = await request.post(`${backendUrl}/projects`, { data: {
      name: "R4 explicit Literature composition",
      research_topic: "Controlled exact composition of iterative Literature evidence",
      selected_workflow: "LITERATURE_SEARCH",
      workflow_setup: "literature-only",
    } });
    expect(created.ok()).toBe(true);
    const project = await created.json() as { project_id: string };

    await page.goto(`/projects/${project.project_id}/workflows`);
    const catalog = page.locator("section").filter({
      has: page.getByRole("heading", { name: "Add another research workflow" }),
    });
    const literatureCard = catalog.locator("article").filter({ hasText: "Literature Search" });
    await expect(literatureCard).toContainText("Version 0.6.0");
    await literatureCard.getByRole("button", { name: "Add workflow" }).click();
    await expect(page.getByText("Literature Search was added to this Project.")).toBeVisible();
    const consolidationCard = catalog.locator("article").filter({ hasText: "Literature Consolidation" });
    await expect(consolidationCard).toContainText("Version 0.1.0");
    await consolidationCard.getByRole("button", { name: "Add workflow" }).click();
    await expect(page.getByText("Literature Consolidation was added to this Project.")).toBeVisible();
    const ideaCard = catalog.locator("article").filter({ hasText: "Idea Discovery" });
    await ideaCard.getByRole("button", { name: "Add workflow" }).click();
    await expect(page.getByText("Idea Discovery was added to this Project.")).toBeVisible();

    execFileSync("conda", [
      "run", "--no-capture-output", "-n", "reagent-dev", "python", "-m",
      "scripts.r4_controlled_fixtures",
      "--api-url", backendUrl,
      "--project-id", project.project_id,
      "--run-id", runId,
      "--manifest", manifestPath,
    ], { cwd: repoRoot, env: process.env, stdio: "pipe" });
    const fixture = JSON.parse(readFileSync(manifestPath, "utf8")) as Fixture;

    const descriptorResponse = await request.get(`${backendUrl}/projects/${project.project_id}/workspace-bootstrap`);
    expect(descriptorResponse.ok()).toBe(true);
    const descriptorPath = join(temporary, "workspace-bootstrap.json");
    writeFileSync(descriptorPath, JSON.stringify(await descriptorResponse.json()));
    expect(commandJson("python3", [
      resolve(repoRoot, "reagent_local.py"), "bootstrap", workspace,
      "--descriptor", descriptorPath, "--json",
    ]).status).toBe("CREATED");
    expect(workspaceCommand(workspace, ["sync", workspace, "--api-url", backendUrl]).status).toBe("SYNCED");

    await page.goto(`/projects/${project.project_id}/workflows/${fixture.instances.consolidation}`);
    await expect(page.getByRole("heading", { name: "Literature Consolidation" })).toBeVisible();
    const inputs = page.getByRole("region", { name: "Inputs", exact: true });
    const base = inputs.getByRole("group", { name: "base library · required" });
    const additional = inputs.getByRole("group", { name: "additional library · required" });
    await expect(base.getByRole("radio")).toHaveCount(2);
    await expect(additional.getByRole("radio")).toHaveCount(2);
    await expect(base.locator('input[type="radio"]:checked')).toHaveCount(0);
    await expect(additional.locator('input[type="radio"]:checked')).toHaveCount(0);
    await expect(base.getByText("Base evidence paper")).toBeVisible();
    await expect(additional.getByText("Additional context paper")).toBeVisible();
    await page.screenshot({ path: join(screenshotRoot, "exact-candidate-choices.png"), fullPage: true });
    await base.locator(`[data-artifact-id="${fixture.artifacts[0].artifact_id}"] input`).check();
    await base.getByRole("button", { name: "Confirm exact input" }).click();
    await additional.locator(`[data-artifact-id="${fixture.artifacts[1].artifact_id}"] input`).check();
    await additional.getByRole("button", { name: "Confirm exact input" }).click();
    await expect(inputs.getByText("Prepare verified local copies of the selected research inputs:")).toBeVisible();
    await page.screenshot({ path: join(screenshotRoot, "exact-two-source-confirmed.png"), fullPage: true });

    const installed = installedCapsules(workspace);
    for (const artifact of fixture.artifacts) {
      const producer = installed.find((item) => item.workflow_instance_id === artifact.producer_workflow_instance_id);
      if (!producer) throw new Error("controlled producer Capsule was not installed");
      const target = join(workspace, producer.relative_path, artifact.relative_path);
      mkdirSync(resolve(target, ".."), { recursive: true });
      writeFileSync(target, artifact.content);
    }
    expect(workspaceCommand(workspace, [
      "artifact", "materialize", workspace,
      "--workflow-instance", fixture.instances.consolidation,
      "--api-url", backendUrl,
    ]).status).toBe("MATERIALIZED");

    const fakeCodex = join(temporary, "codex-r4-fixture");
    writeFileSync(fakeCodex, `#!/usr/bin/env python3
import hashlib, json
from pathlib import Path
root = Path.cwd()
candidates_path = root / "outputs/candidate_papers.json"
candidates = json.loads(candidates_path.read_text())["candidates"]
selected = [{"candidate_id": item["candidate_id"], "relevance_decision": "INCLUDE", "inclusion_reason": "Owner kept the controlled exact source.", "evidence_availability": "METADATA_AND_ABSTRACT"} for item in candidates]
(root / "outputs/selected_papers.json").write_text(json.dumps({"schema_version": "selected-papers/v0.2", "mode": "NORMAL", "selection_status": "SUFFICIENT", "selected": selected, "exclusions": [], "exclusion_summary": {}}, sort_keys=True, separators=(",", ":")) + "\\n")
checksum = "sha256:" + hashlib.sha256(candidates_path.read_bytes()).hexdigest()
(root / "memory/owner-decisions.json").write_text(json.dumps({"schema_version": "reagent.owner-decision-snapshot.literature/v0.1", "candidate_set_checksum": checksum, "decisions": [{"candidate_id": item["candidate_id"], "disposition": "SELECTED"} for item in candidates]}, sort_keys=True, separators=(",", ":")) + "\\n")
(root / "outputs/literature_search_report.md").write_text("# Consolidated Literature\\n\\nThree exact deduplicated records.\\n")
`);
    chmodSync(fakeCodex, 0o700);
    const run = workspaceCommand(workspace, [
      "run", workspace,
      "--workflow-instance", fixture.instances.consolidation,
      "--api-url", backendUrl,
      "--codex-executable", fakeCodex,
    ], { ...process.env, REAGENT_CODEX_EXECUTABLE: fakeCodex });
    expect(run.status).toBe("RUN_COMPLETED");

    const references = await request.get(`${backendUrl}/projects/${project.project_id}/artifacts`);
    expect(references.ok()).toBe(true);
    const artifactPage = await references.json() as { artifacts: Array<Record<string, string>> };
    const composite = artifactPage.artifacts.find(
      (item) => item.producer_workflow_instance_id === fixture.instances.consolidation,
    );
    expect(composite?.artifact_type).toBe("selected-paper-library/v1");

    await page.goto(`/projects/${project.project_id}/workflows/${fixture.instances.idea}`);
    const ideaInputs = page.getByRole("region", { name: "Inputs", exact: true });
    const ideaLibrary = ideaInputs.getByRole("group", { name: "paper library · required" });
    await expect(ideaLibrary.getByRole("radio")).toHaveCount(3);
    await ideaLibrary.locator(`[data-artifact-id="${composite!.artifact_id}"] input`).check();
    await ideaLibrary.getByRole("button", { name: "Confirm exact input" }).click();
    const dependencies = await request.get(
      `${backendUrl}/projects/${project.project_id}/workflow-instances/${fixture.instances.idea}/artifact-dependencies`,
    );
    const dependencyPage = await dependencies.json() as { dependencies: Array<Record<string, string>> };
    expect(dependencyPage.dependencies).toEqual(expect.arrayContaining([
      expect.objectContaining({ requirement_key: "paper_library", artifact_id: composite!.artifact_id, state: "ACTIVE" }),
    ]));
    await page.screenshot({ path: join(screenshotRoot, "composite-selected-downstream.png"), fullPage: true });
    expect(pageErrors).toEqual([]);
    expect(externalRequests).toEqual([]);
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});
