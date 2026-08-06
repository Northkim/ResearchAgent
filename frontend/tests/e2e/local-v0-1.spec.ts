import { execFileSync } from "node:child_process";
import { chmodSync, copyFileSync, existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { expect, test } from "@playwright/test";

test("runs one deterministic local round, auto-uploads, and displays its result", async ({ page }) => {
  const unique = Date.now().toString(36);
  const work = mkdtempSync(join(tmpdir(), "reagent-ls1-e2e-"));
  try {
    await page.goto("/");
    await expect(page).toHaveURL(/\/projects$/);
    await page.getByRole("link", { name: "Create project" }).click();
    await page.getByRole("textbox", { name: /^Project name/ }).fill(`Fictional LS1 E2E ${unique}`);
    await page.getByRole("textbox", { name: /^Fictional or public research topic/ }).fill(
      "A fictional public topic about transparent local research continuation",
    );
    await page.getByRole("button", { name: "Create local project" }).click();
    await expect(page).toHaveURL(/\/projects\/project-[0-9a-f]{32}$/);
    const projectId = page.url().split("/").at(-1)!;
    await expect(page.getByRole("heading", { name: "Four owner actions" })).toBeVisible();

    await page.getByRole("link", { name: "Generate Package" }).first().click();
    await page.getByRole("button", { name: "Generate Package" }).click();
    await expect(page.getByText("Package ready")).toBeVisible();
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: "Download Package ZIP" }).click();
    const download = await downloadPromise;
    const archive = await download.path();
    expect(archive).not.toBeNull();

    const packageRoot = join(work, "package");
    execFileSync("unzip", ["-q", archive!, "-d", packageRoot]);
    const fakeCodex = join(work, "codex-fixture");
    copyFileSync(
      resolve(process.cwd(), "../backend/workflow_packages/tests/fake_codex_cli.py"),
      fakeCodex,
    );
    chmodSync(fakeCodex, 0o700);
    const backendUrl = process.env.REAGENT_E2E_BACKEND_URL ?? "http://127.0.0.1:8000";
    const environment = {
      ...process.env,
      REAGENT_CODEX_EXECUTABLE: fakeCodex,
      PYTHONDONTWRITEBYTECODE: "1",
    };
    const first = execFileSync(
      "python3",
      ["reagent_local.py", "run", ".", "--mode", "demo", "--base-url", backendUrl],
      { cwd: packageRoot, env: environment, encoding: "utf8" },
    );
    expect(JSON.parse(first).status).toBe("ROUND_COMPLETED");
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
    expect(JSON.parse(replay).status).toBe("ROUND_ALREADY_UPLOADED");

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
