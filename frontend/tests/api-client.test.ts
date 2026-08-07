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
