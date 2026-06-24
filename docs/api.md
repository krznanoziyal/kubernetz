# KubeBlueprint API Reference

Base URL: `http://localhost:8000/api/v1`

## Health Check

```
GET /health
```
Returns `{ "status": "ok", "version": "0.1.0" }`.

---

## Diagram Endpoints

### Parse a diagram file

```
POST /diagram/parse
Content-Type: multipart/form-data

Fields:
  file   (required) — diagram file: .xml, .drawio, .excalidraw, .png, .jpg, .svg
  name   (optional) — platform name override
  notes  (optional) — extra context passed to the inference engine
```

**Response**
```json
{
  "parsed": {
    "source_format": "drawio",
    "nodes": [...],
    "edges": [...],
    "parser_notes": [...]
  },
  "platform": { ... }
}
```

### Parse Mermaid text

```
POST /diagram/mermaid
Content-Type: application/json

{
  "text": "graph TD\n  api --> db",
  "name": "my-platform"
}
```

**Response** — same shape as `/diagram/parse`.

---

## Architecture Endpoints

### Validate a platform model

```
POST /architecture/validate
Content-Type: application/json

Body: Platform JSON object
```

**Response**
```json
{
  "passed": true,
  "errors": [],
  "warnings": [
    {
      "severity": "warning",
      "code": "W002",
      "message": "Workload 'api' uses :latest image tag",
      "component_id": "...",
      "component_name": "api",
      "suggestion": "Pin the image to a specific digest or semver tag.",
      "auto_fixable": true
    }
  ],
  "info": [],
  "assumptions": []
}
```

### Update platform model

```
PUT /architecture/
Content-Type: application/json

Body: Platform JSON object
```

**Response** — Echo of the submitted platform (useful for round-trip validation).

---

## Generation Endpoint

```
POST /generate/
Content-Type: application/json

{
  "platform": { ... Platform ... },
  "environments": ["dev", "staging", "prod"],
  "generate_helm": true,
  "generate_argocd": true,
  "generate_terraform": true,
  "generate_observability": true,
  "generate_policies": true,
  "gitops_tool": "argocd",
  "terraform_backend": "s3"
}
```

**Response**
```json
{
  "platform_id": "...",
  "files": [
    {
      "path": "k8s/base/default/api-server.yaml",
      "content": "apiVersion: apps/v1\n...",
      "description": "Deployment api-server"
    }
  ],
  "validation": { "passed": true, "errors": [], "warnings": [...] },
  "assumptions": ["Generated default VPC + EKS Terraform resources"],
  "warnings": []
}
```

---

## Export Endpoint

```
POST /export/zip
Content-Type: application/json

Body: same as /generate/
```

**Response** — `application/zip` binary stream.
Filename: `<platform-name>-blueprint.zip`.

---

## Error Responses

| Code | Meaning |
|---|---|
| 400 | Bad request (missing required field) |
| 413 | File too large (>20 MB by default) |
| 422 | Could not parse diagram or invalid model |
| 500 | Internal server error |

All errors return `{ "detail": "human-readable message" }`.
