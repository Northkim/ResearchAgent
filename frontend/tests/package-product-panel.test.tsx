import { render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { PackageProductPanel } from "@/components/package-product-panel";
import { Providers } from "@/lib/providers";

import { localProjectFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("shows Package checksum, ZIP download, and local Codex instructions", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  render(<Providers><PackageProductPanel projectId={localProjectFixture.project_id} /></Providers>);
  expect(await screen.findByText(localProjectFixture.current_package!.package_checksum)).toBeInTheDocument();
  expect(screen.getByText(localProjectFixture.current_package!.zip_checksum)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Download Package ZIP" })).toHaveAttribute(
    "href",
    expect.stringContaining("/download"),
  );
  expect(screen.getByText(/Credentials are not included/)).toBeVisible();
  expect(screen.getByText("python reagent_local.py run .")).toBeVisible();
  expect(screen.getByText("python reagent_local.py run . --mode demo")).toBeVisible();
  expect(screen.getByText(/interactive Codex session in your current terminal/)).toBeVisible();
  expect(screen.getByText("finish", { selector: "code" })).toBeVisible();
  expect(screen.getByText("Advanced / unattended mode")).toBeVisible();
  expect(screen.getByText(/Four research artifacts/)).toBeVisible();
  expect(screen.getByRole("link", { name: /Read full guide/ })).toHaveAttribute(
    "href",
    expect.stringContaining("/guide"),
  );
});
