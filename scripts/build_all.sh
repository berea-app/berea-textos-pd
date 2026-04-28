#!/usr/bin/env bash
# Build every Bible in the catalogue.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m pipeline.cli build --all
