import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";

import { expect, test } from "@playwright/test";

const ZERO_HASH = `sha256:${"0".repeat(64)}`;

interface PackageManifest {
  package_id: string;
  package_schema_version: string;
  package_checksum: string;
  experimental_project_identity: string;
  workflow_id: string;
  workflow_version: string;
  workflow_checksum: string;
  package_template_id: string;
  package_template_version: string;
  manifest_checksum: string;
  skill_pins: Array<{
    name: string;
    semantic_version: string;
    checksum: string;
  }>;
}

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${canonical(record[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function sha256(value: string | Buffer): string {
  return `sha256:${createHash("sha256").update(value).digest("hex")}`;
}

function progressEnvelope(manifest: PackageManifest) {
  const content = {
    schema_version: "progress-report/v0.2",
    package_id: manifest.package_id,
    package_schema_version: manifest.package_schema_version,
    package_checksum: manifest.package_checksum,
    project_id: manifest.experimental_project_identity,
    workflow_id: manifest.workflow_id,
    workflow_version: manifest.workflow_version,
    workflow_checksum: manifest.workflow_checksum,
    execution_round: 1,
    harness_type: "codex",
    harness_version: "fictional-e2e/1.0",
    harness_session_id: "fictional-local-e2e-session",
    previous_report_id: null,
    previous_report_checksum: null,
    started_at: "2026-08-05T13:00:00Z",
    completed_at: "2026-08-05T13:05:00Z",
    status: "IN_PROGRESS",
    completed_work: ["Validated the fictional local Package."],
    current_state: "Fictional local Package is ready for bounded screening.",
    next_recommended_action: "Continue the fictional screening with Codex.",
    continuation_reason: null,
    output_artifacts: [],
    context_before_checksum: `sha256:${"1".repeat(64)}`,
    context_after_checksum: `sha256:${"2".repeat(64)}`,
    warnings: ["Fictional E2E warning."],
    errors: [],
    unresolved_questions: [],
    continuation_instructions: ["Read local context before continuing."],
    skill_pins: manifest.skill_pins.map((pin: Record<string, string>) => ({
      pin_type: "SKILL",
      identity: pin.name,
      version: pin.semantic_version,
      checksum: pin.checksum,
    })),
    template_pins: [{
      pin_type: "TEMPLATE",
      identity: manifest.package_template_id,
      version: manifest.package_template_version,
      checksum: manifest.manifest_checksum,
    }],
    generated_at: "2026-08-05T13:05:00Z",
    experimental_declaration: "EXPERIMENTAL_PROGRESS_REPORT_V0_2",
  };
  const reportContentChecksum = sha256(canonical(content));
  const reportId = `prv2-${sha256(canonical({
    package_id: content.package_id,
    workflow_id: content.workflow_id,
    workflow_version: content.workflow_version,
    execution_round: content.execution_round,
    previous_report_id: content.previous_report_id,
    report_content_checksum: reportContentChecksum,
  })).split(":")[1]}`;
  const identified = {
    ...content,
    report_id: reportId,
    report_content_checksum: reportContentChecksum,
    report_checksum: ZERO_HASH,
  };
  const report = {
    ...identified,
    report_checksum: sha256(canonical({ ...identified, report_checksum: null })),
  };
  const original = Buffer.from(`${canonical(report)}\n`, "utf8");
  const base = {
    upload_schema_version: "progress-report-upload/v0.1",
    project_id: content.project_id,
    package_id: content.package_id,
    package_checksum: content.package_checksum,
    report_schema_version: content.schema_version,
    report_id: report.report_id,
    report_checksum: report.report_checksum,
    original_report_media_type: "application/json",
    original_report_base64: original.toString("base64"),
    original_report_checksum: sha256(original),
    original_report_size: original.byteLength,
    uploaded_at: "2026-08-05T13:06:00Z",
    uploader_type: "local-cli",
    client_version: "fictional-e2e/1.0",
    source_path_hint: "memory/progress/reports/fictional-e2e.json",
    context_snapshot_metadata: null,
    envelope_checksum: ZERO_HASH,
  };
  return {
    ...base,
    envelope_checksum: sha256(canonical({ ...base, envelope_checksum: null })),
  };
}

test("creates project, downloads Package, and displays explicit local progress", async ({ page }) => {
  const unique = Date.now().toString(36);
  await page.goto("/");
  await expect(page).toHaveURL(/\/projects$/);
  await page.getByRole("link", { name: "Create project" }).click();
  await page.getByRole("textbox", { name: /^Project name/ }).fill(`Fictional E2E ${unique}`);
  await page.getByRole("textbox", { name: /^Fictional or public research topic/ }).fill(
    "A fictional public topic about transparent local research continuation",
  );
  await page.getByRole("button", { name: "Create local project" }).click();
  await expect(page).toHaveURL(/\/projects\/project-[0-9a-f]{32}$/);
  const projectId = page.url().split("/").at(-1)!;
  await expect(page.getByText("No uploaded progress yet")).toBeVisible();

  await page.getByRole("link", { name: "Generate Package" }).click();
  await page.getByRole("button", { name: "Generate Workflow Package" }).click();
  await expect(page.getByText("Package checksum")).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download Package ZIP" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^literature-search-.*\.zip$/);
  const archive = await download.path();
  expect(archive).not.toBeNull();
  const manifest = JSON.parse(
    execFileSync("unzip", ["-p", archive!, "package-manifest.json"], { encoding: "utf8" }),
  ) as PackageManifest;
  expect(manifest.experimental_project_identity).toBe(projectId);

  const upload = await page.request.post(`/backend/projects/${projectId}/progress-reports`, {
    data: progressEnvelope(manifest),
  });
  expect(upload.status()).toBe(201);
  await page.goto(`/projects/${projectId}/progress`);
  await expect(page.getByText("Fictional local Package is ready for bounded screening.")).toBeVisible();
  await expect(page.getByText("Continue the fictional screening with Codex.")).toBeVisible();
  await expect(page.getByText("Fictional E2E warning.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Progress Report receipts" })).toBeVisible();

  const navigation = page.getByRole("navigation", { name: "Primary navigation" });
  await expect(navigation).not.toContainText(/run|resume|approval|hosted/i);
});
