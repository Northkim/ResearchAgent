import type {
  ApiErrorBody,
  ApprovalDecisionRequest,
  ApprovalDecisionResponse,
  ApprovalPage,
  ApprovalStatus,
  Artifact,
  CreateCatalogRunRequest,
  ExecutionEvent,
  ProviderOperation,
  WorkflowDefinition,
  WorkflowRun,
  WorkflowRunPage,
  WorkflowRunStatus,
} from "@/types/api";

const API_BASE = "/backend";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let body: ApiErrorBody = {};
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      // Preserve a stable client error when the upstream body is not JSON.
    }
    throw new ApiError(
      body.error?.message ?? `Backend request failed with ${response.status}`,
      response.status,
      body.error?.code ?? "REQUEST_FAILED",
    );
  }

  return (await response.json()) as T;
}

async function requestText(path: string): Promise<string> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "text/markdown, application/json" },
  });
  if (!response.ok) {
    throw new ApiError(
      `Artifact content request failed with ${response.status}`,
      response.status,
      "ARTIFACT_CONTENT_FAILED",
    );
  }
  return response.text();
}

function queryString(values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined) params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const apiClient = {
  listWorkflows(): Promise<WorkflowDefinition[]> {
    return request("/workflows");
  },

  listRuns(options: {
    status?: WorkflowRunStatus;
    offset?: number;
    limit?: number;
  } = {}): Promise<WorkflowRunPage> {
    return request(
      `/runs${queryString({
        status: options.status,
        offset: options.offset ?? 0,
        limit: options.limit ?? 20,
      })}`,
    );
  },

  getRun(runId: string): Promise<WorkflowRun> {
    return request(`/runs/${encodeURIComponent(runId)}`);
  },

  createCatalogRun(payload: CreateCatalogRunRequest): Promise<WorkflowRun> {
    return request("/runs/from-catalog", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  resumeRun(runId: string): Promise<WorkflowRun> {
    return request(`/runs/${encodeURIComponent(runId)}/resume`, {
      method: "POST",
    });
  },

  listEvents(runId: string): Promise<ExecutionEvent[]> {
    return request(`/runs/${encodeURIComponent(runId)}/events`);
  },

  listArtifacts(runId: string): Promise<Artifact[]> {
    return request(`/runs/${encodeURIComponent(runId)}/artifacts`);
  },

  getArtifact(artifactId: string): Promise<Artifact> {
    return request(`/artifacts/${encodeURIComponent(artifactId)}`);
  },

  readArtifactContent(artifactId: string): Promise<string> {
    return requestText(`/artifacts/${encodeURIComponent(artifactId)}/content`);
  },

  listProviderUsage(runId: string): Promise<ProviderOperation[]> {
    return request(`/runs/${encodeURIComponent(runId)}/provider-usage`);
  },

  artifactContentUrl(artifactId: string): string {
    return `${API_BASE}/artifacts/${encodeURIComponent(artifactId)}/content`;
  },

  listApprovals(options: {
    status?: ApprovalStatus;
    offset?: number;
    limit?: number;
  } = {}): Promise<ApprovalPage> {
    return request(
      `/approvals${queryString({
        status: options.status,
        offset: options.offset ?? 0,
        limit: options.limit ?? 50,
      })}`,
    );
  },

  approve(
    approvalId: string,
    payload: ApprovalDecisionRequest,
  ): Promise<ApprovalDecisionResponse> {
    return request(`/approvals/${encodeURIComponent(approvalId)}/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  reject(
    approvalId: string,
    payload: ApprovalDecisionRequest,
  ): Promise<ApprovalDecisionResponse> {
    return request(`/approvals/${encodeURIComponent(approvalId)}/reject`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
