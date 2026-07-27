export type WorkflowRunStatus =
  | "CREATED"
  | "INITIALIZING"
  | "RUNNING"
  | "WAITING_FOR_APPROVAL"
  | "WAITING_FOR_INPUT"
  | "RETRY_SCHEDULED"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLING"
  | "CANCELLED";

export type StepRunStatus =
  | "CREATED"
  | "READY"
  | "RUNNING"
  | "WAITING_APPROVAL"
  | "COMPLETED"
  | "FAILED"
  | "SKIPPED"
  | "CANCELLED";

export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED";

export type EventType =
  | "WORKFLOW_STARTED"
  | "STEP_STARTED"
  | "SKILL_EXECUTED"
  | "CHECKPOINT_CREATED"
  | "APPROVAL_REQUESTED"
  | "WORKFLOW_COMPLETED"
  | "WORKFLOW_FAILED";

export interface WorkflowStepDefinition {
  id: string;
  kind: "skill" | "approval";
  needs: string[];
  uses: string | null;
  input_mapping: Record<string, unknown>;
  timeout_seconds: number;
  max_attempts: number;
  approval_policy: string | null;
}

export interface WorkflowDefinition {
  id: string;
  version: string;
  name: string;
  schema_version: string;
  input_schema: Record<string, WorkflowInputDefinition>;
  outputs: Record<string, unknown>;
  steps: WorkflowStepDefinition[];
}

export interface WorkflowInputDefinition {
  type?: "string" | "integer" | "number" | "boolean" | "array" | "object";
  required?: boolean;
  description?: string;
  default?: unknown;
  internal?: boolean;
  minimum?: number;
  maximum?: number;
}

export interface WorkflowRunSummary {
  id: string;
  project_id: string;
  workflow_id: string;
  workflow_version: string;
  workflow_name: string;
  status: WorkflowRunStatus;
  wait_reason: string | null;
  error_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRunPage {
  runs: WorkflowRunSummary[];
  total: number;
  offset: number;
  limit: number;
}

export interface StepRun {
  id: string;
  step_id: string;
  attempt: number;
  status: StepRunStatus;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  error_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRun {
  id: string;
  project_id: string;
  workflow_id: string;
  workflow_version: string;
  actor_user_id: string;
  agent_session_id: string;
  status: WorkflowRunStatus;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  wait_reason: string | null;
  error_code: string | null;
  completed_steps: string[];
  checkpoint_count: number;
  created_at: string;
  updated_at: string;
  steps: StepRun[];
}

export interface ExecutionEvent {
  id: string;
  sequence: number;
  type: EventType;
  severity: "INFO" | "WARNING" | "ERROR";
  payload: Record<string, unknown>;
  timestamp: string;
  agent_session_id: string | null;
  step_run_id: string | null;
  correlation_id: string | null;
  causation_id: string | null;
}

export interface Approval {
  id: string;
  project_id: string;
  workflow_run_id: string;
  step_run_id: string;
  policy_key: string;
  request_fingerprint: string;
  prompt: string;
  requested_action: Record<string, unknown>;
  requested_by: string;
  permitted_approver_role: string;
  requested_at: string;
  expires_at: string | null;
  status: ApprovalStatus;
  resolved_by: string | null;
  resolved_at: string | null;
  decision_reason: string | null;
}

export interface ApprovalPage {
  approvals: Approval[];
  total: number;
  offset: number;
  limit: number;
}

export interface ApprovalDecisionResponse {
  approval: Approval;
  workflow_run: WorkflowRun;
}

export interface CreateRunRequest {
  project_id: string;
  actor_user_id: string;
  idempotency_key: string;
  agent_profile_ref: string;
  workflow: WorkflowDefinition;
  inputs: Record<string, unknown>;
}

export interface CreateCatalogRunRequest {
  project_id: string;
  actor_user_id: string;
  idempotency_key: string;
  agent_profile_ref: string;
  workflow_id: string;
  workflow_version: string;
  inputs: Record<string, unknown>;
}

export interface Artifact {
  id: string;
  logical_name: string;
  version: number;
  kind: string;
  checksum: string;
  media_type: string;
  size: number;
  producer_run_id: string | null;
  producer_step_run_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ProviderOperation {
  id: string;
  logical_step_id: string;
  provider_category: string;
  operation_kind: string;
  provider_identity: string;
  adapter_version: string;
  model_or_endpoint: string;
  status: string;
  settlement_state: string;
  request_count: number;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_minor_units: number | null;
  cost_currency: string | null;
  failure_category: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface ApprovalDecisionRequest {
  resolved_by: string;
  decision_idempotency_key: string;
  current_fingerprint?: string;
  reason?: string;
  metadata?: Record<string, unknown>;
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
  };
}
