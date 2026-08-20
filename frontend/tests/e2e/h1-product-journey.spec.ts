import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  chmodSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { requireIsolatedQualification } from "./qualification-safety";

type JsonObject = Record<string, unknown>;

const backendUrl = process.env.REAGENT_E2E_BACKEND_URL ?? "http://127.0.0.1:8000";
const repoRoot = resolve(process.cwd(), "..");

test.beforeAll(() => requireIsolatedQualification());

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

test("qualifies the controlled first-time Literature Search to Idea Discovery journey", async ({ page, context }) => {
  const work = mkdtempSync(join(tmpdir(), "reagent-h1-product-e2e-"));
  const workspace = join(work, "workspace");
  const screenshotRoot = resolve(repoRoot, ".agent_read/tmp/d1-usability-correction-1");
  const pageErrors: string[] = [];
  const externalRequests: string[] = [];
  const browserWorkspaceWrites: string[] = [];
  const frontendUrl = process.env.REAGENT_E2E_BASE_URL ?? "http://127.0.0.1:3000";
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
    if (!["GET", "HEAD", "OPTIONS"].includes(event.method()) && /\/workspace(?:\/|$)/.test(url.pathname)) {
      browserWorkspaceWrites.push(`${event.method()} ${url.pathname}`);
    }
  });
  try {
    rmSync(screenshotRoot, { recursive: true, force: true });
    mkdirSync(screenshotRoot, { recursive: true });
    await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: frontendUrl });
    await page.goto("/projects/new");
    await page.screenshot({ path: join(screenshotRoot, "new-project.png"), fullPage: false });
    await page.getByRole("textbox", { name: /^Project name/ }).fill("H1 first-time research journey");
    await page.getByRole("textbox", { name: /^Fictional or public research topic/ }).fill(
      "LLM agents for scientific literature analysis",
    );
    await page.getByRole("button", { name: "Create project" }).click();
    await expect(page).toHaveURL(/\/projects\/project-[0-9a-f]{32}$/);
    const projectId = page.url().split("/").at(-1)!;
    const setupPanel = page.getByRole("region", { name: "Set up local workspace" });
    await expect(setupPanel.getByText("Local workspace not set up", { exact: true })).toBeVisible();
    const setupAction = setupPanel.getByRole("link", { name: "Set up local workspace" });
    await expect(setupAction).toHaveAttribute("href", `/projects/${projectId}/help`);
    await expect(page.getByRole("link", { name: "Sync workspace" })).toHaveCount(0);
    await page.screenshot({ path: join(screenshotRoot, "project-overview-setup.png"), fullPage: false });
    await page.goto("/projects");
    await expect(page.getByRole("heading", { name: "H1 first-time research journey" })).toBeVisible();
    await page.screenshot({ path: join(screenshotRoot, "projects.png"), fullPage: false });
    await page.goto(`/projects/${projectId}`);
    await setupAction.click();
    await expect(page).toHaveURL(`/projects/${projectId}/help`);
    await expect(page.getByRole("heading", { name: "Set up this Project" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Download local tool" })).toBeVisible();
    const downloadSetup = page.getByRole("link", { name: "Download setup file" });
    await expect(downloadSetup).toBeVisible();
    await expect(page.getByText("python reagent_local.py bootstrap ./reagent-workspace --descriptor ./workspace-bootstrap.json")).toBeVisible();
    const enterAndSync = page.locator(".copy-command code").filter({ hasText: "cd ./reagent-workspace" });
    await expect(enterAndSync).toContainText("cd ./reagent-workspace");
    await expect(enterAndSync).toContainText("python reagent_local.py sync .");
    await enterAndSync.scrollIntoViewIfNeeded();
    await page.screenshot({ path: join(screenshotRoot, "project-help.png"), fullPage: false });

    const downloadPromise = page.waitForEvent("download");
    await downloadSetup.click();
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
    await page.goto(`/projects/${projectId}`);
    const readyPanel = page.getByRole("region", { name: "Literature Search is ready" });
    await expect(readyPanel.getByText(/Run Literature Search in your Local Workspace/)).toBeVisible();
    const viewRunInstructions = readyPanel.getByRole("link", { name: "View run instructions" });
    await expect(viewRunInstructions).toHaveAttribute(
      "href",
      `/projects/${projectId}/workflows/${literature.instanceId}`,
    );
    await expect(readyPanel.getByRole("link", { name: "Run locally" })).toHaveCount(0);
    await page.screenshot({ path: join(screenshotRoot, "project-overview-ready.png"), fullPage: false });
    await viewRunInstructions.click();
    await expect(page).toHaveURL(`/projects/${projectId}/workflows/${literature.instanceId}`);
    const showRunInstructions = page.getByRole("button", { name: "Show run instructions" });
    await expect(showRunInstructions).toHaveAttribute("aria-expanded", "false");
    await showRunInstructions.click();
    await expect(showRunInstructions).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#run-locally")).toHaveAttribute("open", "");
    await expect(page.getByText("Exact command", { exact: true })).toBeVisible();
    await expect(page.getByText(`python reagent_local.py run . --workflow-instance ${literature.instanceId}`)).toBeVisible();
    const copyExactCommand = page.getByRole("button", { name: "Copy Literature Search exact command" });
    await expect(copyExactCommand).toBeVisible();
    await copyExactCommand.click();
    await expect(copyExactCommand).toHaveText("Copied");
    await page.screenshot({ path: join(screenshotRoot, "workflow-run-instructions.png"), fullPage: false });

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
    const driver = resolve(
      repoRoot,
      "backend/workflow_packages/tests/interactive_e2e_driver.py",
    );
    const interruptedOutput = execFileSync(
      "python3",
      [
        driver,
        "--workspace-root",
        workspace,
        "--capsule-root",
        literature.root,
        "--base-url",
        backendUrl,
        "--expect-exit",
        "50",
      ],
      {
        env: {
          ...process.env,
          REAGENT_CODEX_EXECUTABLE: fakeLiteratureCodex,
          REAGENT_FAKE_CODEX_NONZERO: "1",
          PYTHONDONTWRITEBYTECODE: "1",
        },
        encoding: "utf8",
      },
    );
    expect(interruptedOutput).toContain("CHECKPOINT: FINALIZATION");
    const interruptedControl = JSON.parse(
      readFileSync(join(literature.root, "memory/round-control.json"), "utf8"),
    ) as Record<string, unknown>;
    expect(interruptedControl.state).toBe("INTERRUPTED");
    expect(interruptedControl.last_completed_state).toBe("SEARCH_COMPLETED");
    expect(interruptedControl.finalization_confirmed).toBe(false);
    const interruptedList = workspaceCommand(workspace, ["workflow", "list", workspace]);
    const interruptedLiterature = (
      interruptedList.workflows as Array<Record<string, unknown>>
    ).find(
      (item) => item.workflow_definition_id === "literature-search-local-experimental",
    );
    expect(interruptedLiterature?.next_action).toBe("RESUME");
    const searchResultHashes = readdirSync(
      join(literature.root, "memory/search/operations"),
    )
      .filter((name) => name.endsWith(".result.json"))
      .sort()
      .map((name) =>
        createHash("sha256")
          .update(readFileSync(join(literature.root, "memory/search/operations", name)))
          .digest("hex"),
      );
    expect(searchResultHashes).toHaveLength(2);

    // Session B has no chat history. The generic Workspace command selects
    // the existing Capsule resume path from validator-approved local state.
    const literatureOutput = execFileSync(
      "python3",
      [
        driver,
        "--workspace-root",
        workspace,
        "--capsule-root",
        literature.root,
        "--base-url",
        backendUrl,
        "--resume",
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
    expect(literatureOutput).toContain("RESUME: persisted search plan");
    expect(literatureOutput).toContain("CHECKPOINT: FINALIZATION");
    const resumedSearchResultHashes = readdirSync(
      join(literature.root, "memory/search/operations"),
    )
      .filter((name) => name.endsWith(".result.json"))
      .sort()
      .map((name) =>
        createHash("sha256")
          .update(readFileSync(join(literature.root, "memory/search/operations", name)))
          .digest("hex"),
      );
    expect(resumedSearchResultHashes).toEqual(searchResultHashes);
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
    await page.goto(`/projects/${projectId}`);
    const syncPanel = page.getByRole("region", { name: "Sync the local workspace" });
    await expect(syncPanel.getByText("Local workspace needs syncing", { exact: true })).toBeVisible();
    const syncAction = syncPanel.getByRole("link", { name: "Sync workspace" });
    const syncHref = await syncAction.getAttribute("href");
    expect(syncHref).toMatch(
      new RegExp(`^/projects/${projectId}/workflows/wfi-[0-9a-f]{32}$`),
    );
    await syncAction.click();
    await expect(page).toHaveURL(syncHref!);
    await expect(page.getByRole("link", { name: "Sync workspace" })).toHaveAttribute("href", "#run-locally");
    await expect(page.locator("#run-locally")).toContainText("python reagent_local.py sync .");

    const ideaSync = workspaceCommand(workspace, ["sync", workspace, "--api-url", backendUrl]);
    expect(ideaSync.status).toBe("SYNCED");
    expect(hashTree(literature.root)).toBe(literatureHashBeforeIdeaSync);
    const idea = installedCapsule(workspace, "idea-discovery-local-experimental");
    expect(idea.root).not.toBe(literature.root);
    expect(syncHref).toBe(`/projects/${projectId}/workflows/${idea.instanceId}`);

    await page.goto(`/projects/${projectId}/workflows`);
    const current = page.getByRole("region", { name: "Workflow progression" });
    const ideaCard = current.locator("article").filter({ hasText: "Idea Discovery" });
    const openIdea = ideaCard.getByRole("link", { name: "Open Workflow" });
    await expect(openIdea).toHaveAttribute(
      "href",
      `/projects/${projectId}/workflows/${idea.instanceId}`,
    );
    await openIdea.click();
    await expect(page).toHaveURL(`/projects/${projectId}/workflows/${idea.instanceId}`);
    const inputs = page.getByRole("region", { name: "Inputs", exact: true });
    await expect(inputs.getByRole("radio")).toBeChecked();
    await inputs.getByRole("button", { name: "Confirm exact input" }).click();
    await expect(inputs.getByText("Selected", { exact: true })).toBeVisible();

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
    const progressedIdea = page.getByRole("region", { name: "Workflow progression" })
      .locator("article")
      .filter({ hasText: "Idea Discovery" });
    await expect(progressedIdea.getByText("Continue in Local Workspace", { exact: true })).toBeVisible();
    await page.goto(`/projects/${projectId}/progress?workflow_instance_id=${idea.instanceId}`);
    await expect(page.getByText("CANDIDATE_IDEAS", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("USER_REVIEW", { exact: true }).first()).toBeVisible();
    expect(pageErrors).toEqual([]);
    expect(externalRequests).toEqual([]);
    expect(browserWorkspaceWrites).toEqual([]);
    expect(readdirSync(screenshotRoot).sort()).toEqual([
      "new-project.png",
      "project-help.png",
      "project-overview-ready.png",
      "project-overview-setup.png",
      "projects.png",
      "workflow-run-instructions.png",
    ]);
    for (const name of readdirSync(screenshotRoot)) {
      expect(readFileSync(join(screenshotRoot, name))).not.toHaveLength(0);
    }
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
});
