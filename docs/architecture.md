# KubeBlueprint Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                            │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌───────────────────┐  │
│  │ Diagram      │   │ Architecture │   │ Generate /        │  │
│  │ Upload Page  │→  │ Graph Editor │→  │ Preview Page      │  │
│  └──────────────┘   └──────────────┘   └───────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ REST (JSON / multipart)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend                           │
│                                                                 │
│  ┌───────────┐  ┌───────────────┐  ┌──────────────────────┐   │
│  │ Parsers   │→ │ Inference     │→ │ Validators           │   │
│  │           │  │ Engine        │  │                      │   │
│  │ - draw.io │  │               │  │ - Workload rules     │   │
│  │ - Excali. │  │ Classify →    │  │ - Networking rules   │   │
│  │ - Mermaid │  │ Build cluster │  │ - Storage rules      │   │
│  │ - Image   │  │ Build ns      │  │ - Security rules     │   │
│  └───────────┘  └───────────────┘  └──────────────────────┘   │
│                                           │                     │
│                                           ▼                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Generators                             │  │
│  │  ┌──────────┐ ┌──────┐ ┌────────┐ ┌───────┐ ┌────────┐  │  │
│  │  │Kubernetes│ │ Helm │ │ArgoCD  │ │Terraform│ │Obs.   │  │  │
│  │  └──────────┘ └──────┘ └────────┘ └───────┘ └────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────┐                       │
│  │ Export Layer (zip / git)             │                       │
│  └──────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. User uploads diagram (PNG / draw.io / Excalidraw / Mermaid)
2. Parser converts raw bytes → ParsedDiagram (nodes, edges)
3. InferenceEngine converts ParsedDiagram → Platform (canonical model)
4. User reviews and edits the Platform in the graph editor
5. ValidationEngine checks the Platform and emits a ValidationReport
6. Generators read the Platform and produce GeneratedFile[]
7. Export layer zips all GeneratedFile entries into a downloadable archive
```

## Canonical Model

The `Platform` model is the single source of truth between all subsystems:

```
Platform
 └── Cluster[]
      ├── Namespace[]
      │    ├── Workload[]          (Deployment / StatefulSet / DaemonSet / Job / CronJob)
      │    ├── Service[]
      │    ├── Ingress[]
      │    ├── Gateway[]
      │    ├── ConfigMap[]
      │    ├── Secret[]
      │    ├── PersistentVolumeClaim[]
      │    ├── AutoscalingConfig[]
      │    └── NetworkPolicy[]
      ├── NodeGroup[]
      ├── StorageClass[]
      └── ObservabilityStack
 ├── TerraformResource[]
 ├── CloudResource[]
 ├── ExternalDependency[]
 └── Edge[]
```

## Classifier Rules

Component classification is rule-based (fast, deterministic, no ML required):

| Priority | Source | Example | Result |
|---|---|---|---|
| 1 | Explicit tags | `tags: ["namespace"]` | NAMESPACE |
| 2 | Node shape | `shape: "cylinder"` | STATEFULSET |
| 3 | Label patterns | `"postgres"` | STATEFULSET |
| 4 | Child count | node has 5+ children | NAMESPACE |
| 5 | Fallback | anything else | UNKNOWN |

## Extension Points

### Adding a new diagram format

1. Create `backend/app/parsers/<format>.py` implementing `BaseParser`.
2. Register it in `backend/app/parsers/__init__.py → get_parser()`.
3. Add the format to the `DiagramFormat` enum in `models/diagram.py`.

### Adding a new generator

1. Create `backend/app/generators/<name>.py` implementing `BaseGenerator`.
2. Instantiate it in `backend/app/api/generate.py`.

### Adding a new cloud provider (Terraform)

1. Add a branch in `TerraformGenerator._gen_main()` and `_required_providers()`.
2. Add a new module directory under `terraform/modules/`.

### Adding a new validation rule

1. Create a rule class in `backend/app/validators/rules/`.
2. Register it in `ValidationEngine.__init__()`.
