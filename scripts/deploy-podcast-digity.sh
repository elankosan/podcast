#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

cd "${PROJECT_DIR}"

if [[ ! -f .env ]]; then
  if [[ -f .env.podcast.digity.dev.example ]]; then
    cp .env.podcast.digity.dev.example .env
    echo "Created .env from .env.podcast.digity.dev.example"
    echo "Update .env with real secrets before deploying."
    exit 1
  else
    echo "Missing .env and .env.podcast.digity.dev.example"
    exit 1
  fi
fi

bash scripts/deploy-existing-infra.sh
