#!/usr/bin/env bash
# Tag the current commit and trigger the release workflow on GitHub.
# Usage: ./scripts/make_release.sh v0.1.0
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <tag>  (e.g. v0.1.0)" >&2
  exit 2
fi

TAG="$1"
git tag -a "$TAG" -m "Release $TAG"
git push origin "$TAG"
echo "Pushed tag $TAG. The release workflow will build artifacts and publish them."
