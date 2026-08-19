import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { requireIsolatedQualification } from "./qualification-safety";

type FixtureManifest = {
  project_id: string;
  project_name: string;
  instances: Record<string, string>;
};

type DesiredManifest = {
  workspace_id: string;
  manifest_revision: number;
  canonical_checksum: string;
  manifest: {
    workflow_instances: Array<Record<string, string>>;
  };
};

type EpD2ProjectFixture = {
  project_id: string;
  project_name: string;
  instances: Record<string, string>;
};

type EpD2FixtureManifest = {
  eligible: EpD2ProjectFixture;
  completed: EpD2ProjectFixture;
};

const checksumA = `sha256:${"a".repeat(64)}`;
const checksumB = `sha256:${"b".repeat(64)}`;

const viewports = [
  { width: 1440, height: 900 },
  { width: 1280, height: 800 },
] as const;

test.beforeAll(() => requireIsolatedQualification());

test("qualifies the FE-M task-first canonical journey", async ({ page, request }) => {
  const backend = process.env.REAGENT_E2E_BACKEND_URL!;
  const frontend = process.env.REAGENT_E2E_BASE_URL!;
  const repository = resolve(process.cwd(), "..");
  const temporary = mkdtempSync(join(tmpdir(), "reagent-fe-m-"));
  const manifestPath = join(temporary, "fixture.json");
  const screenshotRoot = resolve(repository, ".agent_read/tmp/fe-m-desktop-final-review");
  rmSync(screenshotRoot, { recursive: true, force: true });
  mkdirSync(screenshotRoot, { recursive: true });

  const supportingAttention = await request.post(`${backend}/projects`, {
    data: {
      name: "ResearchAgent architecture study",
      research_topic: "Evaluating a local-first scientific workflow system",
      selected_workflow: "LITERATURE_SEARCH",
      workflow_setup: "literature-only",
    },
  });
  expect(supportingAttention.ok()).toBe(true);
  const supportingReady = await request.post(`${backend}/projects`, {
    data: {
      name: "Maritime video monitoring",
      research_topic: "Latency-aware visual-language analysis for live streams",
      selected_workflow: "LITERATURE_SEARCH",
      workflow_setup: "literature-only",
    },
  });
  expect(supportingReady.ok()).toBe(true);
  const supportingReadyProject = await supportingReady.json() as { project_id: string };

  try {
    execFileSync("conda", [
      "run", "--no-capture-output", "-n", "reagent-dev", "python", "-m",
      "scripts.b0_controlled_fixtures",
      "--api-url", backend,
      "--run-id", crypto.randomUUID().replaceAll("-", ""),
      "--manifest", manifestPath,
      "--project-name", "Urban drainage control study",
      "--research-topic", "Stress-testing multi-agent control under unseen storms",
      "--scenario", "fe-m-desktop",
    ], { cwd: repository, env: process.env, stdio: "pipe" });
    const fixture = JSON.parse(readFileSync(manifestPath, "utf8")) as FixtureManifest;
    const response = await request.get(`${backend}/projects/${fixture.project_id}/progress`);
    expect(response.ok()).toBe(true);
    const progress = await response.json() as { instances: Array<Record<string, unknown>> };
    const state = (workflow: string) => progress.instances.find(
      (item) => item.workflow_instance_id === fixture.instances[workflow],
    )!;
    expect(state("literature-search-local-experimental")).toMatchObject({
      research_status: "COMPLETED",
      installation_state: "ACKNOWLEDGED_STALE",
      action: { attention_state: "ATTENTION_REQUIRED", latest_output: { state: "PRODUCED" } },
    });
    expect(state("idea-discovery-local-experimental")).toMatchObject({
      research_status: "COMPLETED",
      action: { attention_state: "ATTENTION_REQUIRED", latest_output: { state: "PRODUCED" } },
    });
    expect(state("writing-local-experimental")).toMatchObject({
      research_status: "BLOCKED", action: { attention_state: "ATTENTION_REQUIRED" },
    });
    expect(state("review-local-experimental")).toMatchObject({ installation_state: "ACKNOWLEDGED_STALE" });

    const acknowledgeCurrent = async (projectId: string) => {
      const desiredResponse = await request.get(`${backend}/projects/${projectId}/manifest`);
      expect(desiredResponse.ok()).toBe(true);
      const desired = await desiredResponse.json() as DesiredManifest;
      const pinKeys = [
        "workflow_instance_id", "workflow_definition_id", "workflow_definition_version",
        "capsule_id", "capsule_version", "capsule_definition_checksum",
      ];
      const acknowledgement = await request.post(
        `${backend}/projects/${projectId}/workspace/sync-ack`,
        { data: {
          schema_version: "reagent.capsule-installation-ack/v0.1",
          installation_id: `install-${crypto.randomUUID().replaceAll("-", "")}`,
          project_id: projectId,
          workspace_id: desired.workspace_id,
          manifest_revision: desired.manifest_revision,
          manifest_checksum: desired.canonical_checksum,
          plan_checksum: checksumA,
          installed_lock_schema: "reagent.workspace-installed-lock/v0.1",
          installed_lock_checksum: checksumB,
          idempotency_key: crypto.randomUUID(),
          installed_capsules: desired.manifest.workflow_instances
            .filter((item) => item.desired_state === "ACTIVE")
            .map((item) => Object.fromEntries(pinKeys.map((key) => [key, item[key]]))),
          installed_at: new Date().toISOString(),
        } },
      );
      expect(acknowledgement.ok()).toBe(true);
    };

    // The fixture deliberately creates an acknowledged-stale installation. Exercise that
    // state first, then restore the supported public sync acknowledgement so the same
    // controlled journey can also review the underlying blocked and Owner-action states.
    await acknowledgeCurrent(fixture.project_id);
    await acknowledgeCurrent(supportingReadyProject.project_id);
    const synchronizedResponse = await request.get(`${backend}/projects/${fixture.project_id}/progress`);
    expect(synchronizedResponse.ok()).toBe(true);
    const synchronized = await synchronizedResponse.json() as { instances: Array<Record<string, unknown>> };
    const synchronizedState = (workflow: string) => synchronized.instances.find(
      (item) => item.workflow_instance_id === fixture.instances[workflow],
    )!;
    expect(synchronizedState("literature-search-local-experimental")).toMatchObject({
      research_status: "COMPLETED", action: { attention_state: "COMPLETED" },
    });
    expect(synchronizedState("idea-discovery-local-experimental")).toMatchObject({
      research_status: "COMPLETED", action: { attention_state: "COMPLETED" },
    });
    expect(synchronizedState("writing-local-experimental")).toMatchObject({
      research_status: "BLOCKED", action: { attention_state: "OWNER_ACTION_REQUIRED", actor: "OWNER" },
    });

    const pageErrors: string[] = [];
    const externalRequests: string[] = [];
    const browserWorkspaceWrites: string[] = [];
    const allowedPorts = new Set([new URL(frontend).port, new URL(backend).port]);
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("request", (event) => {
      const url = new URL(event.url());
      if (!["data:", "blob:", "about:"].includes(url.protocol)) {
        const allowed = ["http:", "https:", "ws:", "wss:"].includes(url.protocol)
          && ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)
          && allowedPorts.has(url.port);
        if (!allowed) externalRequests.push(event.url());
      }
      if (!["GET", "HEAD", "OPTIONS"].includes(event.method()) && /\/workspace(?:\/|$)/.test(url.pathname)) {
        browserWorkspaceWrites.push(`${event.method()} ${url.pathname}`);
      }
    });

    const assertSafeViewport = async () => {
      await expect(page.locator('[role="alert"]:not(#__next-route-announcer__)')).toHaveCount(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      expect(pageErrors).toEqual([]);
      expect(externalRequests).toEqual([]);
      expect(browserWorkspaceWrites).toEqual([]);
    };

    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.goto("/projects");
      const projectRow = page.locator("article.project-work-row").filter({ hasText: fixture.project_name });
      await expect(projectRow).toBeVisible();
      await expect(page.getByRole("heading", { name: "Needs your attention" })).toBeVisible();
      await expect(projectRow.getByText("Review the writing outline", { exact: true })).toBeVisible();
      await expect(projectRow.getByText("Needs your review", { exact: true })).toBeVisible();
      await expect(projectRow.getByText("The evidence map and outline are ready.", { exact: true })).toBeVisible();
      await expect(projectRow.getByRole("link", { name: /Review outline/ })).toBeVisible();
      await expect(projectRow.getByText(/UTC/)).toHaveCount(0);
      await expect(page.getByText("Maritime video monitoring")).toBeVisible();
      await expect(page.getByText(/Owner acts now|Continue at owner checkpoint|Cloud has not received acknowledgement|B0 controlled|F1F browser/i)).toHaveCount(0);
      await assertSafeViewport();
      if (viewport.width === 1440) await page.screenshot({ path: join(screenshotRoot, "projects__1440x900.png"), fullPage: false });

      await projectRow.getByRole("link", { name: fixture.project_name }).click();
      await expect(page.getByRole("heading", { name: fixture.project_name })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Review the writing outline" })).toBeVisible();
      await expect(page.getByText("The evidence map and six-section outline are ready.", { exact: true })).toBeVisible();
      await expect(page.getByRole("link", { name: "Review outline" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Workflow progress" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Latest output" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Recent activity" })).toBeVisible();
      const workflowProgress = page.locator(".overview-workflow-list");
      await expect(workflowProgress.locator("div").filter({ hasText: "Literature Search" }).first().getByText("Completed", { exact: true })).toBeVisible();
      await expect(workflowProgress.locator("div").filter({ hasText: "Idea Discovery" }).first().getByText("Completed", { exact: true })).toBeVisible();
      await expect(workflowProgress.locator("div").filter({ hasText: "Initial Writing" }).first().getByText("Needs your review", { exact: true })).toBeVisible();
      await expect(workflowProgress.getByText("Blocked", { exact: true })).toHaveCount(0);
      await expect(page.locator("#outputs").getByText("Selected research idea", { exact: true })).toBeVisible();
      await expect(page.getByText(/UTC/)).toHaveCount(0);
      await expect(page.locator("h1")).not.toContainText(fixture.project_id);
      await expect(page.getByText(/Owner acts now|Continue at owner checkpoint|Current research state/i)).toHaveCount(0);
      await assertSafeViewport();
      if (viewport.width === 1440) await page.screenshot({ path: join(screenshotRoot, "overview__1440x900.png"), fullPage: false });

      await page.goto(`/projects/${fixture.project_id}/workflows/${fixture.instances["writing-local-experimental"]}`);
      await expect(page.getByText("Initial Writing", { exact: true }).first()).toBeVisible();
      await expect(page.getByRole("heading", { name: "Prepare an evidence-bound manuscript" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Review the outline locally" })).toBeVisible();
      await expect(page.getByRole("link", { name: "Continue locally" })).toBeVisible();
      const inputs = page.locator("#inputs");
      const inputRows = inputs.locator(".input-readiness-list > div");
      await expect(inputRows.filter({ hasText: "Selected literature" }).getByText("Selected", { exact: true })).toBeVisible();
      await expect(inputRows.filter({ hasText: "Selected research idea" }).getByText("Selected", { exact: true })).toBeVisible();
      await expect(inputs.getByText("Missing", { exact: true })).toHaveCount(0);
      await expect(page.getByRole("heading", { name: "Continue in the Local Workspace" })).toBeVisible();
      await expect(page.locator("details.technical-details")).not.toHaveAttribute("open");
      await expect(page.getByText(/Owner acts now|Continue at owner checkpoint|Run the exact public command locally|placeholder research core|Artifact flow/i)).toHaveCount(0);
      await assertSafeViewport();
      if (viewport.width === 1440) await page.screenshot({ path: join(screenshotRoot, "workflow__1440x900.png"), fullPage: false });
    }

    await page.goto(`/projects/${fixture.project_id}/workflows`);
    const workflowRows = page.locator("article.workflow-work-row");
    await expect(workflowRows).toHaveCount(4);
    await expect(workflowRows.filter({ hasText: "Idea Discovery" }).getByText("Blocked", { exact: true })).toHaveCount(0);
    await page.goto(`/projects/${fixture.project_id}/outputs`);
    await expect(page.getByRole("heading", { name: "Selected paper library" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Selected research idea" })).toBeVisible();
    await expect(page.locator("details").filter({ hasText: "Technical Details" }).first()).not.toHaveAttribute("open");
    await page.goto(`/projects/${fixture.project_id}/progress`);
    await expect(page.getByRole("heading", { name: `${fixture.project_name} Activity` })).toBeVisible();
    await assertSafeViewport();
    expect(readFileSync(join(screenshotRoot, "projects__1440x900.png"))).not.toHaveLength(0);
    expect(readFileSync(join(screenshotRoot, "overview__1440x900.png"))).not.toHaveLength(0);
    expect(readFileSync(join(screenshotRoot, "workflow__1440x900.png"))).not.toHaveLength(0);
    expect(readdirSync(screenshotRoot).sort()).toEqual([
      "overview__1440x900.png", "projects__1440x900.png", "workflow__1440x900.png",
    ]);

    // Preserve the isolated-runner cleanup markers after Owner screenshots are complete.
    for (const [name, researchTopic] of [
      ["F1F browser product width", "Controlled FE-M isolation marker"],
      ["H1 controlled product journey", "Controlled E2E isolation marker"],
    ]) {
      const marker = await request.post(`${backend}/projects`, { data: {
        name, research_topic: researchTopic, selected_workflow: "LITERATURE_SEARCH",
        workflow_setup: "literature-only",
      } });
      expect(marker.ok()).toBe(true);
    }
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});

test("EP-D2-U1 qualifies bounded upstream Outputs and exact-selection previews", async ({ page }) => {
  const backend = process.env.REAGENT_E2E_BACKEND_URL!;
  const identity = process.env.REAGENT_E2E_QUALIFICATION_IDENTITY!;
  const runtime = process.env.REAGENT_LOCAL_RUNTIME_DIR!;
  const repository = resolve(process.cwd(), "..");
  const manifestPath = join(runtime, "ep-d2-u1-fixtures.json");
  execFileSync("conda", [
    "run", "--no-capture-output", "-n", "reagent-dev", "python", "-m",
    "scripts.b0_controlled_fixtures", "--api-url", backend, "--run-id", identity,
    "--manifest", manifestPath, "--scenario", "ep-d2-u1",
    "--project-name", "EP-D2-U1 controlled upstream presentation",
  ], { cwd: repository, env: process.env, stdio: "inherit" });
  const fixture = JSON.parse(readFileSync(manifestPath, "utf8")) as FixtureManifest;
  const screenshotRoot = resolve(process.cwd(), "test-results", "ep-d2-u1-e6", "screenshots");
  mkdirSync(screenshotRoot, { recursive: true, mode: 0o700 });
  const shot = (name: string) => page.screenshot({ path: join(screenshotRoot, `${name}.png`), fullPage: true });

  await page.goto(`/projects/${fixture.project_id}/outputs`);
  await expect(page.getByRole("heading", { name: "Selected paper library" }).first()).toBeVisible();
  await expect(page.getByText("Bounded archival classification study")).toBeVisible();
  await expect(page.getByText("10.1000/controlled.1")).toBeVisible();
  await expect(page.getByText("Contrasting categorical field record")).toBeVisible();
  await expect(page.getByText("controlled-record-2")).toBeVisible();
  await expect(page.getByText("Abstract only; full text is not represented.")).toBeVisible();
  await expect(page.getByText("Metadata only; no abstract or full text is represented.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Compare archival classification practices" })).toBeVisible();
  await expect(page.getByText("Where do the reported categories diverge?")).toBeVisible();
  await expect(page.getByText("Apply a bounded comparative observation protocol.")).toBeVisible();
  await expect(page.getByText("The evidence is limited to metadata and abstracts.")).toBeVisible();
  await expect(page.getByText("Local result preview has not yet been reported.")).toBeVisible();
  await expect(page.getByText("python reagent_local.py artifact refresh .")).toBeVisible();
  await expect(page.locator("details").filter({ hasText: "Technical Details" }).first()).not.toHaveAttribute("open");
  expect(await page.locator("body").innerText()).not.toMatch(/Artifact checksum|Capsule checksum|requirement key/i);
  await shot("01-upstream-outputs-typed-previews");

  const ideaDetail = `/projects/${fixture.project_id}/workflows/${fixture.instances["idea-discovery-local-experimental"]}`;
  await page.goto(ideaDetail);
  const ideaBindings = page.getByText("Manage input bindings").locator("..");
  await ideaBindings.locator("summary").click();
  await expect(ideaBindings.getByText("Bounded archival classification study")).toBeVisible();
  await expect(ideaBindings.getByText("Contrasting categorical field record")).toBeVisible();
  await expect(ideaBindings.getByText("Preview not yet reported from Local Workspace.")).toBeVisible();
  const candidateRadios = ideaBindings.getByRole("radio");
  await expect(candidateRadios).toHaveCount(3);
  await expect(ideaBindings.locator('input[type="radio"]:checked')).toHaveCount(1);
  await expect(
    ideaBindings.locator("label").filter({ hasText: "Bounded archival classification study" }).getByRole("radio"),
  ).toBeChecked();
  await shot("02-literature-exact-selection-multiple-candidates");

  const writingDetail = `/projects/${fixture.project_id}/workflows/${fixture.instances["writing-local-experimental"]}`;
  await page.goto(writingDetail);
  const writingBindings = page.getByLabel("Exact workflow input setup");
  await expect(writingBindings).toBeVisible();
  await expect(writingBindings.getByText("Bounded archival classification study")).toBeVisible();
  await expect(writingBindings.getByRole("heading", { name: "Compare archival classification practices" })).toBeVisible();
  const literatureChoices = writingBindings.locator("fieldset").filter({ hasText: "literature library" });
  const literatureRadios = literatureChoices.getByRole("radio");
  await expect(literatureRadios).toHaveCount(3);
  for (let index = 0; index < 3; index += 1) await expect(literatureRadios.nth(index)).not.toBeChecked();
  await shot("03-writing-literature-idea-selection-previews");

});

test("EP-D2 qualifies the forward Full Research Owner journey", async ({ page, request }) => {
  const backend = process.env.REAGENT_E2E_BACKEND_URL!;
  const identity = process.env.REAGENT_E2E_QUALIFICATION_IDENTITY!;
  const runtime = process.env.REAGENT_LOCAL_RUNTIME_DIR!;
  const repository = resolve(process.cwd(), "..");
  const manifestPath = join(runtime, "ep-d2-fixtures.json");
  execFileSync("conda", [
    "run", "--no-capture-output", "-n", "reagent-dev", "python", "-m",
    "scripts.b0_controlled_fixtures", "--api-url", backend, "--run-id", identity,
    "--manifest", manifestPath, "--scenario", "ep-d2",
  ], { cwd: repository, env: process.env, stdio: "inherit" });
  const fixture = JSON.parse(readFileSync(manifestPath, "utf8")) as EpD2FixtureManifest;
  const screenshotRoot = resolve(process.cwd(), "test-results", "ep-d2-e6", "screenshots");
  mkdirSync(screenshotRoot, { recursive: true, mode: 0o700 });
  const shot = (name: string) => page.screenshot({ path: join(screenshotRoot, `${name}.png`), fullPage: true });

  await page.goto(`/projects/${fixture.eligible.project_id}/workflows`);
  const initialRows = page.locator("article.workflow-work-row");
  await expect(initialRows).toHaveCount(5);
  for (const role of ["Literature Search", "Idea Discovery", "Reproduction & Experiment", "Initial Writing", "Review"]) {
    await expect(initialRows.getByRole("heading", { name: role, exact: true })).toBeVisible();
  }
  await expect(initialRows.getByRole("heading", { name: "Writing Revision", exact: true })).toHaveCount(0);
  await shot("01-full-research-five-forward-workflows");

  await page.goto(`/projects/${fixture.completed.project_id}/workflows/${fixture.completed.instances.writing}`);
  await expect(page.getByRole("heading", { name: "Manuscript completed" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Bounded archival comparison manuscript" })).toBeVisible();
  await expect(page.getByText("The complete manuscript remains in the Local Workspace.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Continue in the Local Workspace" })).toHaveCount(0);
  await shot("02-initial-writing-completed-task-first");

  await page.goto(`/projects/${fixture.eligible.project_id}/workflows/${fixture.eligible.instances.review}`);
  await expect(page.getByRole("heading", { name: "Review completed" })).toBeVisible();
  const reviewIssue = page.getByText("The abstract-only evidence boundary is implicit.");
  const revisionButton = page.getByRole("button", { name: "Start manuscript revision" });
  await expect(reviewIssue).toBeVisible();
  await expect(revisionButton).toBeVisible();
  expect(await reviewIssue.evaluate((node, action) => Boolean(node.compareDocumentPosition(action as Node) & Node.DOCUMENT_POSITION_FOLLOWING), await revisionButton.elementHandle())).toBe(true);
  await shot("03-review-evidence-before-revision-action");
  await revisionButton.click();
  await page.waitForURL(new RegExp(`/projects/${fixture.eligible.project_id}/workflows/wfi-`));
  await expect(page.getByText("Writing Revision", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Revision source" })).toBeVisible();
  const revisedInstances = await request.get(`${backend}/projects/${fixture.eligible.project_id}/workflow-instances`);
  expect(revisedInstances.ok()).toBe(true);
  const afterAction = await revisedInstances.json() as { items: Array<{ workflow_definition_id: string; workflow_version: string }> };
  expect(afterAction.items.filter((item) => item.workflow_definition_id === "writing-local-experimental" && item.workflow_version === "0.6.0")).toHaveLength(1);
  await shot("04-writing-revision-created-task-first");

  await page.goto(`/projects/${fixture.eligible.project_id}/workflows`);
  const postRevisionRows = page.locator("article.workflow-work-row");
  await expect(postRevisionRows).toHaveCount(6);
  await expect(postRevisionRows.getByRole("heading", { name: "Initial Writing", exact: true })).toHaveCount(1);
  await expect(postRevisionRows.getByRole("heading", { name: "Writing Revision", exact: true })).toHaveCount(1);
  await shot("05-post-revision-role-aware-board");

  await page.goto(`/projects/${fixture.completed.project_id}/workflows/${fixture.completed.instances.revision}`);
  await expect(page.getByRole("heading", { name: "Revision completed" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Revised bounded archival comparison manuscript" })).toBeVisible();
  await expect(page.getByText("issue-limitation-1: addressed")).toBeVisible();
  await expect(page.getByText("0 unresolved Review issues.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Continue in the Local Workspace" })).toHaveCount(0);
  await shot("06-revision-completed-with-disposition");

  await page.goto(`/projects/${fixture.completed.project_id}/outputs`);
  await expect(page.getByRole("heading", { name: "Initial manuscript", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Review report", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Revised manuscript", exact: true })).toBeVisible();
  await expect(page.getByText("Full-text evidence remains unavailable.").first()).toBeVisible();
  await expect(page.locator("details").filter({ hasText: "Technical Details" }).first()).not.toHaveAttribute("open");
  await shot("07-downstream-typed-outputs");

  await page.goto(`/projects/${fixture.eligible.project_id}/outputs`);
  await expect(page.getByText("Local preview has not yet been reported.")).toBeVisible();
  await expect(page.getByText("The complete research product remains in the Local Workspace.")).toBeVisible();
  await shot("08-downstream-presentation-absent");

  await page.goto(`/projects/${fixture.completed.project_id}`);
  await expect(page.getByRole("heading", { name: "Recent activity" })).toBeVisible();
  const recentActivity = page.getByRole("region", { name: "Recent activity" });
  await expect(recentActivity.getByText("Writing Revision", { exact: true })).toBeVisible();
  await expect(recentActivity.getByText("Review", { exact: true })).toBeVisible();
  const overviewWorkflows = page.locator(".overview-workflow-list");
  await expect(overviewWorkflows.getByText("Initial Writing", { exact: true })).toBeVisible();
  await expect(overviewWorkflows.getByText("Writing Revision", { exact: true })).toBeVisible();
  await shot("09-overview-role-aware-writing-labels");
  await page.goto(`/projects/${fixture.completed.project_id}/progress`);
  await expect(page.getByRole("heading", { name: `${fixture.completed.project_name} Activity` })).toBeVisible();
  const activity = page.locator(".project-progress-history");
  await expect(activity.getByRole("heading", { name: "Initial Writing", exact: true })).toBeVisible();
  await expect(activity.getByRole("heading", { name: "Writing Revision", exact: true })).toBeVisible();
  await shot("10-forward-activity-and-role-labels");
});
