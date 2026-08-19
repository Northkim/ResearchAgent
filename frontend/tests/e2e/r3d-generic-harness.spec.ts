import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { requireIsolatedQualification } from "./qualification-safety";

type R3DManifest = {
  project_id: string;
  project_name: string;
  workspace: string;
  instances: Record<string, string>;
  idea: { artifact_id: string; checksum: string };
  experiment?: {
    artifact_id: string;
    checksum: string;
    presentation_schema: string;
  };
  interruption_status?: string;
  completion_status?: string;
  writing_materialized_count?: number;
  completed_unit_reused_checksum?: string;
};

test.beforeAll(() => requireIsolatedQualification());

test("qualifies the complete Generic Harness path through exact Writing consumption", async ({ page, request }) => {
  test.setTimeout(300_000);
  const backend = process.env.REAGENT_E2E_BACKEND_URL!;
  const repository = resolve(process.cwd(), "..");
  const temporary = mkdtempSync(join(tmpdir(), "reagent-r3d-"));
  const qualificationRoot = join(temporary, "qualification");
  const manifestPath = join(temporary, "manifest.json");
  const runId = crypto.randomUUID().replaceAll("-", "");
  const screenshotRoot = resolve(repository, ".agent_read/tmp/r3d-generic-harness");
  rmSync(screenshotRoot, { recursive: true, force: true });
  mkdirSync(screenshotRoot, { recursive: true });

  const drive = (phase: "prepare" | "finish") => execFileSync(
    "conda",
    [
      "run", "--no-capture-output", "-n", "reagent-dev", "python", "-m",
      "scripts.r3d_controlled_generic_harness", phase,
      "--api-url", backend,
      "--run-id", runId,
      "--root", qualificationRoot,
      "--manifest", manifestPath,
    ],
    {
      cwd: repository,
      env: process.env,
      encoding: "utf8",
      timeout: 180_000,
      stdio: "pipe",
    },
  );

  const pageErrors: string[] = [];
  const externalRequests: string[] = [];
  const allowedPorts = new Set([
    new URL(process.env.REAGENT_E2E_BASE_URL!).port,
    new URL(backend).port,
  ]);
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
    expect(drive("prepare")).toContain("R3D_PREPARE=PASS");
    const prepared = JSON.parse(readFileSync(manifestPath, "utf8")) as R3DManifest;
    const experimentId = prepared.instances["reproduction-experiment-local-experimental"];

    await page.goto(`/projects/${prepared.project_id}/workflows/${experimentId}`);
    await expect(page.getByRole("heading", { name: "Prepare and run an experiment" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Standardization Effect on KNN Performance/ })).toBeVisible();
    await expect(page.getByText("Source · Selected research idea · exact version recorded")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Exact run summary" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "How would you like to start?" })).toHaveCount(0);
    await expect(page.getByText(/System-owned Generic Agent Harness/).first()).toBeVisible();
    await expect(page.getByText("Network disabled")).toBeVisible();
    await page.screenshot({ path: join(screenshotRoot, "01-exact-run-approval.png"), fullPage: true });

    await page.getByRole("button", { name: "Approve this run" }).click();
    await expect(page.getByRole("heading", { name: "Run approved" })).toBeVisible();
    await page.screenshot({ path: join(screenshotRoot, "02-run-approved.png"), fullPage: true });

    expect(drive("finish")).toContain("R3D_FINISH=PASS");
    const completed = JSON.parse(readFileSync(manifestPath, "utf8")) as R3DManifest;
    expect(completed.interruption_status).toBe("EXECUTION_INTERRUPTED");
    expect(completed.completion_status).toBe("PROGRESS_SYNCHRONIZED");
    expect(completed.writing_materialized_count).toBe(3);
    expect(completed.completed_unit_reused_checksum).toMatch(/^sha256:[0-9a-f]{64}$/);
    expect(completed.experiment).toMatchObject({
      presentation_schema: "reagent.artifact-presentation.experiment-record/v0.2",
    });

    const artifactResponse = await request.get(
      `${backend}/projects/${prepared.project_id}/artifacts?workflow_instance_id=${experimentId}`,
    );
    expect(artifactResponse.ok()).toBe(true);
    const artifactPage = await artifactResponse.json() as {
      artifacts: Array<Record<string, unknown>>;
    };
    expect(artifactPage.artifacts).toHaveLength(1);
    expect(artifactPage.artifacts[0]).toMatchObject({
      artifact_id: completed.experiment!.artifact_id,
      artifact_type: "experiment-record/v5",
      content_checksum: completed.experiment!.checksum,
    });

    await page.reload();
    await expect(page.getByRole("heading", { name: "Experiment completed" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Experiment result" })).toBeVisible();
    await expect(page.getByText("SUPPORTS BOUNDED FINDINGS", { exact: false }).first()).toBeVisible();
    await expect(page.getByText(/cannot establish a real Wine-dataset claim/i)).toBeVisible();
    await page.screenshot({ path: join(screenshotRoot, "03-completed-generic-experiment.png"), fullPage: true });

    await page.goto(`/projects/${prepared.project_id}/outputs`);
    await expect(page.getByRole("heading", { name: "Experiment result" }).first()).toBeVisible();
    await expect(page.getByText(completed.experiment!.artifact_id)).not.toBeVisible();
    await page.screenshot({ path: join(screenshotRoot, "04-v5-output.png"), fullPage: true });

    expect(pageErrors).toEqual([]);
    expect(externalRequests).toEqual([]);
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});
