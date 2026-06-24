// ─── Container & Workload Types ───────────────────────────────────────────────

export interface ContainerPort {
  name?: string;
  container_port: number;
  protocol: string;
}

export interface ResourceRequirements {
  requests?: Record<string, string>;
  limits?: Record<string, string>;
}

export interface EnvVar {
  name: string;
  value?: string;
  value_from?: Record<string, unknown>;
}

export interface Workload {
  id: string;
  name: string;
  namespace: string;
  kind: string;
  replicas: number;
  image: string;
  ports: ContainerPort[];
  component_type: string;
  env_vars: EnvVar[];
  resources: ResourceRequirements;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  volumes: unknown[];
  health_checks: Record<string, unknown>;
  service_account?: string;
  security_context?: Record<string, unknown>;
}

// ─── Service Types ─────────────────────────────────────────────────────────────

export interface ServicePort {
  name?: string;
  port: number;
  target_port: number;
  protocol: string;
  node_port?: number;
}

export interface Service {
  id: string;
  name: string;
  namespace: string;
  service_type: string;
  selector: Record<string, string>;
  ports: ServicePort[];
  labels: Record<string, string>;
  annotations: Record<string, string>;
}

// ─── Ingress Types ─────────────────────────────────────────────────────────────

export interface IngressRule {
  host?: string;
  paths: Array<{
    path: string;
    path_type: string;
    service_name: string;
    service_port: number;
  }>;
}

export interface Ingress {
  id: string;
  name: string;
  namespace: string;
  ingress_class?: string;
  rules: IngressRule[];
  tls: unknown[];
  annotations: Record<string, string>;
}

// ─── Config & Secret Types ─────────────────────────────────────────────────────

export interface ConfigMap {
  id: string;
  name: string;
  namespace: string;
  data: Record<string, string>;
  labels: Record<string, string>;
}

export interface Secret {
  id: string;
  name: string;
  namespace: string;
  secret_type: string;
  data_keys: string[];
  labels: Record<string, string>;
}

export interface PVC {
  id: string;
  name: string;
  namespace: string;
  storage_class?: string;
  access_modes: string[];
  storage: string;
  labels: Record<string, string>;
}

// ─── Autoscaling & Policy Types ───────────────────────────────────────────────

export interface AutoscalingConfig {
  id: string;
  target_name: string;
  target_kind: string;
  min_replicas: number;
  max_replicas: number;
  metrics: unknown[];
}

export interface NetworkPolicy {
  id: string;
  name: string;
  namespace: string;
  pod_selector: Record<string, unknown>;
  ingress_rules: unknown[];
  egress_rules: unknown[];
}

// ─── Namespace & Cluster Types ─────────────────────────────────────────────────

export interface Namespace {
  id: string;
  name: string;
  workloads: Workload[];
  services: Service[];
  ingresses: Ingress[];
  configmaps: ConfigMap[];
  secrets: Secret[];
  pvcs: PVC[];
  autoscaling: AutoscalingConfig[];
  network_policies: NetworkPolicy[];
  labels: Record<string, string>;
  resource_quota?: Record<string, unknown>;
}

export interface NodeGroup {
  id: string;
  name: string;
  instance_type: string;
  min_nodes: number;
  max_nodes: number;
  desired_nodes: number;
  labels: Record<string, string>;
  taints: unknown[];
  disk_size?: number;
}

export interface ObservabilityStack {
  metrics_enabled: boolean;
  logging_enabled: boolean;
  tracing_enabled: boolean;
  metrics_provider?: string;
  logging_provider?: string;
  tracing_provider?: string;
  dashboards: unknown[];
  alerts: unknown[];
}

export interface Cluster {
  id: string;
  name: string;
  provider: string;
  kubernetes_version: string;
  namespaces: Namespace[];
  node_groups: NodeGroup[];
  observability?: ObservabilityStack;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  region?: string;
}

// ─── External & Cloud Types ────────────────────────────────────────────────────

export interface ExternalDependency {
  id: string;
  name: string;
  dependency_type: string;
  host?: string;
  port?: number;
  protocol?: string;
  description?: string;
  metadata: Record<string, unknown>;
}

export interface CloudResource {
  id: string;
  name: string;
  resource_type: string;
  provider: string;
  region?: string;
  properties: Record<string, unknown>;
  tags: Record<string, string>;
}

export interface TerraformResource {
  id: string;
  resource_type: string;
  name: string;
  provider: string;
  config: Record<string, unknown>;
  depends_on: string[];
}

export interface Edge {
  id: string;
  source_id: string;
  target_id: string;
  edge_type: string;
  label?: string;
  metadata: Record<string, unknown>;
}

// ─── Platform Model ────────────────────────────────────────────────────────────

export interface Platform {
  id: string;
  name: string;
  description: string;
  clusters: Cluster[];
  external_dependencies: ExternalDependency[];
  cloud_resources: CloudResource[];
  terraform_resources: TerraformResource[];
  edges: Edge[];
  environments: string[];
  gitops_tool: string;
  assumptions: string[];
  metadata: Record<string, unknown>;
}

// ─── Validation Types ──────────────────────────────────────────────────────────

export type IssueSeverity = 'error' | 'warning' | 'info' | 'assumption';

export interface ValidationIssue {
  severity: IssueSeverity;
  code: string;
  message: string;
  component_id?: string;
  component_name?: string;
  suggestion?: string;
}

export interface ValidationReport {
  passed: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  info: ValidationIssue[];
  assumptions: ValidationIssue[];
}

// ─── Generation Types ──────────────────────────────────────────────────────────

export interface GenerationOptions {
  generate_helm: boolean;
  generate_argocd: boolean;
  generate_terraform: boolean;
  generate_observability: boolean;
  generate_policies: boolean;
  environments: string[];
  gitops_tool: string;
  terraform_backend: string;
}

export interface GenerationRequest {
  platform: Platform;
  options: GenerationOptions;
}

export interface GeneratedFile {
  path: string;
  content: string;
  description: string;
}

export interface GenerationResult {
  platform_id: string;
  files: GeneratedFile[];
  validation: ValidationReport;
  assumptions: string[];
  warnings: string[];
}

// ─── API Response Types ────────────────────────────────────────────────────────

export interface ParseResponse {
  parsed: Platform;
  platform: string;
}
