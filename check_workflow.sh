#!/usr/bin/env bash
set -euo pipefail

REPO="abhishekshankar/HAckernews-wisdom"
WORKFLOW_NAME="Daily HN Scrape"
POLL_SECONDS=10
MAX_POLLS=30

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install with: brew install gh" >&2
  exit 1
fi

if ! gh auth status -h github.com >/dev/null 2>&1; then
  echo "gh not authenticated. Run: gh auth login" >&2
  exit 1
fi

echo "Waiting for latest run of '$WORKFLOW_NAME' to finish..."

run_id=""
for _ in $(seq 1 "$MAX_POLLS"); do
  run_id=$(gh run list --repo "$REPO" --workflow "$WORKFLOW_NAME" --limit 1 --json databaseId,status,conclusion -q '.[0].databaseId')
  status=$(gh run list --repo "$REPO" --workflow "$WORKFLOW_NAME" --limit 1 --json status -q '.[0].status')
  if [[ "$status" == "completed" ]]; then
    break
  fi
  sleep "$POLL_SECONDS"
done

if [[ -z "$run_id" ]]; then
  echo "No runs found." >&2
  exit 1
fi

echo "Latest run id: $run_id"

gh run view "$run_id" --repo "$REPO" --log
