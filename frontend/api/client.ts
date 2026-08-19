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
  CreateLocalProjectRequest,
  LocalPackage,
  LocalProject,
  ProjectProgress,
  UploadedProgressReport,
  WorkflowCatalogPage,
  ProjectWorkflowInstance,
  ProjectWorkflowInstancePage,
  CanonicalArtifactPage,
  ArtifactDependencyBinding,
  ArtifactDependencyPage,
  WorkflowInputSetupDecision,
  WorkflowInputSetupState,
  ProjectResourcePage,
  ProjectResourceReference,
  WorkflowResourceBinding,
  WorkflowResourceBindingPage,
  WorkflowCatalogDetail,
  ControlledLocalRunApproval,
  ControlledLocalRunApprovalProjection,
} from "@/types/api";

const API_BASE = "/backend";

export interface UserSkill {
  skill_id: string;
  name: string;
  slug: string;
  description: string;
  source_locator: string;
  source_revision: string;
  source_checksum: string;
  usage_count: number;
  local_status: "Ready" | "Needs sync" | null;
}

export interface UserSkillPage { items: UserSkill[]; total: number }

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly requestId?: string,
  ) {
    super(requestId ? `${message} Diagnostic request: ${requestId}.` : message);
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
      response.headers.get("x-request-id") ?? undefined,
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
      response.headers.get("x-request-id") ?? undefined,
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
  listProjects(): Promise<LocalProject[]> {
    return request("/projects");
  },

  getProject(projectId: string): Promise<LocalProject> {
    return request(`/projects/${encodeURIComponent(projectId)}`);
  },

  listUserSkills(): Promise<UserSkillPage> {
    return request("/user-skills");
  },

  createUserSkill(payload: {
    name: string;
    description: string;
    source_locator: string;
    source_revision?: string;
  }): Promise<UserSkill> {
    return request("/user-skills", { method: "POST", body: JSON.stringify(payload) });
  },

  listProjectUserSkills(projectId: string): Promise<UserSkillPage> {
    return request(`/projects/${encodeURIComponent(projectId)}/user-skills`);
  },

  attachProjectUserSkill(projectId: string, skillId: string): Promise<UserSkill> {
    return request(`/projects/${encodeURIComponent(projectId)}/user-skills`, {
      method: "POST", body: JSON.stringify({ skill_id: skillId }),
    });
  },

  detachProjectUserSkill(projectId: string, skillId: string): Promise<void> {
    return request(`/projects/${encodeURIComponent(projectId)}/user-skills/${encodeURIComponent(skillId)}`, {
      method: "DELETE",
    });
  },

  createProject(payload: CreateLocalProjectRequest): Promise<LocalProject> {
    return request("/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  generatePackage(projectId: string): Promise<LocalPackage> {
    return request(`/projects/${encodeURIComponent(projectId)}/packages`, {
      method: "POST",
    });
  },

  getLatestPackage(projectId: string): Promise<LocalPackage> {
    return request(`/projects/${encodeURIComponent(projectId)}/packages/latest`);
  },

  packageDownloadUrl(projectId: string, packageId: string): string {
    return `${API_BASE}/projects/${encodeURIComponent(projectId)}/packages/${encodeURIComponent(packageId)}/download`;
  },

  workspaceBootstrapDownloadUrl(projectId: string): string {
    return `${API_BASE}/projects/${encodeURIComponent(projectId)}/workspace-bootstrap`;
  },

  localClientDownloadUrl(): string {
    return `${API_BASE}/local-client/reagent_local.py`;
  },

  getProjectProgress(
    projectId: string,
    options: { workflowInstanceId?: string; offset?: number; limit?: number } = {},
  ): Promise<ProjectProgress> {
    return request(`/projects/${encodeURIComponent(projectId)}/progress${queryString({
      workflow_instance_id: options.workflowInstanceId,
      offset: options.offset,
      limit: options.limit,
    })}`);
  },

  listWorkflowDefinitions(): Promise<WorkflowCatalogPage> {
    return request("/workflow-definitions");
  },

  getWorkflowDefinition(workflowDefinitionId: string): Promise<WorkflowCatalogDetail> {
    return request(`/workflow-definitions/${encodeURIComponent(workflowDefinitionId)}`);
  },

  listProjectWorkflowInstances(projectId: string): Promise<ProjectWorkflowInstancePage> {
    return request(`/projects/${encodeURIComponent(projectId)}/workflow-instances`);
  },

  createProjectWorkflowInstance(projectId: string, payload: {
    workflow_definition_id: string;
    workflow_version: string;
    capsule_id: string;
    capsule_version: string;
    display_name?: string;
    base_revision: number;
  }): Promise<ProjectWorkflowInstance> {
    return request(`/projects/${encodeURIComponent(projectId)}/workflow-instances`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  startWritingRevision(projectId: string, payload: {
    parent_manuscript_artifact_id: string;
    causal_review_artifact_id: string;
    base_revision: number;
  }): Promise<ProjectWorkflowInstance> {
    return request(`/projects/${encodeURIComponent(projectId)}/writing-revisions`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  retireProjectWorkflowInstance(
    projectId: string,
    instanceId: string,
    baseRevision: number,
  ): Promise<ProjectWorkflowInstance> {
    return request(
      `/projects/${encodeURIComponent(projectId)}/workflow-instances/${encodeURIComponent(instanceId)}/retire`,
      { method: "POST", body: JSON.stringify({ base_revision: baseRevision }) },
    );
  },

  listProjectArtifactReferences(
    projectId: string,
    options: { artifactType?: string; workflowInstanceId?: string } = {},
  ): Promise<CanonicalArtifactPage> {
    return request(`/projects/${encodeURIComponent(projectId)}/artifacts${queryString({
      artifact_type: options.artifactType === "all" ? undefined : options.artifactType,
      workflow_instance_id: options.workflowInstanceId,
      limit: 100,
    })}`);
  },

  listCompatibleArtifactReferences(
    projectId: string,
    workflowInstanceId: string,
    requirementKey: string,
  ): Promise<CanonicalArtifactPage> {
    return request(
      `/projects/${encodeURIComponent(projectId)}/workflow-instances/` +
      `${encodeURIComponent(workflowInstanceId)}/artifact-requirements/` +
      `${encodeURIComponent(requirementKey)}/candidates?limit=100`,
    );
  },

  listArtifactDependencies(
    projectId: string,
    workflowInstanceId: string,
  ): Promise<ArtifactDependencyPage> {
    return request(
      `/projects/${encodeURIComponent(projectId)}/workflow-instances/` +
      `${encodeURIComponent(workflowInstanceId)}/artifact-dependencies`,
    );
  },

  bindArtifactDependency(
    projectId: string,
    workflowInstanceId: string,
    payload: {
      requirement_key: string;
      artifact_id: string;
      idempotency_key: string;
      replace_binding_id?: string;
    },
  ): Promise<ArtifactDependencyBinding> {
    return request(
      `/projects/${encodeURIComponent(projectId)}/workflow-instances/` +
      `${encodeURIComponent(workflowInstanceId)}/artifact-dependencies`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  },

  getWorkflowInputSetup(
    projectId: string,
    workflowInstanceId: string,
  ): Promise<WorkflowInputSetupState> {
    return request(
      `/projects/${encodeURIComponent(projectId)}/workflow-instances/` +
      `${encodeURIComponent(workflowInstanceId)}/input-setup`,
    );
  },

  confirmWorkflowInputSetup(
    projectId: string,
    workflowInstanceId: string,
    payload: {
      omitted_optional_requirement_keys: string[];
      idempotency_key: string;
    },
  ): Promise<WorkflowInputSetupDecision> {
    return request(
      `/projects/${encodeURIComponent(projectId)}/workflow-instances/` +
      `${encodeURIComponent(workflowInstanceId)}/input-setup-decisions`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  },

  listProjectResources(projectId: string): Promise<ProjectResourcePage> {
    return request(`/projects/${encodeURIComponent(projectId)}/resources?limit=100`);
  },

  createProjectResource(projectId: string, payload: {
    resource_kind: string;
    provider: string;
    locator: string;
    exact_revision: string;
    expected_content_checksum: string;
    display_name: string;
    metadata: Record<string, unknown>;
  }): Promise<ProjectResourceReference> {
    return request(`/projects/${encodeURIComponent(projectId)}/resources`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listWorkflowResourceBindings(
    projectId: string, workflowInstanceId: string,
  ): Promise<WorkflowResourceBindingPage> {
    return request(
      `/projects/${encodeURIComponent(projectId)}/workflow-instances/` +
      `${encodeURIComponent(workflowInstanceId)}/resource-bindings`,
    );
  },

  bindWorkflowResource(projectId: string, workflowInstanceId: string, payload: {
    requirement_key: string;
    resource_id: string;
    idempotency_key: string;
  }): Promise<WorkflowResourceBinding> {
    return request(
      `/projects/${encodeURIComponent(projectId)}/workflow-instances/` +
      `${encodeURIComponent(workflowInstanceId)}/resource-bindings`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  },

  observeControlledLocalRunApproval(
    projectId: string,
    workflowInstanceId: string,
  ): Promise<ControlledLocalRunApprovalProjection> {
    return request(
      `/projects/${encodeURIComponent(projectId)}/workflow-instances/` +
      `${encodeURIComponent(workflowInstanceId)}/run-approval`,
    );
  },

  decideControlledLocalRunApproval(
    projectId: string,
    workflowInstanceId: string,
    requestId: string,
    decision: "approve" | "reject",
    payload: {
      execution_plan_checksum: string;
      request_checksum: string;
      idempotency_key: string;
      reason?: string;
    },
  ): Promise<ControlledLocalRunApproval> {
    return request(
      `/projects/${encodeURIComponent(projectId)}/workflow-instances/` +
      `${encodeURIComponent(workflowInstanceId)}/run-approvals/` +
      `${encodeURIComponent(requestId)}/${decision}`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  },

  listProgressReports(projectId: string): Promise<UploadedProgressReport[]> {
    return request(`/projects/${encodeURIComponent(projectId)}/progress-reports`);
  },

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
