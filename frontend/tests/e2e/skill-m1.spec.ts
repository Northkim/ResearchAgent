import { execFileSync } from "node:child_process";
import {
  existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { requireIsolatedQualification } from "./qualification-safety";

const source = "https://github.com/reagent-controlled/sample-research-skill";

test.beforeAll(() => requireIsolatedQualification());

test("qualifies the lightweight Owner-managed Skill journey", async ({ page, request }) => {
  const backend = process.env.REAGENT_E2E_BACKEND_URL!;
  const pwd = resolve(process.env.PWD ?? process.cwd());
  const repository = existsSync(join(pwd, "reagent_local.py"))
    ? pwd : resolve(process.cwd(), "..");
  const temporary = mkdtempSync(join(tmpdir(), "reagent-skill-m1-"));
  const workspace = join(temporary, "workspace");
  const descriptor = join(temporary, "workspace-bootstrap.json");
  const screenshots = join(repository, ".agent_read/tmp/skill-m1-e6");
  rmSync(screenshots, { recursive: true, force: true });
  mkdirSync(screenshots, { recursive: true });

  const created = await request.post(`${backend}/projects`, { data: {
    name: "Skill M1 disposable Project",
    research_topic: "Controlled Agent Skill qualification",
    selected_workflow: "LITERATURE_SEARCH",
    workflow_setup: "literature-only",
  } });
  expect(created.ok()).toBe(true);
  const project = await created.json() as { project_id: string };

  const local = (...args: string[]) => execFileSync("conda", [
    "run", "--no-capture-output", "-n", "reagent-dev", "python",
    "reagent_local.py", ...args,
  ], { cwd: repository, env: process.env, encoding: "utf8" });

  try {
    await page.goto("/skills");
    await expect(page.getByRole("heading", { name: "Skills", exact: true })).toBeVisible();
    await expect(page.getByText("No skills yet.")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Primary navigation" })
      .getByRole("link", { name: /Skills/ })).toBeVisible();
    await page.screenshot({ path: join(screenshots, "01-skills-empty.png"), fullPage: false });

    await page.getByRole("button", { name: "Add skill" }).first().click();
    await expect(page.getByLabel("Name")).toBeVisible();
    await expect(page.getByLabel("What does it help with?")).toBeVisible();
    await expect(page.getByLabel("GitHub URL")).toBeVisible();
    await expect(page.getByText(/checksum|capsule|manifest/i)).toHaveCount(0);
    await page.screenshot({ path: join(screenshots, "02-add-skill.png"), fullPage: false });

    await page.getByLabel("Name").fill("Academic Literature Review");
    await page.getByLabel("What does it help with?").fill(
      "Review papers and extract grounded evidence.",
    );
    await page.getByLabel("GitHub URL").fill(source);
    await page.getByRole("button", { name: "Add skill" }).click();
    await expect(page.getByText("Academic Literature Review")).toBeVisible();
    await expect(page.getByText("Used in 0 projects")).toBeVisible();
    await expect(page.getByText("Technical details")).toBeVisible();
    await page.screenshot({ path: join(screenshots, "03-skill-library.png"), fullPage: false });

    await page.goto(`/projects/${project.project_id}`);
    await expect(page.getByRole("heading", { name: "Skills", exact: true })).toBeVisible();
    await expect(page.getByText("No skills added yet.")).toBeVisible();
    await page.getByRole("link", { name: "Manage skills →" }).click();
    const choice = page.getByRole("checkbox", { name: /Academic Literature Review/ });
    await expect(choice).not.toBeChecked();
    await choice.check();
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Needs sync", { exact: true })).toBeVisible();

    const bootstrap = await request.get(
      `${backend}/projects/${project.project_id}/workspace-bootstrap`,
    );
    expect(bootstrap.ok()).toBe(true);
    writeFileSync(descriptor, JSON.stringify(await bootstrap.json()));
    expect(JSON.parse(local("bootstrap", workspace, "--descriptor", descriptor, "--json")).status)
      .toBe("CREATED");
    expect(JSON.parse(local("sync", workspace, "--api-url", backend, "--json")).status)
      .toBe("SYNCED");
    const installed = join(workspace, ".agents/skills/academic-literature-review/SKILL.md");
    expect(readFileSync(installed, "utf8")).toContain("Keep claims grounded");
    expect(JSON.parse(local("sync", workspace, "--api-url", backend, "--json")).status)
      .toBe("NO_CHANGE");

    await page.goto(`/projects/${project.project_id}`);
    await expect(page.getByText("Academic Literature Review")).toBeVisible();
    await expect(page.getByText("Ready", { exact: true })).toBeVisible();
    await page.screenshot({ path: join(screenshots, "04-project-skill-ready.png"), fullPage: false });

    const manual = join(workspace, ".agents/skills/owner-created/SKILL.md");
    mkdirSync(resolve(manual, ".."), { recursive: true });
    writeFileSync(manual, "# Owner-created Skill\n");
    await page.getByRole("link", { name: "Manage skills →" }).click();
    await page.getByRole("checkbox", { name: /Academic Literature Review/ }).uncheck();
    await page.getByRole("button", { name: "Save" }).click();
    expect(JSON.parse(local("sync", workspace, "--api-url", backend, "--json")).status)
      .toBe("SYNCED");
    expect(existsSync(installed)).toBe(false);
    expect(readFileSync(manual, "utf8")).toBe("# Owner-created Skill\n");
    await page.goto(`/projects/${project.project_id}`);
    await expect(page.getByText("No skills added yet.")).toBeVisible();
    await page.screenshot({ path: join(screenshots, "05-project-skill-detached.png"), fullPage: false });
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});
