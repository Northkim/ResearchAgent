import { afterEach, expect, test, vi } from "vitest";

import { ApiError, apiClient } from "@/api/client";

afterEach(() => vi.restoreAllMocks());

test("preserves safe backend diagnostics without exposing a traceback", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(
    JSON.stringify({ error: { code: "SERVICE_UNAVAILABLE", message: "Service is not ready" } }),
    {
      status: 503,
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": "operator-correlation-1",
      },
    },
  ));

  await expect(apiClient.listProjects()).rejects.toMatchObject({
    name: "ApiError",
    status: 503,
    code: "SERVICE_UNAVAILABLE",
    requestId: "operator-correlation-1",
    message: "Service is not ready Diagnostic request: operator-correlation-1.",
  } satisfies Partial<ApiError>);
});

test("exposes one fixed local client download URL", () => {
  expect(apiClient.localClientDownloadUrl()).toBe("/backend/local-client/reagent_local.py");
});

test("omits the frontend all sentinel while preserving exact Artifact type filters", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(
    JSON.stringify({ artifacts: [], total: 0, offset: 0, limit: 100 }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  ));

  await apiClient.listProjectArtifactReferences("project-1", { artifactType: "all" });
  await apiClient.listProjectArtifactReferences("project-1", {
    artifactType: "manuscript-draft/v4",
  });

  expect(fetch.mock.calls[0]?.[0]).toBe("/backend/projects/project-1/artifacts?limit=100");
  expect(fetch.mock.calls[1]?.[0]).toBe(
    "/backend/projects/project-1/artifacts?artifact_type=manuscript-draft%2Fv4&limit=100",
  );
});

test("requests candidates through the exact consumer requirement", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(
    JSON.stringify({ artifacts: [], total: 0, offset: 0, limit: 100 }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  ));

  await apiClient.listCompatibleArtifactReferences(
    "project-1", "wfi-1", "paper_library",
  );

  expect(fetch.mock.calls[0]?.[0]).toBe(
    "/backend/projects/project-1/workflow-instances/wfi-1/" +
    "artifact-requirements/paper_library/candidates?limit=100",
  );
});
