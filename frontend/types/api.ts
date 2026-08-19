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

export type LocalWorkflow = "LITERATURE_SEARCH";

export interface LocalPackage {
  package_id: string;
  package_schema_version: string;
  package_checksum: string;
  manifest_checksum: string;
  zip_checksum: string;
  workflow_id: string;
  workflow_version: string;
  workflow_checksum: string;
  file_count: number;
  package_size_bytes: number;
  generated_at: string;
  download_url: string;
}

export interface ProgressOutputArtifact {
  relative_path: string;
  artifact_kind: string;
  media_type: string;
  checksum: string;
  size: number | null;
}

export interface LegacyProjectProgress {
  schema_version: string;
  project_id: string;
  package_id: string;
  package_schema_version: string | null;
  package_checksum: string;
  workflow_id: string;
  workflow_version: string;
  latest_accepted_report_id: string;
  latest_accepted_report_checksum: string;
  latest_execution_round: number;
  latest_status: string;
  completed_work_summary: string[];
  current_state_summary: string;
  next_recommended_action: string;
  output_artifacts: ProgressOutputArtifact[];
  warning_count: number;
  error_count: number;
  unresolved_question_count: number;
  harness_type: string;
  latest_local_execution_timestamp: string;
  latest_upload_timestamp: string;
  chain_state: string;
  legacy_warning_state: boolean;
  projection_checksum: string;
}

export interface LocalProject {
  project_id: string;
  name: string;
  research_topic: string;
  selected_workflow: LocalWorkflow;
  created_at: string;
  updated_at: string;
  current_package: LocalPackage | null;
  progress: LegacyProjectProgress | null;
  attention: ProjectAttentionProjection;
}

export interface CreateLocalProjectRequest {
  name: string;
  research_topic: string;
  selected_workflow: LocalWorkflow;
  workflow_setup?: "literature-only" | "literature-and-idea" | "full-research" | "custom";
  custom_workflow_definition_ids?: string[];
}

export interface NormalizedProgressRecord {
  report_id: string;
  execution_round: number;
  status: string;
  completed_work: string[];
  current_state: string;
  next_recommended_action: string;
  output_artifacts: ProgressOutputArtifact[];
  warnings: string[];
  errors: string[];
  unresolved_questions: string[];
}

export interface UploadedProgressReport {
  receipt_id: string;
  project_id: string;
  workflow_instance_id: string;
  package_id: string;
  package_checksum: string;
  report_id: string;
  report_checksum: string;
  report_schema_version: string;
  original_report_checksum: string;
  original_report_size: number;
  original_report_media_type: string;
  envelope_checksum: string;
  uploaded_at: string;
  received_at: string;
  uploader_type: string;
  client_version: string;
  source_path_hint: string;
  validation_status: string;
  validation_errors: string[];
  validation_warnings: string[];
  chain_state: string;
  accepted_for_projection: boolean;
  normalized_record: NormalizedProgressRecord | null;
}

export interface WorkflowVersionCatalog {
  version: string;
  contract_checksum: string;
  input_schema_id: string;
  output_schema_id: string;
  review_status: string;
  core_capability_maturity: "REVIEWED_CORE" | "SCAFFOLD_CORE";
  published_at: string | null;
  artifact_requirements?: WorkflowArtifactRequirement[];
  skills?: WorkflowSkillProjection[];
  resource_requirements?: WorkflowResourceRequirement[];
}

export interface WorkflowResourceRequirement {
  requirement_key: string;
  resource_kind: "SOURCE_REPOSITORY" | "DATASET" | "MODEL" | "CHECKPOINT" | "GENERIC_FILE";
  required: boolean;
  cardinality_min: number;
  cardinality_max: number;
  allowed_providers: ("GITHUB" | "HUGGING_FACE" | "LOCAL_TEST")[];
  usage_description: string;
}

export interface ProjectResourceReference {
  resource_id: string;
  project_id: string;
  resource_kind: WorkflowResourceRequirement["resource_kind"];
  provider: "GITHUB" | "HUGGING_FACE" | "LOCAL_TEST";
  locator: string;
  exact_revision: string;
  expected_content_checksum: string;
  display_name: string;
  metadata: Record<string, unknown>;
  lifecycle: "ACTIVE" | "RETIRED";
  created_at: string;
}

export interface ProjectResourcePage {
  items: ProjectResourceReference[];
  total: number;
  offset: number;
  limit: number;
}

export interface WorkflowResourceBinding {
  binding_id: string;
  project_id: string;
  workflow_instance_id: string;
  workflow_definition_id: string;
  workflow_version: string;
  requirement_key: string;
  resource_id: string;
  expected_content_checksum: string;
  state: "ACTIVE" | "RETIRED";
  resource: ProjectResourceReference;
}

export interface WorkflowResourceBindingPage {
  items: WorkflowResourceBinding[];
  total: number;
}

export interface WorkflowSkillProjection {
  skill_id: string;
  display_name: string;
  version: string;
  checksum: string;
  trust: "BUILT_IN_REVIEWED";
  purpose: string;
}

export interface WorkflowArtifactRequirement {
  requirement_key: string;
  artifact_type: string;
  schema_constraint: string;
  required: boolean;
  target_relative_path: string;
}

export interface CapsuleVersionCatalog {
  capsule_id: string;
  capsule_version: string;
  workflow_version: string;
  definition_checksum: string;
  review_status: string;
  trust_classification: string | null;
  legacy_package_compatible: boolean;
}

export interface WorkflowCatalogItem {
  workflow_definition_id: string;
  stable_workflow_key: string;
  display_name: string;
  description: string;
  lifecycle: "AVAILABLE" | "PLANNED" | "RETIRED";
  creatable: boolean;
  allows_multiple_instances: boolean;
  recommended_version: WorkflowVersionCatalog | null;
  recommended_capsule: CapsuleVersionCatalog | null;
}

export interface WorkflowCatalogPage {
  items: WorkflowCatalogItem[];
  total: number;
}

export interface WorkflowCatalogDetail extends WorkflowCatalogItem {
  versions: WorkflowVersionCatalog[];
  capsules: CapsuleVersionCatalog[];
}

export interface ProjectWorkflowInstance {
  workflow_instance_id: string;
  project_id: string;
  workflow_definition_id: string;
  workflow_version: string;
  capsule_id: string | null;
  capsule_version: string | null;
  desired_state: "ACTIVE" | "RETIRED";
  display_name: string;
  created_manifest_revision: number;
  retired_manifest_revision: number | null;
  in_current_manifest: boolean;
  created_at: string;
  updated_at: string;
  skills?: WorkflowSkillProjection[];
  resource_requirements?: WorkflowResourceRequirement[];
}

export interface ProjectWorkflowInstancePage {
  items: ProjectWorkflowInstance[];
  total: number;
  manifest_revision: number;
}

export interface WorkflowStageProjection {
  code: string;
  label: string;
}

export interface WorkflowBlockerProjection {
  code: string;
  message: string;
}

export interface WorkflowNextActionProjection {
  surface: "BROWSER" | "LOCAL" | "INFORMATIONAL" | "NONE";
  code: string;
  label: string;
  description: string;
}

export interface WorkflowOutputProjection {
  label: string;
  artifact_id: string | null;
  artifact_type: string;
  artifact_schema: string;
  checksum: string | null;
  produced_at: string | null;
  progress_round: number | null;
  state: "EXPECTED" | "PRODUCED";
}

export interface WorkflowActionProjection {
  stage: WorkflowStageProjection;
  actor: "OWNER" | "AGENT" | "SYSTEM" | "NONE";
  attention_state: "NORMAL" | "OWNER_ACTION_REQUIRED" | "BLOCKED" | "ATTENTION_REQUIRED" | "COMPLETED";
  blocker: WorkflowBlockerProjection | null;
  next_action: WorkflowNextActionProjection;
  expected_output: WorkflowOutputProjection | null;
  latest_output: WorkflowOutputProjection | null;
}

export interface ProjectAttentionProjection {
  recommended_workflow_instance_id: string | null;
  recommended_workflow_label: string | null;
  action: WorkflowActionProjection;
  recent_change: { summary: string; changed_at: string | null };
  latest_output: WorkflowOutputProjection | null;
}

export interface WorkflowInstanceProgress {
  schema_version: string;
  project_id: string;
  workflow_instance_id: string;
  workflow_definition_id: string;
  workflow_definition_version: string;
  core_capability_maturity: "REVIEWED_CORE" | "SCAFFOLD_CORE";
  workflow_display_name: string;
  instance_display_name: string;
  friendly_instance_label?: string;
  lifecycle: "ACTIVE" | "RETIRED";
  desired_state: "DESIRED" | "NOT_DESIRED";
  capsule_id: string | null;
  capsule_version: string | null;
  research_status: string;
  latest_report_id: string | null;
  latest_report_checksum: string | null;
  latest_execution_round: number | null;
  latest_summary: string | null;
  next_recommended_action: string | null;
  artifact_metadata: ProgressOutputArtifact[];
  report_count: number;
  first_activity_at: string | null;
  latest_activity_at: string | null;
  installation_state: string;
  installation_manifest_revision: number | null;
  sync_uncertainty: string;
  readiness?: string;
  next_action?: "SETUP" | "SYNC" | "WAIT_FOR_UPSTREAM" | "SELECT_INPUT" | "MATERIALIZE" | "SELECT_RESOURCE" | "STAGE_RESOURCE" | "RUN" | "CONTINUE" | "REVIEW_RESULT" | "REVISE_MANUSCRIPT";
  missing_required_inputs?: string[];
  compatible_input_counts?: Record<string, number>;
  bound_required_inputs?: string[];
  result_count?: number;
  action: WorkflowActionProjection;
}

export interface ProjectProgress {
  schema_version: "reagent.project-progress/v0.1";
  project_id: string;
  project_name: string;
  research_topic: string;
  manifest_revision: number;
  cloud_observed_at: string;
  active_workflow_count: number;
  retired_workflow_count: number;
  total_progress_report_count: number;
  latest_project_activity_at: string | null;
  status_counts: Record<string, number>;
  instances: WorkflowInstanceProgress[];
  history: UploadedProgressReport[];
  history_offset: number;
  history_limit: number;
  history_total: number;
  has_more_history: boolean;
  dependency_edges: ArtifactDependencyEdge[];
  recommended_workflow_instance_id?: string | null;
  recommended_next_action?: string;
  attention: ProjectAttentionProjection;
  latest_status: string | null;
  latest_execution_round: number | null;
  current_state_summary: string | null;
  next_recommended_action: string | null;
  completed_work_summary: string[];
  output_artifacts: ProgressOutputArtifact[];
  warning_count: number;
  error_count: number;
}

export type ControlledLocalRunApprovalStatus =
  | "REQUESTED"
  | "APPROVED"
  | "REJECTED"
  | "CONSUMED"
  | "SUPERSEDED";

export interface ControlledLocalRunSummary {
  schema: "reagent.controlled-local-run-approval-summary/v0.1";
  what_will_run: string;
  research_objective: string;
  preparation_method: string;
  research_resources: string[];
  execution_environment: string;
  network_policy: "DISABLED" | "BOUNDED_DECLARED";
  compute_limits: string[];
  expected_outputs: string[];
  evaluation_approach: string;
  important_assumptions: string[];
  important_limitations: string[];
  summary_checksum: string;
}

export interface ControlledLocalRunApproval {
  schema: "reagent.controlled-local-run-approval/v0.1";
  request_id: string;
  project_id: string;
  workflow_instance_id: string;
  research_objective_checksum: string;
  execution_plan_checksum: string;
  validated_package_checksum: string;
  runtime_compatibility_checksum: string | null;
  capability_checksum: string | null;
  summary: ControlledLocalRunSummary;
  created_at: string;
  request_checksum: string;
  status: ControlledLocalRunApprovalStatus;
  owner_actor: string | null;
  decision_reason: string | null;
  decision_idempotency_key: string | null;
  decided_at: string | null;
  approval_checksum: string | null;
  consumed_attempt_id: string | null;
  consumed_at: string | null;
  consumption_checksum: string | null;
}

export interface ControlledLocalRunApprovalProjection {
  request: ControlledLocalRunApproval | null;
  next_action: string;
}

export interface ArtifactDependencyEdge {
  binding_id: string;
  consumer_workflow_instance_id: string;
  requirement_key: string;
  artifact_id: string;
  expected_checksum: string;
  state: string;
  producer_workflow_instance_id: string;
  artifact_type: string;
  artifact_schema_version: string;
  produced_at: string;
}

export interface CanonicalArtifactReference {
  schema_version: string;
  artifact_id: string;
  project_id: string;
  producer_workflow_instance_id: string;
  producer_progress_receipt_id: string;
  producer_progress_report_id: string;
  producer_execution_round: number;
  producer_capsule_id: string;
  producer_capsule_version: string;
  producer_core_capability_maturity: "REVIEWED_CORE" | "SCAFFOLD_CORE";
  artifact_type: string;
  artifact_schema_version: string;
  media_type: string;
  state: string;
  relative_path: string;
  content_checksum: string;
  size_bytes: number;
  cloud_metadata_available: boolean;
  produced_at: string;
  retired_at: string | null;
  created_at: string;
  updated_at: string;
  presentation?: {
    schema_identity: string;
    artifact_id: string;
    artifact_checksum: string;
    presentation_checksum: string;
    payload: Record<string, unknown>;
    reported_at: string;
  } | null;
}

export interface CanonicalArtifactPage {
  schema_version: string;
  project_id: string;
  artifacts: CanonicalArtifactReference[];
  offset: number;
  limit: number;
  total: number;
  has_more: boolean;
}

export interface ArtifactDependencyBinding {
  binding_id: string;
  project_id: string;
  consumer_workflow_instance_id: string;
  consumer_workflow_definition_id: string;
  consumer_workflow_version: string;
  requirement_key: string;
  artifact_id: string;
  expected_checksum: string;
  state: string;
  idempotency_key: string;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
}

export interface ArtifactDependencyPage {
  schema_version: string;
  project_id: string;
  consumer_workflow_instance_id: string;
  dependencies: ArtifactDependencyBinding[];
  offset: number;
  limit: number;
  total: number;
  has_more: boolean;
}

export interface WorkflowInputSetupDecision {
  decision_id: string;
  project_id: string;
  consumer_workflow_instance_id: string;
  consumer_workflow_definition_id: string;
  consumer_workflow_version: string;
  binding_set_checksum: string;
  omitted_optional_requirement_keys: string[];
  decision: "CONTINUE_WITHOUT_OPTIONAL_EVIDENCE";
  idempotency_key: string;
  decision_checksum: string;
  decided_at: string;
}

export interface WorkflowInputSetupState {
  schema_version: "reagent.workflow-input-setup-state/v0.1";
  project_id: string;
  consumer_workflow_instance_id: string;
  binding_set_checksum: string;
  missing_required_requirement_keys: string[];
  omitted_optional_requirement_keys: string[];
  decision_required: boolean;
  current_decision: WorkflowInputSetupDecision | null;
}
