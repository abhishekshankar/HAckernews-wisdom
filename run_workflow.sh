#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install with: brew install gh" >&2
  exit 1
fi

if ! gh auth status -h github.com >/dev/null 2>&1; then
  echo "gh not authenticated. Run: gh auth login" >&2
  exit 1
fi

echo "Triggering GitHub Actions workflow 'Daily HN Scrape'..."
gh workflow run "Daily HN Scrape" --repo abhishekshankar/HAckernews-wisdom

echo "Latest runs:"
gh run list --repo abhishekshankar/HAckernews-wisdom --limit 3
