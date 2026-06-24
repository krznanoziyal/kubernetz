#!/usr/bin/env bash
# Usage: ./scripts/parse-diagram.sh <path-to-diagram-file> [platform-name]
# Sends the diagram to the KubeBlueprint API and prints the inferred platform.

set -euo pipefail

DIAGRAM_FILE="${1:?Usage: $0 <diagram-file> [name]}"
PLATFORM_NAME="${2:-platform}"
API_URL="${KUBEBLUEPRINT_URL:-http://localhost:8000}"

if [[ ! -f "$DIAGRAM_FILE" ]]; then
  echo "Error: file not found: $DIAGRAM_FILE" >&2
  exit 1
fi

echo "Parsing: $DIAGRAM_FILE"
curl -s -X POST "$API_URL/api/v1/diagram/parse" \
  -F "file=@$DIAGRAM_FILE" \
  -F "name=$PLATFORM_NAME" \
  | python3 -m json.tool
