import { execFileSync } from "node:child_process";
import { chmodSync, copyFileSync, existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

function resultFrom(output: string): Record<string, unknown> {
  const line = output.replaceAll("\r", "").trim().split("\n").reverse().find((item) => item.startsWith("{"));
  if (!line) throw new Error("launcher did not print a final JSON result");
  return JSON.parse(line) as Record<string, unknown>;
}

async function createDownloadedPackage(page: Page, work: string, label: string) {
    await page.goto("/");
    await expect(page).toHaveURL(/\/projects$/);
    await page.getByRole("link", { name: "Create project" }).click();
    await page.getByRole("textbox", { name: /^Project name/ }).fill(label);
    await page.getByRole("textbox", { name: /^Fictional or public research topic/ }).fill(
      "A fictional public topic about transparent local research continuation",
    );
    await page.getByRole("button", { name: "Create local project" }).click();
    await expect(page).toHaveURL(/\/projects\/project-[0-9a-f]{32}$/);
    const projectId = page.url().split("/").at(-1)!;
    await expect(page.getByRole("heading", { name: "Eight guided steps" })).toBeVisible();

    await page.getByRole("link", { name: "Generate Package" }).first().click();
    await page.getByRole("button", { name: "Generate Package" }).click();
    await expect(page.getByText("Package ready")).toBeVisible();
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: "Download Package ZIP" }).click();
    const download = await downloadPromise;
    const archive = await download.path();
    expect(archive).not.toBeNull();

    const packageRoot = join(work, projectId);
    execFileSync("unzip", ["-q", archive!, "-d", packageRoot]);
    return { packageRoot, projectId };
}

function fixtureEnvironment(work: string) {
    const fakeCodex = join(work, "codex-fixture");
    if (!existsSync(fakeCodex)) {
      copyFileSync(resolve(process.cwd(), "../backend/workflow_packages/tests/fake_codex_cli.py"), fakeCodex);
      chmodSync(fakeCodex, 0o700);
    }
    return {
      ...process.env,
      REAGENT_CODEX_EXECUTABLE: fakeCodex,
      PYTHONDONTWRITEBYTECODE: "1",
    };
}

test("runs the default interactive demo through all checkpoints and displays its result", async ({ page }) => {
  const unique = Date.now().toString(36);
  const work = mkdtempSync(join(tmpdir(), "reagent-ls2-interactive-e2e-"));
  try {
    const { packageRoot, projectId } = await createDownloadedPackage(page, work, `Fictional LS2 interactive ${unique}`);
    const backendUrl = process.env.REAGENT_E2E_BACKEND_URL ?? "http://127.0.0.1:8000";
    const environment = fixtureEnvironment(work);
    const driver = resolve(process.cwd(), "../backend/workflow_packages/tests/interactive_e2e_driver.py");
    const first = execFileSync(
      "python3",
      [driver, "--package-root", packageRoot, "--base-url", backendUrl],
      { env: environment, encoding: "utf8" },
    );
    expect(first).toContain("[4/6] Launching interactive Codex");
    expect(first).toContain("CHECKPOINT: SEARCH PLAN");
    expect(first).toContain("CHECKPOINT: CANDIDATE SCREENING");
    expect(first).toContain("CHECKPOINT: FINALIZATION");
    expect(resultFrom(first).status).toBe("ROUND_COMPLETED");
    for (const output of [
      "search_plan.md",
      "candidate_papers.json",
      "selected_papers.json",
      "literature_search_report.md",
    ]) {
      expect(existsSync(join(packageRoot, "outputs", output))).toBe(true);
    }
    expect(readFileSync(join(packageRoot, "outputs/literature_search_report.md"), "utf8")).toContain(
      "FICTIONAL DEMO EVIDENCE",
    );

    const replay = execFileSync(
      "python3",
      ["reagent_local.py", "run", ".", "--mode", "demo", "--base-url", backendUrl],
      { cwd: packageRoot, env: environment, encoding: "utf8" },
    );
    expect(resultFrom(replay).status).toBe("ROUND_ALREADY_UPLOADED");

    await page.goto(`/projects/${projectId}/progress`);
    await expect(page.getByText("Round completed")).toHaveClass(/active/);
    await expect(page.getByText("FICTIONAL DEMO EVIDENCE: three representative records selected.")).toBeVisible();
    await expect(page.getByText("2", { exact: true })).toBeVisible();
    await expect(page.getByText("5", { exact: true })).toBeVisible();
    await expect(page.getByText("3", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Progress Report receipts" })).toBeVisible();
    await expect(page.getByText(/complete artifact contents remain/)).toBeVisible();

    const navigation = page.getByRole("navigation", { name: "Primary navigation" });
    await expect(navigation).not.toContainText(/run|resume|approval|hosted/i);
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
});

test("preserves the explicit unattended demo path", async ({ page }) => {
  const unique = Date.now().toString(36);
  const work = mkdtempSync(join(tmpdir(), "reagent-ls2-auto-e2e-"));
  try {
    const { packageRoot, projectId } = await createDownloadedPackage(page, work, `Fictional LS2 auto ${unique}`);
    const backendUrl = process.env.REAGENT_E2E_BACKEND_URL ?? "http://127.0.0.1:8000";
    const first = execFileSync(
      "python3",
      ["reagent_local.py", "run", ".", "--mode", "demo", "--auto", "--base-url", backendUrl],
      { cwd: packageRoot, env: fixtureEnvironment(work), encoding: "utf8" },
    );
    expect(first).toContain("[4/6] Launching Codex in auto mode");
    expect(resultFrom(first).status).toBe("ROUND_COMPLETED");
    await page.goto(`/projects/${projectId}/progress`);
    await expect(page.getByText("Round completed")).toHaveClass(/active/);
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
});
