"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { isActiveRun } from "@/lib/format";
import type {
  Approval,
  ApprovalStatus,
  CreateCatalogRunRequest,
  CreateLocalProjectRequest,
  ProjectWorkflowInstance,
  WorkflowRunStatus,
} from "@/types/api";

import { apiClient } from "./client";
import { queryKeys } from "./query-keys";

export function useProjects() {
  return useQuery({ queryKey: queryKeys.projects, queryFn: apiClient.listProjects });
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: queryKeys.project(projectId),
    queryFn: () => apiClient.getProject(projectId),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateLocalProjectRequest) => apiClient.createProject(payload),
    onSuccess: async (project) => {
      queryClient.setQueryData(queryKeys.project(project.project_id), project);
      await queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

export function useGeneratePackage(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiClient.generatePackage(projectId),
    onSuccess: async (pkg) => {
      queryClient.setQueryData(queryKeys.projectPackage(projectId), pkg);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.project(projectId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.projects }),
      ]);
    },
  });
}

export function useProjectProgress(
  projectId: string,
  options: { workflowInstanceId?: string; offset?: number; limit?: number; enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: queryKeys.projectProgress(
      projectId,
      options.workflowInstanceId,
      options.offset ?? 0,
    ),
    queryFn: () => apiClient.getProjectProgress(projectId, options),
    enabled: options.enabled ?? true,
    retry: false,
  });
}

export function useWorkflowDefinitions() {
  return useQuery({
    queryKey: queryKeys.workflowDefinitions,
    queryFn: apiClient.listWorkflowDefinitions,
  });
}

export function useProjectWorkflowInstances(projectId: string) {
  return useQuery({
    queryKey: queryKeys.projectWorkflowInstances(projectId),
    queryFn: () => apiClient.listProjectWorkflowInstances(projectId),
  });
}

export function useCreateProjectWorkflowInstance(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      workflow_definition_id: string;
      workflow_version: string;
      capsule_id: string;
      capsule_version: string;
      display_name?: string;
      base_revision: number;
    }) => apiClient.createProjectWorkflowInstance(projectId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.projectWorkflowInstances(projectId) }),
        queryClient.invalidateQueries({ queryKey: ["projects", projectId, "progress"] }),
      ]);
    },
  });
}

export function useRetireProjectWorkflowInstance(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ instance, baseRevision }: {
      instance: ProjectWorkflowInstance;
      baseRevision: number;
    }) => apiClient.retireProjectWorkflowInstance(
      projectId,
      instance.workflow_instance_id,
      baseRevision,
    ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.projectWorkflowInstances(projectId) }),
        queryClient.invalidateQueries({ queryKey: ["projects", projectId, "progress"] }),
      ]);
    },
  });
}

export function useProjectArtifactReferences(projectId: string, artifactType: string) {
  return useQuery({
    queryKey: queryKeys.projectArtifactReferences(projectId, artifactType),
    queryFn: () => apiClient.listProjectArtifactReferences(projectId, { artifactType }),
    retry: false,
  });
}

export function useArtifactDependencies(projectId: string, workflowInstanceId: string) {
  return useQuery({
    queryKey: queryKeys.artifactDependencies(projectId, workflowInstanceId),
    queryFn: () => apiClient.listArtifactDependencies(projectId, workflowInstanceId),
    retry: false,
  });
}

export function useBindArtifactDependency(projectId: string, workflowInstanceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      artifactId: string;
      replaceBindingId?: string;
      idempotencyKey: string;
      requirementKey?: string;
    }) => apiClient.bindArtifactDependency(projectId, workflowInstanceId, {
      requirement_key: payload.requirementKey ?? "paper_library",
      artifact_id: payload.artifactId,
      idempotency_key: payload.idempotencyKey,
      replace_binding_id: payload.replaceBindingId,
    }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.artifactDependencies(projectId, workflowInstanceId),
        }),
        queryClient.invalidateQueries({
          queryKey: ["projects", projectId, "progress"],
        }),
      ]);
    },
  });
}

export function useProjectResources(projectId: string) {
  return useQuery({
    queryKey: queryKeys.projectResources(projectId),
    queryFn: () => apiClient.listProjectResources(projectId),
    retry: false,
  });
}

export function useWorkflowResourceBindings(projectId: string, workflowInstanceId: string) {
  return useQuery({
    queryKey: queryKeys.resourceBindings(projectId, workflowInstanceId),
    queryFn: () => apiClient.listWorkflowResourceBindings(projectId, workflowInstanceId),
    retry: false,
  });
}

export function useCreateProjectResource(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof apiClient.createProjectResource>[1]) =>
      apiClient.createProjectResource(projectId, payload),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: queryKeys.projectResources(projectId) }),
  });
}

export function useBindWorkflowResource(projectId: string, workflowInstanceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof apiClient.bindWorkflowResource>[2]) =>
      apiClient.bindWorkflowResource(projectId, workflowInstanceId, payload),
    onSuccess: async () => queryClient.invalidateQueries({
      queryKey: queryKeys.resourceBindings(projectId, workflowInstanceId),
    }),
  });
}

export function useProgressReports(projectId: string) {
  return useQuery({
    queryKey: queryKeys.projectProgressReports(projectId),
    queryFn: () => apiClient.listProgressReports(projectId),
  });
}

function decisionId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `decision-${Date.now()}`;
}

export function useWorkflows() {
  return useQuery({
    queryKey: queryKeys.workflows,
    queryFn: apiClient.listWorkflows,
  });
}

export function useRuns(options: { status?: WorkflowRunStatus; limit?: number } = {}) {
  return useQuery({
    queryKey: [...queryKeys.runs, options],
    queryFn: () => apiClient.listRuns({ ...options, limit: options.limit ?? 20 }),
  });
}

export function useRun(runId: string) {
  return useQuery({
    queryKey: queryKeys.run(runId),
    queryFn: () => apiClient.getRun(runId),
    refetchInterval: (query) => {
      const run = query.state.data;
      return run && !isActiveRun(run.status) ? false : 3_000;
    },
  });
}

export function useRunEvents(runId: string) {
  return useQuery({
    queryKey: queryKeys.events(runId),
    queryFn: () => apiClient.listEvents(runId),
    refetchInterval: 3_000,
  });
}

export function useApprovals(status?: ApprovalStatus) {
  return useQuery({
    queryKey: [...queryKeys.approvals, status ?? "ALL"],
    queryFn: () => apiClient.listApprovals({ status }),
    refetchInterval: status === "PENDING" ? 5_000 : false,
  });
}

export function useCreateAndRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateCatalogRunRequest) => {
      const created = await apiClient.createCatalogRun(payload);
      return apiClient.resumeRun(created.id);
    },
    onSuccess: async (run) => {
      queryClient.setQueryData(queryKeys.run(run.id), run);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.runs }),
        queryClient.invalidateQueries({ queryKey: queryKeys.approvals }),
        queryClient.invalidateQueries({ queryKey: queryKeys.workflows }),
      ]);
    },
  });
}

export function useRunArtifacts(runId: string) {
  return useQuery({
    queryKey: queryKeys.artifacts(runId),
    queryFn: () => apiClient.listArtifacts(runId),
    refetchInterval: 3_000,
  });
}

export function useArtifactContent(artifactId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.artifactContent(artifactId ?? "none"),
    queryFn: () => apiClient.readArtifactContent(artifactId as string),
    enabled: Boolean(artifactId),
  });
}

export function useProviderUsage(runId: string) {
  return useQuery({
    queryKey: queryKeys.providerUsage(runId),
    queryFn: () => apiClient.listProviderUsage(runId),
    refetchInterval: 3_000,
  });
}

export function useResumeRun(runId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiClient.resumeRun(runId),
    onSuccess: async (run) => {
      queryClient.setQueryData(queryKeys.run(run.id), run);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.runs }),
        queryClient.invalidateQueries({ queryKey: queryKeys.events(run.id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.approvals }),
        queryClient.invalidateQueries({ queryKey: queryKeys.artifacts(run.id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.providerUsage(run.id) }),
      ]);
    },
  });
}

export function useApprovalDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      approval,
      decision,
      reason,
    }: {
      approval: Approval;
      decision: "approve" | "reject";
      reason?: string;
    }) => {
      const common = {
        resolved_by: "prototype-reviewer",
        decision_idempotency_key: decisionId(),
        reason: reason || undefined,
        metadata: { source: "frontend_vertical_slice" },
      };
      return decision === "approve"
        ? apiClient.approve(approval.id, {
            ...common,
            current_fingerprint: approval.request_fingerprint,
          })
        : apiClient.reject(approval.id, common);
    },
    onSuccess: async (result) => {
      queryClient.setQueryData(
        queryKeys.run(result.workflow_run.id),
        result.workflow_run,
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.approvals }),
        queryClient.invalidateQueries({ queryKey: queryKeys.runs }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.events(result.workflow_run.id),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.artifacts(result.workflow_run.id),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.providerUsage(result.workflow_run.id),
        }),
      ]);
    },
  });
}
