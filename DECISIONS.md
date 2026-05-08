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

## D-011 · Catálogo v0.3: Nestle 1904, Westcott-Hort, Tregelles

**Fecha:** 2026-04-29
**Contexto:** Después de v0.2 quedaban pendientes los críticos NT del s. XIX:
WH 1881, Tregelles 1879, Tischendorf VIII, Nestle 1904. Las fuentes limpias
no son ebible.org sino dos repos académicos:

| Texto | Fuente | Formato | Licencia |
|---|---|---|---|
| Nestle 1904 | `biblicalhumanities/Nestle1904` (CSV) | TSV con BCV inglés | PD por antigüedad |
| Westcott-Hort 1881 | STEPBible TAGNT | TSV multi-edición | CC BY 4.0 |
| Tregelles 1879+Jongkind | STEPBible TAGNT | TSV multi-edición | CC BY 4.0 |
| Tischendorf VIII | sin fuente PD limpia identificada | — | pendiente |

**Elegido:**

- **`nestle1904`**: parser propio `nestle1904_tsv` que consume el CSV
  (BCV en formato "Matt 1:1") y emite ParsedVerse por versículo.
- **`wh` y `tregelles`**: parser propio `stepbible_tagnt` que filtra
  el corpus TAGNT por `edition` (config del parser). Una sola implementación
  produce dos Biblias.
- **Tischendorf VIII**: aplazado. No hay fuente PD limpia en formato
  parseable; lo más cercano es archive.org OCR del libro de 1872.

**Justificación técnica de elegir TAGNT sobre `byztxt/greektext-westcott-hort`:**
El repo byztxt usa codificación BetaCode (no Unicode), agrega `\h`/`/`/`(` etc
y necesita un convertidor BetaCode → Unicode con varias variantes históricas.
TAGNT viene en Unicode directo, con texto-crítico canónico revisado por
Tyndale House. Trade-off: aceptamos CC BY 4.0 (en lugar de PD estricto) a
cambio de calidad textual y simplicidad de parser.

**Manejo de variantes en TAGNT:**
1. Columna `editions` (5): qué ediciones contienen ESA palabra exacta.
2. Columna `meaning variants` (6): palabras alternativas que otras ediciones
   usan en lugar de la principal (ej. WH dice "ἁγίων" donde TR dice "ὑμῶν").
3. Columna `spelling variants` (7): variantes ortográficas (ej. WH dice
   "Δαυεὶδ", Tregelles "Δαυὶδ", TR "Δαβὶδ").

El parser maneja las tres y produce ediciones críticas accuratas:
- WH Mc 1:1 omite "υἱοῦ θεοῦ" (lectura de א*).
- WH y Tregelles omiten el Comma Johanneum (1 Jn 5:7-8) — sólo TR lo conserva.
- WH Rev 22:21 termina en "ἁγίων", Tregelles en "ἁγίων" sin "Χριστοῦ".

**Atribución obligatoria CC BY 4.0:**
- `wh.bb` y `tregelles.bb` declaran `attribution_required: true`.
- `attribution_text` cita STEPBible/Tyndale House.
- La pantalla "Sobre Berea" de la app debe exhibir esta atribución.

---

## D-010 · Catálogo v0.2: Textus Receptus, Brenton LXX, OSHB Leningrad

**Fecha:** 2026-04-28
**Contexto:** Después del piloto RV 1909, escalar el catálogo. El Doc 3 sec 4
listaba SBLGNT/Westcott-Hort/Scrivener/Tregelles/Tischendorf/Nestle 1904 como
"originales" y OSHB Leningrad / LXX Rahlfs como "originales hebreos/griegos".
Hay que distinguir lo que está disponible en formato limpio hoy de lo que
requiere parsers nuevos por fuente.
**Elegido para v0.2:**

| bible_id | Texto | Fuente | Parser | Estatus |
|---|---|---|---|---|
| `tr` | Textus Receptus (NT, griego) | `ebible.org/grctr_usfm.zip` | `ebible_usfm` | PD |
| `brenton` | Septuaginta de Brenton (1851, inglés) | `ebible.org/eng-Brenton_usfm.zip` | `ebible_usfm` | PD |
| `wlc` | Westminster Leningrad Codex (OSHB v2.2) | `morphhb v.2.2 release zip` | `oshb_osis` | CC BY 4.0 |

**Justificación de selección:**
- TR es la fuente histórica del NT griego que respalda RV 1909; juntos cubren
  el flujo "leer la versión recibida en castellano y consultar el manuscrito
  griego de base" sin tener que esperar Westcott-Hort.
- Brenton es la traducción al inglés más usada de la LXX y la única edición
  PD limpia disponible. Cubre AT + deuterocanónicos en la numeración LXX.
- OSHB es la fuente académica de facto del AT hebreo: WLC limpio + morfología.
  La obligación de atribución CC BY 4.0 se cumple en `attribution_text`
  por entrada y en la pantalla "Sobre Berea" cuando se implemente.

**Lo que queda pendiente (parsers por fuente, levantar issues legales primero):**
- Westcott-Hort 1881 — fuente: `openscriptures/westcottHort` (TEI XML).
- Scrivener 1894 — fuente: `byztxt/Scrivener` (BETA / TEI).
- Tregelles 1879 — fuente: STEPBible TSV.
- Nestle 1904 — fuente: `biblicalhumanities/Nestle1904` (TEI XML).
- Tischendorf VIII — fuente: STEPBible TSV.
- LXX Rahlfs / Swete — fuente legalmente revisable; **Issue 3 abierto**.
- Vulgata Clementina (Tweedale) — atribución exacta pendiente; **Issue 2 abierto**.
- Torres Amat 1823 — sólo en archive.org (escaneo OCR); requiere parser de
  texto plano y revisión manual extensiva.
- Pratt 1893 — idem archive.org.

**Notas técnicas:**
- Brenton's USFM tiene fragmentos como `\v 50` + `\v 50a` (versículo extra
  LXX no presente en MT). El parser `ebible_usfm` los fusiona en un único
  versículo 50 con texto combinado, en lugar de duplicar la clave.
- Brenton usa `DAG` ("Daniel Greek") en lugar de `DAN`; lo mapeamos a `dan`
  con 14 capítulos (Daniel + Susana + Bel inline). El verifier acepta
  capítulos extra más allá del conteo canónico de 12.
- WLC usa numeración MT en Joel (4 caps vs 3 cristianos) y Malaquías (3 vs
  4). Se distribuye tal cual; la alineación cross-translation entre WLC y
  RV se gestiona con `verse_alias_lxx.json` en versiones futuras.

---

## D-012 · Expansión del catálogo más allá del Doc 4: bloque inglés y español ampliado

**Fecha:** 2026-05-07
**Contexto:** El Doc 4 §1.3 fijó un catálogo de 12 textos PD con buena cobertura
de lenguas originales pero pobre en traducciones modernas: sólo 3 versiones
en español (RV 1909, Torres Amat, Pratt) y **cero traducciones inglesas estándar**
(Brenton sólo cubre la LXX). La app apunta fuerte al módulo de comparación de
traducciones, así que la pobreza relativa del español y la ausencia del inglés
limita ese módulo desde v1.0.

**Decisión:** ampliar el catálogo con un bloque inglés serio y más versiones
históricas en español, todas PD estrictas. El catálogo objetivo pasa de 12 a
~24 textos. Documentado en Doc 4 §1.3 (sección actualizada el 2026-05-07).

**Agregados — inglés (Tier 1):**
- King James Version 1769 + Apocrypha (`kjv`)
- American Standard Version 1901 (`asv`)
- Young's Literal Translation 1898 (`ylt`)
- Darby Bible 1890 (`darby`)
- Douay-Rheims (Challoner) (`drc`)

**Agregados — inglés (Tier 2, oportunista):** Webster 1833 (`webster`),
Revised Version 1881–85 (`rv1885`), Rotherham 1902 (`rotherham`).

**Agregados — español (Tier 1):**
- Reina "Biblia del Oso" 1569 (`reina1569`)
- Valera 1602 (`valera1602`)
- Scío de San Miguel 1793 (`scio`)

**Agregados — español (Tier 2):** Reina-Valera 1865 (`rv1865`).

**Justificación legal:** todos los autores cumplen vida+95 con margen amplio.
La única salvedad documental es la KJV: el Reino Unido conserva *Letters Patent*
que reservan la impresión a Cambridge / Oxford / Collins **dentro del UK**.
Fuera del UK la KJV es PD pleno; la distribución digital global vía Play Store
no se considera afectada por la patente real (que apunta a impresión, no a
copia digital), tal como hacen YouVersion, Bible Gateway y demás distribuidores
mainstream sin litigio. **Riesgo asumido: bajo.** Si hay una notificación legal
del Crown, retiramos la KJV del manifest distribuido a UK y listo (no afecta a
quienes ya la descargaron porque el binario está libre en cualquier jurisdicción
no-UK).

**Justificación de fuentes:** ebible.org publica USFM limpio para KJV, ASV,
YLT, Darby, Douay-Rheims, Webster y Rotherham. El parser `ebible_usfm` ya
existente las absorbe sin cambios. Reina 1569, Valera 1602 y Scío requieren
parser propio (digitalizaciones de archive.org / SBT en texto plano, calidad OCR
variable). Esos van en una segunda fase.

**Distribución:** todas las nuevas Biblias van con `bundled_in_apk: false`. Se
distribuyen como `.bb` descargables vía GitHub Releases, igual que el resto del
catálogo. La única Biblia bundleada en el APK sigue siendo RV 1909. El usuario
descarga las demás bajo demanda desde la pantalla de "Biblioteca".

**Orden de implementación (priorizado):**

1. KJV (este commit / build)
2. ASV
3. YLT
4. Darby
5. Douay-Rheims
6. Torres Amat 1823 (parser archive.org propio)
7. Versión Moderna (Pratt) 1893 (parser archive.org)
8. Tischendorf VIII (parser STEPBible o archive.org)
9. Swete LXX
10. Vulgata Clementina (Tweedale)
11. Reina 1569 / Valera 1602 / Scío 1793 (parsers de digitalización)
12. Tier 2: Webster, RV 1881, Rotherham, RV 1865

---

## D-013 · Torres Amat 1823 + Vulgata Clementina 1592 vía itercatholicum

**Fecha:** 2026-05-08
**Contexto:** Después de cerrar el bloque inglés (D-012, v0.4.0), seguimos con
los textos pendientes en español. La fuente más antigua para Torres Amat 1823
son los nueve tomos escaneados en archive.org (1823–25), sin estructura por
capítulo/versículo: significaría parser OCR desde cero más limpieza manual
extensiva. Mucho costo para un solo texto.

**Hallazgo:** el repo público `danloi2/itercatholicum` distribuye dos ediciones
ya transcritas y estructuradas en JSON por libro (73 archivos cada una,
canon católico):

- `1823_torres_amat_es` — Torres Amat 1823 desde credobiblestudy.
- `1592_vulgata_clementina_la` — Vulgata Sixto-Clementina desde Wikisource.

Cada archivo declara `licentia: "Dominio Público"` o `"Public Domain"`
y referencia su `fons`. La estructura es un dict `{capitula: [{numerus,
versus: {n: text}}]}` trivial de parsear.

**Decisión:**

1. Tomar ambas ediciones como fuente y escribir un parser propio
   `pipeline/parsers/itercatholicum_json.py`. El estatus PD de cada texto
   está garantizado por antigüedad (Torres Amat m. 1847, Vulgata Clementina
   1592); la licencia del repo intermedio es secundaria.
2. **Pinear la fuente al commit `ffe943aaf0ec25dcbc0188f24471f6f6683069cc`**
   de itercatholicum (HEAD al 2026-04-30) para reproducibilidad. Se descargan
   los 73 archivos individuales vía `raw.githubusercontent.com/<commit>/...`
   (byte-estable a un ref dado), no el zipball completo (que GitHub
   re-genera con bytes distintos al re-archivar).
3. **`source_attribution`** menciona explícitamente la cadena:
   `danloi2/itercatholicum · <edición> · <fons>`. Atribución de cortesía,
   no obligatoria (PD).
4. **Pratt 1893 (Versión Moderna)** queda postergado: no hay digitalización
   estructurada disponible; requiere parser OCR desde archive.org en sesión
   dedicada.

**Mapeo de book_id:** los IDs de itercatholicum usan abreviaturas en español
(`ex`, `dt`, `mt`, `mc`, `lc`, `jn`, `hch`, `eclo`, `cant`, `ag`, `ap`,
etc.). El parser los normaliza a USFM 3.0 lowercase via `_SOURCE_BOOK_ID_TO_USFM`.

**Sobre la calidad del OCR:** la transcripción de Torres Amat tiene
artefactos menores típicos del XIX digitalizado (ej. "SucediÓ" con Ó
mayúscula errónea en 1Mac 1:1; tildes faltantes ocasionales). Aceptable;
el texto es legible y coherente. La Vulgata Clementina viene de
Wikisource, sin esos artefactos, con ligaduras `æ` preservadas.

**Numeración de Salmos:** ambas ediciones siguen la numeración Vulgata/LXX
(offset −1 respecto a MT en gran parte del salterio). Sal 22 TA / Vulgata
= Sal 23 RV ("El Señor es mi pastor"). El aliasing entre numeraciones
queda como deuda técnica; `canon/verse_alias_lxx.json` ya existe para LXX,
falta extender a Vulgata. La app por ahora muestra cada Biblia con su
propia numeración.

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
