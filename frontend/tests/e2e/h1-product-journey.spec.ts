import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  chmodSync,
  copyFileSync,
  existsSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { expect, test } from "@playwright/test";

type JsonObject = Record<string, unknown>;

const backendUrl = process.env.REAGENT_E2E_BACKEND_URL ?? "http://127.0.0.1:8000";
const repoRoot = resolve(process.cwd(), "..");

function commandJson(command: string, args: string[], options: { cwd?: string; env?: NodeJS.ProcessEnv } = {}) {
  const output = execFileSync(command, args, {
    cwd: options.cwd,
    env: options.env ?? process.env,
    encoding: "utf8",
  });
  const line = output.replaceAll("\r", "").trim().split("\n").reverse().find((item) => item.startsWith("{"));
  if (!line) throw new Error(`command did not return JSON: ${output}`);
  return JSON.parse(line) as JsonObject;
}

function workspaceCommand(workspace: string, args: string[]) {
  return commandJson("python3", [join(workspace, "reagent_local.py"), ...args, "--json"]);
}

function installedCapsule(workspace: string, definitionId: string) {
  const lock = JSON.parse(
    readFileSync(join(workspace, ".reagent/installed-lock.json"), "utf8"),
  ) as { installed_capsules: Array<Record<string, string>> };
  const match = lock.installed_capsules.find(
    (item) => item.workflow_definition_id === definitionId && item.lifecycle === "ACTIVE",
  );
  if (!match) throw new Error(`installed Capsule not found: ${definitionId}`);
  return {
    instanceId: match.workflow_instance_id,
    root: join(workspace, match.relative_path),
  };
}

function hashTree(root: string): string {
  const digest = createHash("sha256");
  function visit(directory: string, prefix: string) {
    for (const name of readdirSync(directory).sort()) {
      const path = join(directory, name);
      const relative = prefix ? `${prefix}/${name}` : name;
      const info = statSync(path);
      if (info.isDirectory()) visit(path, relative);
      else if (info.isFile()) {
        digest.update(relative);
        digest.update("\0");
        digest.update(readFileSync(path));
        digest.update("\0");
      }
    }
  }
  visit(root, "");
  return digest.digest("hex");
}

test("qualifies the controlled first-time Literature Search to Idea Discovery journey", async ({ page }) => {
  const work = mkdtempSync(join(tmpdir(), "reagent-h1-product-e2e-"));
  const workspace = join(work, "workspace");
  try {
    await page.goto("/projects/new");
    await page.getByRole("textbox", { name: /^Project name/ }).fill("H1 controlled product journey");
    await page.getByRole("textbox", { name: /^Fictional or public research topic/ }).fill(
      "LLM agents for scientific literature analysis",
    );
    await page.getByRole("button", { name: "Create project" }).click();
    await expect(page).toHaveURL(/\/projects\/project-[0-9a-f]{32}$/);
    const projectId = page.url().split("/").at(-1)!;
    await expect(page.getByRole("heading", { name: "Create your Local Workspace" })).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: "Download setup file" }).click();
    const descriptor = await (await downloadPromise).path();
    expect(descriptor).not.toBeNull();
    const bootstrap = commandJson(
      "python3",
      [resolve(repoRoot, "reagent_local.py"), "bootstrap", workspace, "--descriptor", descriptor!, "--json"],
    );
    expect(bootstrap.status).toBe("CREATED");

    const firstSync = workspaceCommand(workspace, ["sync", workspace, "--api-url", backendUrl]);
    expect(firstSync.status).toBe("SYNCED");
    const literature = installedCapsule(
      workspace,
      "literature-search-local-experimental",
    );
    const preflight = workspaceCommand(workspace, [
      "run",
      workspace,
      "--workflow",
      "literature-search-local-experimental",
      "--api-url",
      backendUrl,
      "--preflight-only",
    ]);
    expect(preflight.status).toBe("PREFLIGHT_READY");

    const fakeLiteratureCodex = join(work, "codex-literature-fixture");
    copyFileSync(
      resolve(repoRoot, "backend/workflow_packages/tests/fake_codex_cli.py"),
      fakeLiteratureCodex,
    );
    chmodSync(fakeLiteratureCodex, 0o700);
    const literatureOutput = execFileSync(
      "python3",
      [
        resolve(repoRoot, "backend/workflow_packages/tests/interactive_e2e_driver.py"),
        "--package-root",
        literature.root,
        "--base-url",
        backendUrl,
      ],
      {
        env: {
          ...process.env,
          REAGENT_CODEX_EXECUTABLE: fakeLiteratureCodex,
          PYTHONDONTWRITEBYTECODE: "1",
        },
        encoding: "utf8",
      },
    );
    expect(literatureOutput).toContain("CHECKPOINT: FINALIZATION");
    expect(existsSync(join(literature.root, "outputs/artifacts/selected-paper-library"))).toBe(true);

    await page.goto(`/projects/${projectId}/progress`);
    await expect(page.getByText("Completed", { exact: true })).toBeVisible();
    await page.goto(`/projects/${projectId}/workflows`);
    const catalog = page.locator("section").filter({
      has: page.getByRole("heading", { name: "Add another research workflow" }),
    });
    const ideaCatalogCard = catalog.locator("article").filter({ hasText: "Idea Discovery" });
    await ideaCatalogCard.getByRole("button", { name: "Add workflow" }).click();
    await expect(page.getByText("Idea Discovery was added to this Project.")).toBeVisible();

    const literatureHashBeforeIdeaSync = hashTree(literature.root);
    const ideaSync = workspaceCommand(workspace, ["sync", workspace, "--api-url", backendUrl]);
    expect(ideaSync.status).toBe("SYNCED");
    expect(hashTree(literature.root)).toBe(literatureHashBeforeIdeaSync);
    const idea = installedCapsule(workspace, "idea-discovery-local-experimental");
    expect(idea.root).not.toBe(literature.root);

    await page.reload();
    const current = page.locator("section").filter({
      has: page.getByRole("heading", { name: "Your Project workflows" }),
    });
    const ideaCard = current.locator("article").filter({ hasText: "Idea Discovery" });
    await expect(ideaCard.getByText("Recommended: this is the only compatible result.")).toBeVisible();
    await ideaCard.getByRole("button", { name: "Confirm selected input" }).click();
    await expect(ideaCard.getByText("Input selected. Next, prepare the verified copy")).toBeVisible();

    const refreshed = workspaceCommand(workspace, ["artifact", "refresh", workspace, "--api-url", backendUrl]);
    expect(refreshed.status).toBe("INDEX_REFRESHED");
    const materialized = workspaceCommand(workspace, [
      "artifact",
      "materialize",
      workspace,
      "--workflow",
      "idea-discovery-local-experimental",
      "--api-url",
      backendUrl,
    ]);
    expect(materialized.status).toBe("MATERIALIZED");
    const ideaInput = join(idea.root, "inputs/selected-paper-library.json");
    expect(existsSync(ideaInput)).toBe(true);

    const ideaPreflight = workspaceCommand(workspace, [
      "run",
      workspace,
      "--workflow",
      "idea-discovery-local-experimental",
      "--api-url",
      backendUrl,
      "--preflight-only",
    ]);
    expect(ideaPreflight.status).toBe("PREFLIGHT_READY");

    const fakeIdeaCodex = join(work, "codex-idea-fixture");
    copyFileSync(
      resolve(repoRoot, "backend/workflow_packages/tests/fake_idea_codex_cli.py"),
      fakeIdeaCodex,
    );
    chmodSync(fakeIdeaCodex, 0o700);
    const runArgs = [
      "run",
      workspace,
      "--workflow",
      "idea-discovery-local-experimental",
      "--api-url",
      backendUrl,
      "--codex-executable",
      fakeIdeaCodex,
    ];
    expect(workspaceCommand(workspace, runArgs).status).toBe("RUN_COMPLETED");
    expect(existsSync(join(idea.root, "outputs/candidate_ideas.json"))).toBe(true);
    expect(existsSync(join(idea.root, "outputs/idea_discovery_report.md"))).toBe(true);

    const afterFirstSession = workspaceCommand(workspace, ["workflow", "list", workspace]);
    const listed = afterFirstSession.workflows as Array<Record<string, unknown>>;
    const listedIdea = listed.find(
      (item) => item.workflow_definition_id === "idea-discovery-local-experimental",
    );
    expect(listedIdea?.next_action).toBe("CONTINUE");

    // A second process has no browser/chat memory; continuation comes only from Capsule files.
    expect(workspaceCommand(workspace, runArgs).status).toBe("RUN_COMPLETED");
    const reports = readdirSync(join(idea.root, "memory/progress/reports")).filter(
      (name) => name.startsWith("prv2-") && name.endsWith(".json"),
    );
    expect(reports).toHaveLength(2);
    expect(readFileSync(join(idea.root, "memory/context.md"), "utf8")).toContain(
      "H1 deterministic session 2",
    );

    await page.goto(`/projects/${projectId}/workflows`);
    await expect(page.getByRole("heading", { name: "Literature Search" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Idea Discovery" }).first()).toBeVisible();
    await expect(page.getByText("Continue this Workflow")).toBeVisible();
    await page.goto(`/projects/${projectId}/progress?workflow_instance_id=${idea.instanceId}`);
    await expect(page.getByText("CANDIDATE_IDEAS", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("USER_REVIEW", { exact: true }).first()).toBeVisible();
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
});
