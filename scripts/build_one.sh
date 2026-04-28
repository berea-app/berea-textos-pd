#!/usr/bin/env bash
# Build a single Bible by id.
# Usage: ./scripts/build_one.sh rv1909
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <bible_id>" >&2
  exit 2
fi

python3 -m pipeline.cli build --bible "$1"
