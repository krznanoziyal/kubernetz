# Supported Diagram Formats

## draw.io / diagrams.net

Export from diagrams.net as **XML** (File → Export → XML) or as a **PNG** (which embeds the XML in metadata and is parsed separately).

**Tips for better inference:**
- Use the built-in Kubernetes shape library (Extras → Edit Diagram → load k8s shape library).
- Group related components using swimlanes or frames — these become namespaces.
- Label groups explicitly (e.g., "default namespace", "monitoring").
- Use cylinder shapes for databases/stateful stores.
- Draw arrows between components to represent network connections.

**Example component mappings:**

| draw.io shape | Inferred type |
|---|---|
| Rectangle (dashed border) | Namespace |
| Rectangle labeled "postgres" | StatefulSet |
| Cylinder | StatefulSet |
| Rounded rectangle | Deployment |
| Cloud shape | External dependency / Cloud resource |
| Arrow | Edge / network connection |

---

## Excalidraw

Export as `.excalidraw` JSON (Export → Excalidraw file).

**Tips:**
- Nest shapes to indicate containment (rectangle inside rectangle = workload inside namespace).
- Use frame elements to group related components.
- Add text labels to all shapes — the text is used for classification.
- Color coding is respected: blue shapes are treated as core workloads, orange as stateful.

---

## Mermaid

Paste Mermaid text directly into the "Mermaid" tab of the editor.

Supported diagram types:
- `graph TD / LR / BT / RL`
- `flowchart TD / LR`

**Example:**

```mermaid
graph TD
    subgraph cluster[EKS Cluster]
        subgraph default[default namespace]
            api[api-server]
            db[(postgres)]
            redis[(redis cache)]
        end
        subgraph monitoring[monitoring]
            prom[prometheus]
            grafana[grafana]
        end
    end
    internet((Internet)) -->|HTTPS| ingress[nginx ingress]
    ingress --> api
    api -->|SQL| db
    api -->|cache| redis
    prom --> api
    grafana --> prom
```

**Classification keywords in labels:**
- `postgres`, `mysql`, `mongodb`, `redis`, `kafka` → StatefulSet
- `nginx`, `traefik`, `ingress` → Ingress
- `prometheus`, `grafana`, `alertmanager` → Monitoring
- `loki`, `fluentd`, `fluentbit` → Logging
- `namespace`, `ns` → Namespace
- `eks`, `gke`, `aks`, `cluster`, `kubernetes` → Cluster
- `s3`, `rds`, `gcs`, `azure`, `aws` → Cloud resource

---

## PNG / JPG Images

Upload any PNG or JPG diagram. The system uses Claude's vision API to extract components and connections.

**Requirements:** `ANTHROPIC_API_KEY` must be set in `.env`.

**What the vision parser extracts:**
- All visible shapes → nodes
- All visible arrows/connections → edges
- Shape labels → used for classification
- Grouping/nesting → namespace / cluster boundaries
- Shape colors and styles → additional hints

**Limitations:**
- Quality depends on image resolution and label legibility.
- Handwritten or freehand diagrams may produce lower accuracy.
- Always review the inferred graph before generating.
