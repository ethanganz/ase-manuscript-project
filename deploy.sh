#!/usr/bin/env bash
# Deploy the stack on the server.
#
# Usage: ./deploy.sh
#
# Selects image tags in this order:
#   1. Server-local .env (next to docker-compose.yml) — the normal way to pin
#      or change the deployed image from the server.
#   2. */docker/IMAGE_VERSION — fallback when .env doesn't set the variable.
# With neither set, docker-compose.yml falls back to :latest.
#
# Pulls the latest repo state first, then pulls and restarts the stack.
set -euo pipefail
cd "$(dirname "$0")"

git pull --ff-only

# Resolve a tag: value from .env if set, otherwise contents of the given file.
resolve_version() {
  local var="$1" file="$2" value=""
  if [ -f .env ]; then
    value="$(sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?${var}[[:space:]]*=[[:space:]]*//p" .env | tail -n 1)"
    value="${value%%#*}"
    value="$(printf '%s' "$value" | tr -d '[:space:]' | sed -E 's/^"(.*)"$/\1/; s/^'"'"'(.*)'"'"'$/\1/')"
  fi
  if [ -n "$value" ]; then
    printf '%s\n' "$value"
  else
    tr -d '[:space:]' < "$file"
  fi
}

export BACKEND_IMAGE_VERSION
BACKEND_IMAGE_VERSION="$(resolve_version BACKEND_IMAGE_VERSION backend/docker/IMAGE_VERSION)"
export FRONTEND_IMAGE_VERSION
FRONTEND_IMAGE_VERSION="$(resolve_version FRONTEND_IMAGE_VERSION frontend/docker/IMAGE_VERSION)"

echo "Deploying backend:${BACKEND_IMAGE_VERSION} frontend:${FRONTEND_IMAGE_VERSION}"

docker compose pull
docker compose up -d
