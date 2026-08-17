import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { requireIsolatedQualification } from "./qualification-safety";

type Fixture = {
  run_id: string;
  project_id: string;
  project_name: string;
  instances: Record<string, string>;
  historical: Record<string, string>;
  non_experiment: string;
  artifacts: Record<string, string>;
  superseding_request: Record<string, unknown>;
};

test.describe.configure({ mode: "serial" });

test("GEN-D-C1 Owner projection and controlled-local approval pass real E6", async ({ page, request }) => {
  requireIsolatedQualification();
  const backend = process.env.REAGENT_E2E_BACKEND_URL;
  const identity = process.env.REAGENT_E2E_QUALIFICATION_IDENTITY;
  const runtime = process.env.REAGENT_LOCAL_RUNTIME_DIR;
  if (!backend || !identity || !runtime) throw new Error("controlled E6 environment is incomplete");
  const manifestPath = join(runtime, "gen-d-c1-fixtures.json");
  execFileSync(
    "conda",
    ["run", "--no-capture-output", "-n", "reagent-dev", "python", "-m", "scripts.gen_d_c1_controlled_fixtures", "--api-url", backend, "--run-id", identity, "--manifest", manifestPath],
    { cwd: resolve(process.cwd(), ".."), env: process.env, stdio: "inherit" },
  );
  const fixture = JSON.parse(readFileSync(manifestPath, "utf8")) as Fixture;
  const screenshots = resolve(process.cwd(), "test-results", "gen-d-c1-e6", "screenshots");
  mkdirSync(screenshots, { recursive: true, mode: 0o700 });
  const shot = async (name: string) => page.screenshot({ path: join(screenshots, `${name}.png`), fullPage: true });
  const detail = (name: string) => `/projects/${fixture.project_id}/workflows/${fixture.instances[name]}`;
  const pageErrors: string[] = [];
  const externalRequests: string[] = [];
  const allowedPorts = new Set([
    new URL(process.env.REAGENT_E2E_BASE_URL!).port,
    new URL(backend).port,
  ]);
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (event) => {
    const url = new URL(event.url());
    if (["data:", "blob:", "about:"].includes(url.protocol)) return;
    if (!(["127.0.0.1", "localhost", "[::1]"].includes(url.hostname) && allowedPorts.has(url.port))) {
      externalRequests.push(event.url());
    }
  });

  await page.goto(detail("fresh"));
  await expect(page.getByText("Research objective", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "How would you like to start?" })).toBeVisible();
  await expect(page.getByText("Selected research idea · exact version recorded", { exact: false })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Prepare a new experiment with ReAgent" })).toBeVisible();
  await expect(page.getByText(/No existing code or Git repository is required/)).toBeVisible();
  const pathB = page.getByRole("heading", { name: "Use an existing local project" }).locator("..");
  await expect(pathB.getByText("Git is optional.")).toBeVisible();
  await expect(pathB.getByRole("button", { name: "Not available in this build" })).toBeDisabled();
  await expect(page.getByText(/GitHub repository|Commit SHA|ResourceReference/)).toHaveCount(0);
  await shot("01-fresh-experiment-and-path-b");
  const choosePath = page.getByRole("button", { name: "Choose this path" });
  await choosePath.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "What ReAgent understands" })).toBeVisible();
  await expect(page.getByText(/ReAgent owns the managed Workflow-local preparation area/)).toBeVisible();
  await expect(page.getByText(/filesystem folder|Git initialization|Python implementation|manifest|dependency file|entrypoint/i)).toHaveCount(0);

  await page.goto(detail("methodology"));
  await expect(page.getByRole("heading", { name: "ReAgent needs your decision" })).toBeVisible();
  await expect(page.getByText(/scientific choice must be resolved/i).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Review methodology" })).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain("METHODOLOGY_DECISION_REQUIRED");
  await shot("02-methodology-checkpoint");

  await page.goto(detail("design"));
  for (const label of ["Questions or hypotheses", "Inputs or materials", "Protocol", "Observations or expected outputs", "Evaluation criteria", "Reproducibility controls", "Resource constraints", "Compute constraints", "Network policy", "Assumptions", "Claim boundaries"]) {
    await expect(page.getByText(label, { exact: true })).toBeVisible();
  }
  await expect(page.getByRole("link", { name: "Approve experiment design" }).first()).toBeVisible();
  await expect(page.getByText(/does not run the experiment/i)).toBeVisible();
  expect(await page.locator("body").innerText()).not.toMatch(/Cross-validation|Robustness|Seeds/);

  await page.goto(detail("unsupported"));
  await expect(page.getByRole("heading", { name: "ReAgent cannot prepare this experiment automatically yet." })).toBeVisible();
  expect(await page.locator("body").innerText()).not.toMatch(/write.*Python|GitHub metadata|ResourceReference/);

  await page.goto(detail("resource"));
  await expect(page.getByRole("heading", { name: "A research resource is needed" })).toBeVisible();
  const resourceRow = page.getByText("Research resources", { exact: true }).locator("..").locator("..");
  await expect(resourceRow).toContainText("Needs attention");
  await expect(resourceRow).toContainText("not verified locally");
  expect(await page.locator("body").innerText()).not.toContain("RESOURCE_READINESS_REQUIRED");
  await shot("03-resource-readiness");

  await page.goto(detail("preparation_requirement"));
  await expect(page.getByRole("heading", { name: "A preparation prerequisite is missing" })).toBeVisible();
  const prerequisite = page.getByText("What ReAgent needs to prepare", { exact: true }).locator("..").locator("..");
  await expect(prerequisite).toContainText("Needs attention");
  await expect(prerequisite).toContainText("observation tool is missing");
  expect(await page.locator("body").innerText()).not.toContain("PREPARATION_REQUIREMENT_UNMET");
  await shot("04-preparation-prerequisite");

  await page.goto(detail("preparation_complete"));
  await expect(page.getByRole("heading", { name: "Experiment implementation prepared" })).toBeVisible();
  const prepared = page.getByText("Implementation preparation", { exact: true }).locator("..").locator("..");
  await expect(prepared).toContainText("Implementation prepared");
  await expect(prepared).not.toContainText("In progress");
  await shot("05-preparation-complete");

  await page.goto(detail("runtime"));
  await expect(page.getByRole("heading", { name: "No compatible execution environment is ready" })).toBeVisible();
  const runtimeRow = page.getByText("Execution environment", { exact: true }).locator("..").locator("..");
  await expect(runtimeRow).toContainText("Needs attention");
  await expect(runtimeRow).not.toContainText("Checked after the experiment is prepared");
  expect(await page.locator("body").innerText()).not.toContain("RUNTIME_INCOMPATIBLE");
  await shot("06-runtime-incompatible");

  await page.goto(detail("run_approval"));
  await expect(page.getByRole("heading", { name: "Exact run summary" })).toBeVisible();
  await expect(page.getByText("A bounded categorical observation protocol.")).toBeVisible();
  await expect(page.getByText("This supports only a narrow categorical claim")).toBeVisible();
  const approve = page.getByRole("button", { name: "Approve this run" });
  await expect(approve).toBeEnabled();
  await shot("07-run-approval-required");
  await approve.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Run approved")).toBeVisible();
  await expect(page.getByRole("link", { name: "Continue in Local Workspace" })).toBeVisible();
  await expect(page.getByText(/consume this one-use approval, and execute through the controlled local runner/i)).toBeVisible();
  await shot("08-run-approved-local-handoff");
  const observedApproval = await request.get(`${backend}/projects/${fixture.project_id}/workflow-instances/${fixture.instances.run_approval}/run-approval`);
  expect((await observedApproval.json()).request.status).toBe("APPROVED");

  await page.goto(detail("run_reject"));
  await page.getByRole("button", { name: "Request changes" }).click();
  await expect(page.getByText("Changes requested")).toBeVisible();
  await expect(page.getByText("This run is not approved.")).toBeVisible();

  await page.goto(detail("run_superseded"));
  await expect(page.getByRole("button", { name: "Approve this run" })).toBeVisible();
  const supersede = await request.post(`${backend}/projects/${fixture.project_id}/workflow-instances/${fixture.instances.run_superseded}/run-approvals`, { data: fixture.superseding_request });
  expect(supersede.ok()).toBe(true);
  await page.getByRole("button", { name: "Approve this run" }).click();
  await expect(page.locator('[role="alert"]:not(#__next-route-announcer__)')).toContainText("The prepared experiment changed after approval.");
  expect(await page.locator("body").innerText()).not.toContain("APPROVAL_SUPERSEDED");
  await shot("09-changed-plan-owner-language");

  await page.goto(detail("result_review"));
  const resultHeading = page.getByRole("heading", { name: "Experiment result" });
  const reviewHeading = page.getByRole("heading", { name: "Does this accurately represent the experiment and its limitations?" });
  await expect(resultHeading).toBeVisible();
  await expect(page.getByText("The final category remained amber under the bounded transition.")).toBeVisible();
  await expect(reviewHeading).toBeVisible();
  const resultBox = await resultHeading.boundingBox();
  const reviewBox = await reviewHeading.boundingBox();
  expect(resultBox!.y).toBeLessThan(reviewBox!.y);
  await shot("10-result-review");

  await page.goto(detail("non_ml"));
  await expect(page.getByText("The final category remained amber under the bounded transition.")).toBeVisible();
  await expect(page.getByRole("table").last()).toBeVisible();
  await expect(page.getByText("View chart data")).toBeVisible();
  const nonMlText = await page.locator("body").innerText();
  expect(nonMlText).not.toMatch(/accuracy|F1|Cross-validation|Robustness|dataset/i);
  await shot("11-completed-non-ml-result");

  await page.goto(detail("sklearn"));
  await expect(page.getByText("Held-out score")).toBeVisible();
  await expect(page.getByText("Configuration comparison")).toBeVisible();
  await expect(page.getByRole("img", { name: "Comparison series series chart" })).toBeVisible();
  await expect(page.getByText("View chart data")).toBeVisible();
  await expect(page.getByRole("heading", { name: "How would you like to start?" })).toBeVisible();
  await shot("12-completed-sklearn-shaped-result");

  await page.goto(detail("completed_absent"));
  await expect(page.getByText("Local result presentation has not yet been reported.")).toBeVisible();
  await expect(page.getByText("Scientific evidence", { exact: true }).locator("..").locator("..")).toContainText("Not reported");

  await page.goto(`/projects/${fixture.project_id}/outputs`);
  await expect(page.getByRole("heading", { name: `${fixture.project_name} Outputs` })).toBeVisible();
  await expect(page.getByText("The final category remained amber under the bounded transition.").first()).toBeVisible();
  await expect(page.getByText("Configuration B was stronger in this controlled reference-shaped fixture.")).toBeVisible();
  await expect(page.getByText("Local result presentation has not yet been reported.")).toBeVisible();
  await shot("13-outputs-typed-v4-preview");

  await page.goto(detail("run_approval"));
  const technical = page.getByText("Technical details").locator("..");
  await expect(technical).not.toHaveAttribute("open", "");
  await technical.locator("summary").click();
  await expect(technical).toHaveAttribute("open", "");
  for (const label of ["Workflow Definition", "Capsule", "Capability", "Validated package", "Runtime compatibility", "Run Approval request", "Run Approval status", "Execution Plan", "Artifact", "Presentation"]) {
    await expect(technical.getByText(label, { exact: true })).toBeVisible();
  }
  await shot("14-technical-details-expanded");
  await technical.locator("summary").click();
  await expect(technical).not.toHaveAttribute("open", "");

  for (const key of ["experiment_04", "experiment_05"] as const) {
    await page.goto(`/projects/${fixture.project_id}/workflows/${fixture.historical[key]}`);
    await expect(page.getByRole("heading", { name: /Reproduction & Experiment #/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: "How would you like to start?" })).toHaveCount(0);
  }
  await page.goto(`/projects/${fixture.project_id}/workflows/${fixture.non_experiment}`);
  await expect(page.getByRole("heading", { name: /Idea Discovery/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "How would you like to start?" })).toHaveCount(0);
  await page.goto(`/projects/${fixture.project_id}`);
  await expect(page.getByRole("heading", { name: fixture.project_name })).toBeVisible();
  await page.goto(`/projects/${fixture.project_id}/progress`);
  await expect(page.getByRole("heading", { name: `${fixture.project_name} Activity` })).toBeVisible();

  expect(pageErrors).toEqual([]);
  expect(externalRequests).toEqual([]);
});
