#!/usr/bin/env bash
# Descarga las fuentes de léxico y alineamiento para el módulo v1.5 de Berea.
#
# Fuentes (todas redistribuibles bajo CC BY 4.0 o PD/CC0):
#   - STEPBible-Data: TAGNT, TAHOT, TBESG, TBESH, TFLSJ
#   - openscriptures/HebrewLexicon: BrownDriverBriggs.xml, LexicalIndex.xml
#   - openscriptures/strongs: strongs-greek-dictionary.js
#
# Estrategia: bajamos archivos individuales por HTTP (raw.githubusercontent.com)
# ancladados a commit SHA exacto. Más rápido y reproducible que `git clone`
# del repo entero STEPBible-Data (>500 MB de historial), y permite pinear
# versión por SHA para los releases del pipeline.
#
# Reproducibilidad: si una de estas SHA queda atrás respecto a upstream, el
# resultado del pipeline se sigue construyendo idéntico byte-a-byte. Para
# refrescar a la última versión upstream, actualizar las SHA aquí.

set -euo pipefail

# Pineamos commit SHA para reproducibilidad de releases del pipeline.
# Para actualizar: ver el último commit en cada repo y reemplazar.
STEPBIBLE_SHA="29897f468446297e78dbb317aaeca5f4ea4f4ca1"      # 2026-05-09
HEBLEX_SHA="21c9add13bc727d3a951361778e97e3ff7afd1ce"          # 2019-09-02 (stable)
STRONGS_SHA="0acd2f251c2d35ff8db2dece4e0593979d3ac223"         # 2021-07-15 (stable)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCES_DIR="${REPO_ROOT}/sources"

# Helper: bajar un archivo si no existe o si su SHA-256 difiere del esperado.
# Uso: fetch <url> <destino> [<sha256_esperado>]
fetch() {
  local url="$1"
  local dest="$2"
  local expected_sha="${3:-}"

  mkdir -p "$(dirname "${dest}")"

  if [[ -f "${dest}" && -n "${expected_sha}" ]]; then
    local current
    current="$(sha256sum "${dest}" | awk '{print $1}')"
    if [[ "${current}" == "${expected_sha}" ]]; then
      echo "  ✓ ${dest##${REPO_ROOT}/} (cached, sha ok)"
      return 0
    fi
    echo "  ⚠ ${dest##${REPO_ROOT}/} existe pero sha distinto; re-bajando"
  fi

  echo "  ↓ ${url}"
  curl -fsSL "${url}" -o "${dest}.tmp"
  mv "${dest}.tmp" "${dest}"

  if [[ -n "${expected_sha}" ]]; then
    local got
    got="$(sha256sum "${dest}" | awk '{print $1}')"
    if [[ "${got}" != "${expected_sha}" ]]; then
      echo "  ✗ SHA-256 mismatch en ${dest##${REPO_ROOT}/}" >&2
      echo "    esperado: ${expected_sha}" >&2
      echo "    obtenido: ${got}" >&2
      exit 1
    fi
  fi
}

echo "=== STEPBible-Data @ ${STEPBIBLE_SHA:0:8} ==="

# TAGNT — Translators Amalgamated Greek NT (palabra a palabra, NA/TR/SBL/...)
# Ya viene desde sesión previa (texto griego usado para Tregelles), pero lo
# refresheamos para que toda la dependencia STEPBible quede pinneada a un
# solo SHA conocido.
STEPBIBLE_RAW="https://raw.githubusercontent.com/STEPBible/STEPBible-Data/${STEPBIBLE_SHA}"

# OJO: TAGNT usa "CC-BY" (con guión), TAHOT y los lexicones usan "CC BY"
# (con espacio). Diferencia heredada del upstream.
fetch "${STEPBIBLE_RAW}/Translators%20Amalgamated%20OT%2BNT/TAGNT%20Mat-Jhn%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt" \
      "${SOURCES_DIR}/stepbible_tagnt/TAGNT_Mat-Jhn.txt" \
      "ab8eaaeb68e17a1dcfa34e1e9350358f22f03bc2a97244d848750ad81044bc8e"

fetch "${STEPBIBLE_RAW}/Translators%20Amalgamated%20OT%2BNT/TAGNT%20Act-Rev%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt" \
      "${SOURCES_DIR}/stepbible_tagnt/TAGNT_Act-Rev.txt" \
      "524e32375361e6d3fa2f7ef00b87605fdc4317a762f395651a05fdc31ad031b7"

# TAHOT — Translators Amalgamated Hebrew OT (palabra a palabra, MT con
# morfología). Upstream lo split en 4 archivos por sección del canon AT.
fetch "${STEPBIBLE_RAW}/Translators%20Amalgamated%20OT%2BNT/TAHOT%20Gen-Deu%20-%20Translators%20Amalgamated%20Hebrew%20OT%20-%20STEPBible.org%20CC%20BY.txt" \
      "${SOURCES_DIR}/stepbible_tahot/TAHOT_Gen-Deu.txt" \
      "e9b8546ee48fe0bfc57c3b70f5f40e98d96580e803526d19026224e31753368b"
fetch "${STEPBIBLE_RAW}/Translators%20Amalgamated%20OT%2BNT/TAHOT%20Jos-Est%20-%20Translators%20Amalgamated%20Hebrew%20OT%20-%20STEPBible.org%20CC%20BY.txt" \
      "${SOURCES_DIR}/stepbible_tahot/TAHOT_Jos-Est.txt" \
      "195fee1dc3653bab33701f170734eb894ed647c10cd08cc61749375fe8b73775"
fetch "${STEPBIBLE_RAW}/Translators%20Amalgamated%20OT%2BNT/TAHOT%20Job-Sng%20-%20Translators%20Amalgamated%20Hebrew%20OT%20-%20STEPBible.org%20CC%20BY.txt" \
      "${SOURCES_DIR}/stepbible_tahot/TAHOT_Job-Sng.txt" \
      "84e118a97e5725e3847cdfdd593873513021c790c63cc91a0d41fca2b5db2ed5"
fetch "${STEPBIBLE_RAW}/Translators%20Amalgamated%20OT%2BNT/TAHOT%20Isa-Mal%20-%20Translators%20Amalgamated%20Hebrew%20OT%20-%20STEPBible.org%20CC%20BY.txt" \
      "${SOURCES_DIR}/stepbible_tahot/TAHOT_Isa-Mal.txt" \
      "f3ded203d2a74d6368932c97ae550d1d0754b271af491dc0dedf36fe3ba0bcc5"

# TBESG — Translators Brief lexicon of Extended Strongs for Greek
fetch "${STEPBIBLE_RAW}/Lexicons/TBESG%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Greek%20-%20STEPBible.org%20CC%20BY.txt" \
      "${SOURCES_DIR}/stepbible_lexicon/TBESG.txt" \
      "312f723d7b8ef263bbdfb0451c9b8057125804dfff390b6f8544cff2a84b57f4"

# TBESH — Translators Brief lexicon of Extended Strongs for Hebrew
fetch "${STEPBIBLE_RAW}/Lexicons/TBESH%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Hebrew%20-%20STEPBible.org%20CC%20BY.txt" \
      "${SOURCES_DIR}/stepbible_lexicon/TBESH.txt" \
      "464dccadd95fd8620dd05fa0d7a4caba58ec3c4d5db3ebf38e43d046ca25b591"

# TFLSJ — Translators Formatted Full LSJ Bible Lexicon (split en 2 archivos:
# rangos 0-5624 y "extra" para Strong's > 5624 + variantes no-Strong's)
fetch "${STEPBIBLE_RAW}/Lexicons/TFLSJ%20%200-5624%20-%20Translators%20Formatted%20full%20LSJ%20Bible%20lexicon%20-%20STEPBible.org%20CC%20BY.txt" \
      "${SOURCES_DIR}/stepbible_lexicon/TFLSJ_0-5624.txt" \
      "fcc2845412132a7bb91fc3dbb5a544c807daf57e4791c4d9af61efe209e97691"

fetch "${STEPBIBLE_RAW}/Lexicons/TFLSJ%20extra%20-%20Translators%20Formatted%20full%20LSJ%20Bible%20lexicon%20-%20STEPBible.org%20CC%20BY.txt" \
      "${SOURCES_DIR}/stepbible_lexicon/TFLSJ_extra.txt" \
      "fdb2840067faa11301b208a343a9453fbe40b367e94eac981071261626201bc2"

echo "=== openscriptures/HebrewLexicon @ ${HEBLEX_SHA:0:8} ==="
HEBLEX_RAW="https://raw.githubusercontent.com/openscriptures/HebrewLexicon/${HEBLEX_SHA}"

fetch "${HEBLEX_RAW}/BrownDriverBriggs.xml" \
      "${SOURCES_DIR}/openscriptures_hebrew/BrownDriverBriggs.xml" \
      "2b52658a4323d91674cda4090ab8b3ebddfff640f4f18143c28300e80b2c38f8"
fetch "${HEBLEX_RAW}/LexicalIndex.xml" \
      "${SOURCES_DIR}/openscriptures_hebrew/LexicalIndex.xml" \
      "8f7a605c58899d2f44430149c143c00903976e1e91232476677972a69e5bc85f"
fetch "${HEBLEX_RAW}/AugIndex.xml" \
      "${SOURCES_DIR}/openscriptures_hebrew/AugIndex.xml" \
      "e7217ca8ff8ff3f21f9cf1bbe87411adf55f6aa88bcf5ed9ddc886cc6b160c5d"
fetch "${HEBLEX_RAW}/HebrewStrong.xml" \
      "${SOURCES_DIR}/openscriptures_hebrew/HebrewStrong.xml" \
      "a628f4f89f8bdaf2483fd3faf1abc8653cc6717758dfc9f24beb7571d9bdd0c4"

echo "=== openscriptures/strongs @ ${STRONGS_SHA:0:8} ==="
STRONGS_RAW="https://raw.githubusercontent.com/openscriptures/strongs/${STRONGS_SHA}"

fetch "${STRONGS_RAW}/greek/strongs-greek-dictionary.js" \
      "${SOURCES_DIR}/openscriptures_greek/strongs-greek-dictionary.js" \
      "7624ee738ae47e80f1a352223e28a26d011c9cd4898822cee52f47a010c04efd"

echo ""
echo "Descarga completa. Fuentes en ${SOURCES_DIR##${REPO_ROOT}/}/{stepbible_*,openscriptures_*}."
