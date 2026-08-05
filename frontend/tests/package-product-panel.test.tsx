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
  expect(await screen.findByText(localProjectFixture.current_package!.package_checksum)).toBeVisible();
  expect(screen.getByText(localProjectFixture.current_package!.zip_checksum)).toBeVisible();
  expect(screen.getByRole("link", { name: "Download Package ZIP" })).toHaveAttribute(
    "href",
    expect.stringContaining("/download"),
  );
  expect(screen.getByText(/Credentials are not included/)).toBeVisible();
  expect(screen.getByText("AGENT.md")).toBeVisible();
});
