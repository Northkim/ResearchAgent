"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { isActiveRun } from "@/lib/format";
import type {
  Approval,
  ApprovalStatus,
  CreateCatalogRunRequest,
  CreateLocalProjectRequest,
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

export function useProjectProgress(projectId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.projectProgress(projectId),
    queryFn: () => apiClient.getProjectProgress(projectId),
    enabled,
    retry: false,
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
