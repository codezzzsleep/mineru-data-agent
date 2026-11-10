#!/usr/bin/env bash
# Publish the committed static website with a regular, history-preserving push.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "$#" -gt 1 || ( "$#" -eq 1 && "$1" != "--dry-run" ) ]]; then
  echo "Usage: bash scripts/publish_pages.sh [--dry-run]" >&2
  exit 2
fi
if [[ -n "$(git status --porcelain -- site)" ]]; then
  echo "Commit the website before publishing; deployment is built from HEAD." >&2
  exit 1
fi
for file in index.html style.css app.js favicon.svg .nojekyll assets/document-harness.svg assets/defense-demo.mp4 assets/demo-poster.webp assets/social-card.png; do
  git cat-file -e "HEAD:site/$file"
done
site_revision=$(git subtree split --prefix=site HEAD)
if [[ "${1:-}" == "--dry-run" ]]; then
  git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push --dry-run origin "$site_revision:refs/heads/gh-pages"
else
  git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push origin "$site_revision:refs/heads/gh-pages"
fi
