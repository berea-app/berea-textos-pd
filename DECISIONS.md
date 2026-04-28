# Decisiones (editoriales y técnicas)

Bitácora de decisiones tomadas en el repo. Cada entrada incluye fecha, contexto,
opciones consideradas, y la elección. Formato Spanish-first porque captura el
razonamiento del autor.

---

## D-001 · Stack: Python 3.11 + `pip` + `pyproject.toml`

**Fecha:** 2026-04-28
**Contexto:** El Documento 3 sugiere `uv` o `pip-tools`. Hay que elegir uno.
**Opciones:**
- `uv` — más rápido, lockfile reproducible, todavía relativamente nuevo.
- `pip-tools` — maduro, integrado con `pip`, lockfile vía `requirements.txt`.
- `pip` puro con `pyproject.toml` y extras `[dev]`.
**Elegido:** **`pip` + `pyproject.toml`**.
**Justificación:** Las dependencias del pipeline son pocas y todas estables
(`requests`, `lxml`, `beautifulsoup4`, `pyyaml`, `pytest`). Para tres
dependencias no necesitamos un lockfile sofisticado; una versión pinneada
mínima en `pyproject.toml` y la imagen de CI (Python 3.11 estable) bastan
para reproducibilidad. Si en el futuro el pipeline crece (ej. embeddings con
`sentence-transformers`), migramos a `uv` con `uv.lock` sin perder nada.

---

## D-002 · Formato `.bb`: JSON + gzip

**Fecha:** 2026-04-28
**Contexto:** Hay que congelar el formato del archivo distribuido.
**Opciones:**
- JSON crudo: legible, debuggeable, ~6 MB por Biblia.
- JSON + gzip: compresión 3-4×, sigue siendo trivial de inspeccionar
  (`gunzip < rv1909.bb | jq .books[0]`).
- SQLite parcial: la app importa a SQLite igual; saltearíamos un paso, pero
  rompemos inspectabilidad y la verificación de integridad hash queda atada
  al binario SQLite (no determinístico entre versiones).
- MessagePack/Protobuf: más rápido de parsear, pero opaco para auditoría
  y sin ganancia de tamaño tras gzip.
**Elegido:** **JSON UTF-8 + gzip nivel 9**, extensión `.bb`.
**Justificación:** La app importa a SQLite una sola vez por Biblia; el costo
de parseo JSON pasa desapercibido frente al I/O de la base. La auditabilidad
y reproducibilidad valen más que los milisegundos. Tamaños esperados:
RV 1909 ~5.5 MB JSON → ~1.8 MB `.bb`.

Para que dos builds del mismo commit produzcan bytes idénticos:
- Claves del JSON ordenadas alfabéticamente (`json.dumps(..., sort_keys=True)`).
- `gzip` con `mtime=0` (suprime el timestamp en el header).
- Sin trailing newline. Encoding UTF-8 sin BOM.

Especificación completa: [`docs/format_bb.md`](docs/format_bb.md).

---

## D-003 · Reproducibilidad determinística

**Fecha:** 2026-04-28
**Contexto:** La promesa central del repo es "dos clones producen los mismos
SHA-256". Hay varias fuentes de no-determinismo a controlar.
**Decisiones:**
- `json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",", ":"))`.
- `gzip.GzipFile(..., mtime=0)` siempre.
- Archivos descargados a `sources/` se cachean por SHA-256, no por timestamp.
- Si una fuente externa cambia, el SHA-256 de `sources/<archivo>` cambia y
  el pipeline aborta con un mensaje claro: "fuente upstream cambió, revisar
  manualmente". No se rebuilda silenciosamente.
- En CI corremos el pipeline dos veces y verificamos hashes idénticos.

---

## D-004 · Identificadores de libros: USFM 3.0 lowercase

**Fecha:** 2026-04-28
**Contexto:** Hay que congelar los `book_id` y compatibilidad con OSHB,
STEPBible, Paratext, etc.
**Elegido:** USFM 3.0 lowercase (`gen`, `exo`, `psa`, `mat`, `rev`, etc.).
**Justificación:** Es el estándar industrial (Paratext lo emite, OSHB lo
consume, STEPBible lo expone). El canon ya está congelado en
`canon/canon_66.json` y `canon/canon_extendido.json`, copiados desde la app
para que ambas partes (repo PD ↔ app) compartan ground truth.

Adiciones a Daniel y Ester se distribuyen como `book_id` separados (`sus`,
`bel`, `s3y`, `lje`, `esg`) con `parent_book_id` apuntando al libro base.
La numeración divergente entre LXX y MT (Salmos 9-147) se resuelve vía
`canon/verse_alias_lxx.json`, generado en el pipeline.

---

## D-005 · RV 1909: fuente y edición

**Fecha:** 2026-04-28
**Contexto:** El Documento 3 sugería `spavbl` de ebible.org, pero esa es la
"Versión Biblia Libre" (CC-BY-SA 4.0, no PD). El ID correcto de Reina-Valera
1909 en ebible es `spaRV1909`.
**Elegido:** `https://ebible.org/Scriptures/spaRV1909_usfm.zip`.
**Estatus legal:** dominio público declarado en la página de la fuente.
RV 1909 es una revisión de la traducción de Reina (1569) y Valera (1602);
sus autores murieron hace siglos y la edición de 1909 está libre de derechos
en cualquier jurisdicción razonable.
**Atribución mínima:** "Reina-Valera 1909, dominio público. Distribución vía
ebible.org."

---

## D-006 · Regla legal: vida + 95

**Fecha:** 2026-04-28
**Contexto:** Argentina aplica vida + 70 (Ley 11.723), Estados Unidos vida + 95
para obras corporativas y reglas más complejas para obras anteriores a 1929.
La app va a Play Store global.
**Elegido:** **vida + 95 como regla de oro**.
**Implicancias:** Toda fuente nueva debe verificar que el autor murió hace 95+
años antes de incluirla. Los textos del catálogo v1.0 cumplen sin ambigüedad
(Reina, Valera, Torres Amat 1847, Pratt 1916, Westcott 1901, Hort 1892, Scrivener
1891, Tregelles 1875, Tischendorf 1874, Eberhard Nestle 1913, Swete 1917,
Brenton 1862).

Casos límite en el roadmap:
- Rahlfs (1935) cumple vida + 95 recién en 2031. Para la edición de 1935 el
  copyright editorial es de Württembergische Bibelanstalt, no del autor; aún
  así, la edición ha sido tradicionalmente tratada como PD por la academia.
  **Levantar issue legal antes de incluir.**
- Vulgata Clementina edición Tweedale: licencia libre con atribución, no PD
  estricto. Compatibilidad con vida+95 N/A. **Levantar issue de atribución.**

---

## D-007 · SBLGNT: fuera del catálogo

**Fecha:** 2026-04-28
**Contexto:** El EULA del SBLGNT permite redistribución sin modificación pero
restringe uso comercial. Berea cobra USD 6,99 (uso comercial).
**Elegido:** **No incluir SBLGNT en v1.0**. Reemplazos PD claros:
- **Tregelles 1879** (NT crítico).
- **Nestle 1904** (NT eclectico).
- **Tischendorf VIII** (NT crítico, octava ed. 1869-1872).
- **Westcott-Hort 1881** (ya en el catálogo).
- **Scrivener 1894** (Textus Receptus).

Si en una versión futura se quiere incluir SBLGNT, requiere autorización
escrita de la Society of Biblical Literature. Tracking en issue legal.

---

## D-008 · Acentos en RV 1909

**Fecha:** 2026-04-28
**Contexto:** ebible.org distribuye dos variantes: edición original (sin
acentos modernos) y normalización moderna.
**Elegido:** **Distribuir la edición tal como viene en `spaRV1909_usfm.zip`**.
El parser respeta caracteres UTF-8 originales. No introducimos modernización
ortográfica — eso sería "magia editorial" y rompe el principio de
transformación mecánica documentada (sección 1 del Doc 3).

Si en v1.5+ se decide ofrecer una capa de "ortografía modernizada", se
implementa como Biblia separada (`bible_id = "rv1909_mod"`) con su propio
parser y su propio `.bb`. Nunca se mezcla con el original.

---

## D-009 · Versionado

**Fecha:** 2026-04-28
**Tres niveles independientes** (igual al Doc 3 sec. 9):
- `manifest.schema_version` — string SemVer del schema del manifest. Hoy `1.1`.
- `bb.schema_version` — string SemVer del formato interno del `.bb`. Hoy `1.0`.
- Tag de release (`v0.1.0`, `v1.0.0`, …) — versión del repo, congelada en
  GitHub Releases.

Política: SemVer estricto. `MAJOR` rompe compatibilidad con apps existentes;
`MINOR` agrega textos al catálogo; `PATCH` corrige tipos sin tocar el schema.
