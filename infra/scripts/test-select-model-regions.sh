#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SOURCE_UNDER_TEST="$(mktemp)"
trap 'rm -f "$SOURCE_UNDER_TEST"' EXIT
sed '/^main "\$@"/d' "$SCRIPT_DIR/select-model-regions.sh" > "$SOURCE_UNDER_TEST"
source "$SOURCE_UNDER_TEST"

azd() {
    if [ "$1" = "env" ] && [ "$2" = "get-values" ]; then
        cat <<'EOF'
AZURE_RESOURCE_GROUP="rg-test"
EOF
        return 0
    fi
    return 1
}

az() {
    if [ "$1" = "cognitiveservices" ] && [ "$2" = "model" ] && [ "$3" = "list" ]; then
        printf '%s\n' "OpenAI.gpt-4.1.2025-04-14"
        return 0
    fi

    if [ "$1" = "cognitiveservices" ] && [ "$2" = "usage" ] && [ "$3" = "list" ]; then
        cat <<'EOF'
[
  {
    "currentValue": 500,
    "limit": 500,
    "name": {
      "value": "OpenAI.GlobalStandard.gpt-4.1"
    }
  }
]
EOF
        return 0
    fi

    if [ "$1" = "cognitiveservices" ] && [ "$2" = "account" ] && [ "$3" = "list" ]; then
        printf '%s\n' "ai-primary-test"
        return 0
    fi

    if [ "$1" = "cognitiveservices" ] && [ "$2" = "account" ] && [ "$3" = "deployment" ] && [ "$4" = "list" ]; then
        cat <<'EOF'
[
  {
    "name": "gpt-4.1",
    "properties": {
      "model": {
        "name": "gpt-4.1"
      },
      "provisioningState": "Succeeded"
    },
    "sku": {
      "capacity": 500
    }
  }
]
EOF
        return 0
    fi

    return 1
}

if ! region_satisfies_model_requirement "swedencentral" "gpt-4.1" 500; then
    echo "Expected existing deployment capacity to satisfy selected-region validation" >&2
    exit 1
fi

echo "select-model-regions regression tests passed"
