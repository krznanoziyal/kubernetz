#!/usr/bin/env bash
# Usage: ./scripts/generate-from-mermaid.sh <mermaid-file> [platform-name] [output-dir]
# Parses a Mermaid diagram, generates the full project, and unzips it.

set -euo pipefail

MERMAID_FILE="${1:?Usage: $0 <mermaid-file> [name] [output-dir]}"
PLATFORM_NAME="${2:-platform}"
OUTPUT_DIR="${3:-./${PLATFORM_NAME}-generated}"
API_URL="${KUBEBLUEPRINT_URL:-http://localhost:8000}"

if [[ ! -f "$MERMAID_FILE" ]]; then
  echo "Error: file not found: $MERMAID_FILE" >&2
  exit 1
fi

echo "Step 1: Parsing Mermaid diagram..."
MERMAID_TEXT=$(cat "$MERMAID_FILE")

PARSE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/diagram/mermaid" \
  -H "Content-Type: application/json" \
  -d "{\"text\": $(echo "$MERMAID_TEXT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'), \"name\": \"$PLATFORM_NAME\"}")

PLATFORM=$(echo "$PARSE_RESPONSE" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['platform']))")

echo "Step 2: Generating project files..."
GENERATE_REQUEST=$(python3 -c "
import json, sys
platform = json.loads(sys.argv[1])
req = {
  'platform': platform,
  'environments': ['dev', 'staging', 'prod'],
  'generate_helm': True,
  'generate_argocd': True,
  'generate_terraform': True,
  'generate_observability': True,
  'gitops_tool': 'argocd',
  'terraform_backend': 's3'
}
print(json.dumps(req))
" "$PLATFORM")

echo "Step 3: Downloading zip..."
mkdir -p "$OUTPUT_DIR"
curl -s -X POST "$API_URL/api/v1/export/zip" \
  -H "Content-Type: application/json" \
  -d "$GENERATE_REQUEST" \
  -o "/tmp/${PLATFORM_NAME}-blueprint.zip"

echo "Step 4: Extracting to $OUTPUT_DIR..."
unzip -q "/tmp/${PLATFORM_NAME}-blueprint.zip" -d "$OUTPUT_DIR"
rm "/tmp/${PLATFORM_NAME}-blueprint.zip"

echo ""
echo "Done! Project generated at: $OUTPUT_DIR"
echo ""
ls "$OUTPUT_DIR"
