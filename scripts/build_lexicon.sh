#!/usr/bin/env bash
# Construye los 3 archivos .bb del módulo de léxico v1.5:
#
#   lexicon_grc.bb       — griego default (TBESG + Strong's), ~1.8 MB
#   lexicon_grc_lsj.bb   — griego LSJ completo (avanzado), ~7.6 MB
#   lexicon_hbo.bb       — hebreo (TBESH + BDB), ~1.2 MB
#
# Pre-requisitos: las fuentes descargadas en sources/ vía
# scripts/download_stepbible.sh. Si faltan, el build falla con error claro.
#
# Para un solo target: ``./scripts/build_lexicon.sh lexicon_grc``.
# Output va a output/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"
exec python3 -m pipeline.lexicon.build "$@"
