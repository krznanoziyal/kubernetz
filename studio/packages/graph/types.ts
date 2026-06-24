/**
 * Kube Architect Studio — Canonical Graph Model
 *
 * The Graph is the ONLY source of truth.
 * All generators, validators, and cost estimators consume ONLY the Graph.
 * The Canvas (React Flow) is a view of the Graph, not the source.
 */

// ─── Primitive types ──────────────────────────────────────────────────────────

export type NodeId = string;
export type EdgeId = string;

export type ComponentCategory =
  | "workload"
  | "service"
  | "networking"
  | "gateway-api"
  | "configuration"
  | "storage"
  | "security"
  | "autoscaling"
  | "policy"
  | "observability"
  | "database"
  | "messaging"
  | "gitops"
  | "cloud-aws"
  | "cloud-gcp"
  | "cloud-azure"
  | "service-mesh"
  | "ci-cd"
  | "addon"
  | "namespace"
  | "cluster"
  | "external";

export type EdgeRelationship =
  | "traffic"        // Ingress → Service → Workload
  | "dependency"     // Backend → Database
  | "monitoring"     // Prometheus → Service
  | "security"       // Cert → Ingress, Vault → Workload
  | "gitops"         // ArgoCD → Namespace
  | "storage"        // PVC → StatefulSet
  | "dns"            // ExternalDNS → Service
  | "scaling"        // HPA → Deployment
  | "ownership"      // Namespace owns workloads
  | "replication"    // Primary → Replica
  | "custom";

export type ValidationSeverity = "error" | "warning" | "suggestion";

// ─── Validation ───────────────────────────────────────────────────────────────

export interface ValidationIssue {
  id: string;
  nodeId?: NodeId;
  edgeId?: EdgeId;
  severity: ValidationSeverity;
  code: string;
  title: string;
  message: string;
  suggestion?: string;
  documentationUrl?: string;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
  score: ArchitectureScore;
}

// ─── Architecture scoring ─────────────────────────────────────────────────────

export interface ArchitectureScore {
  overall: number;       // 0–100
  security: number;
  reliability: number;
  scalability: number;
  costEfficiency: number;
  operationalComplexity: number;
  breakdown: ScoreBreakdown[];
}

export interface ScoreBreakdown {
  category: string;
  score: number;
  maxScore: number;
  notes: string[];
}

// ─── Cost estimation ──────────────────────────────────────────────────────────

export interface CostEstimate {
  provider: "aws" | "gcp" | "azure";
  monthly: number;
  breakdown: CostLineItem[];
  currency: string;
}

export interface CostLineItem {
  nodeId: NodeId;
  componentName: string;
  resourceType: string;
  monthlyCost: number;
  details: string;
}

// ─── Graph nodes ──────────────────────────────────────────────────────────────

export interface NodePosition {
  x: number;
  y: number;
}

export interface NodeDimensions {
  width: number;
  height: number;
}

export interface NodeConfig {
  [key: string]: unknown;
}

export interface GraphNode {
  id: NodeId;
  componentId: string;       // references ComponentDefinition.id
  name: string;              // user-defined resource name
  position: NodePosition;
  dimensions?: NodeDimensions;
  parentId?: NodeId;         // for nodes nested inside Namespace/Cluster
  config: NodeConfig;        // matches the component's JSON Schema
  tags: string[];
  annotations: Record<string, string>;
  namespace?: string;        // resolved namespace name
  environments?: EnvironmentOverride[];
}

export interface EnvironmentOverride {
  environment: "dev" | "staging" | "prod" | string;
  config: Partial<NodeConfig>;
}

// ─── Graph edges ──────────────────────────────────────────────────────────────

export interface GraphEdge {
  id: EdgeId;
  source: NodeId;
  target: NodeId;
  sourceHandle?: string;
  targetHandle?: string;
  relationship: EdgeRelationship;
  label?: string;
  config?: Record<string, unknown>;
}

// ─── Graph metadata ───────────────────────────────────────────────────────────

export interface GraphMetadata {
  name: string;
  description: string;
  version: string;
  schemaVersion: "1.0";
  createdAt: string;
  updatedAt: string;
  author?: string;
  tags: string[];
  environments: string[];
  targetProvider: "aws" | "gcp" | "azure" | "generic";
  gitopsBackend: "argocd" | "flux" | "none";
  terraformBackend: "s3" | "gcs" | "azurerm" | "local";
  clusterName: string;
}

// ─── Root graph ───────────────────────────────────────────────────────────────

export interface Graph {
  metadata: GraphMetadata;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ─── Canvas state (React Flow view state, NOT graph state) ───────────────────

export interface CanvasViewport {
  x: number;
  y: number;
  zoom: number;
}

export interface CanvasState {
  viewport: CanvasViewport;
  selectedNodeIds: NodeId[];
  selectedEdgeIds: EdgeId[];
}

// ─── Saved project ───────────────────────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  description: string;
  graph: Graph;
  canvasState: CanvasState;
  thumbnail?: string;
  createdAt: string;
  updatedAt: string;
  version: number;
}

// ─── Generator output ────────────────────────────────────────────────────────

export type GeneratorType =
  | "kubernetes"
  | "helm"
  | "argocd"
  | "flux"
  | "terraform"
  | "monitoring"
  | "security"
  | "documentation";

export interface GeneratedFile {
  path: string;
  content: string;
  generator: GeneratorType;
  description?: string;
  language?: string;
}

export interface GenerationOptions {
  generators: GeneratorType[];
  environments: string[];
  gitopsBackend: "argocd" | "flux" | "none";
  terraformBackend: string;
  targetProvider: string;
  outputFormat: "zip" | "git" | "inline";
  helmRepoUrl?: string;
}

export interface GenerationResult {
  files: GeneratedFile[];
  warnings: string[];
  stats: {
    totalFiles: number;
    byGenerator: Record<GeneratorType, number>;
  };
}
