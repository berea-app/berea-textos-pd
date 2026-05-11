# Atribuciones — Módulo léxico (v1.5)

Este documento concentra los textos **exactos** de atribución para cada fuente
upstream que alimenta los archivos `.bb` del módulo léxico/interlineal de
Berea v1.5. La app debe usar estas cadenas literalmente en:

- el **bottom sheet léxico** (footer "Fuentes: ..."), por fuente activada;
- la pantalla **Sobre Berea** (sección "Datos léxicos"), agrupado por archivo
  `.bb` descargado.

Las licencias CC BY 4.0 son **de atribución obligatoria** — quitar el
crédito viola los términos de la licencia y nos quita el derecho de
distribuirlas. Cualquier cambio acá debe replicarse en
`pipeline/lexicon/build.py` (constantes `_*_ATTRIBUTION`) y en
`pipeline/build.py` (constantes `_LEXICON_MANIFEST_META` /
`_ALIGNMENT_MANIFEST_META`) para que el header del `.bb` y el manifest
queden consistentes.

---

## Fuentes upstream

### 1. STEPBible Brief Lexicon (TBESG · griego, TBESH · hebreo)

- **Origen**: Tyndale House Cambridge — proyecto STEPBible.
- **Repositorio**: <https://github.com/STEPBible/STEPBible-Data>
- **Licencia**: Creative Commons Attribution 4.0 (CC BY 4.0).
- **Atribución obligatoria**: sí.
- **Texto de atribución**:

  > STEPBible.org / Tyndale House Cambridge — usado bajo CC BY 4.0.

### 2. Strong's Greek Dictionary (1890)

- **Origen**: James Strong (1822-1894), publicado en 1890.
- **Digitalización**: OpenScriptures — <https://github.com/openscriptures/strongs>
- **Licencia**: dominio público por antigüedad; la digitalización
  OpenScriptures es CC0.
- **Atribución obligatoria**: no (PD/CC0), pero Berea la incluye por
  trazabilidad.
- **Texto de atribución**:

  > Strong's Greek Dictionary (1890) — dominio público; digitalización CC0
  > por OpenScriptures.org.

### 3. Brown-Driver-Briggs Hebrew Lexicon (1906)

- **Origen**: F. Brown, S. R. Driver, C. A. Briggs — publicado en 1906.
- **Digitalización**: Open Scriptures Hebrew Bible Project —
  <https://github.com/openscriptures/HebrewLexicon>
- **Licencia**: texto base en dominio público; la digitalización OSHB se
  distribuye bajo Creative Commons Attribution 4.0.
- **Atribución obligatoria**: sí (por la capa OSHB).
- **Texto de atribución**:

  > Brown-Driver-Briggs Hebrew Lexicon (1906) — dominio público;
  > digitalización CC BY 4.0 por Open Scriptures Hebrew Bible Project.

### 4. Liddell-Scott-Jones Full Bible Lexicon (TFLSJ · LSJ completo)

- **Origen**: Henry Liddell + Robert Scott + Henry Stuart Jones — última
  edición revisada (LSJ9, 1940). Texto base en dominio público.
- **Formateo**: Tyndale House Cambridge — proyecto STEPBible.
- **Licencia**: Creative Commons Attribution 4.0 (por la capa de formateo).
- **Atribución obligatoria**: sí.
- **Texto de atribución**:

  > Liddell-Scott-Jones Greek-English Lexicon — dominio público; formateado
  > por Tyndale House / STEPBible.org bajo CC BY 4.0.

### 5. TAGNT — Translators Amalgamated Greek NT (alineamiento NT)

- **Origen**: Tyndale House Cambridge — proyecto STEPBible.
- **Licencia**: Creative Commons Attribution 4.0.
- **Atribución obligatoria**: sí.
- **Cubre las 3 ediciones de Berea v1.5**: Westcott-Hort 1881, Tregelles
  1879 (ed. Jongkind 2009), Textus Receptus (Scrivener 1894).
- **Texto de atribución**:

  > STEPBible.org / Tyndale House Cambridge — TAGNT (Translators
  > Amalgamated Greek NT), distribuido bajo CC BY 4.0.

### 6. TAHOT — Translators Amalgamated Hebrew OT (alineamiento AT)

- **Origen**: Tyndale House Cambridge — proyecto STEPBible.
- **Licencia**: Creative Commons Attribution 4.0.
- **Atribución obligatoria**: sí.
- **Cubre**: Westminster Leningrad Codex moderno (Leningrad + Qere).
  Variantes Ketiv / restored / suplido-LXX se descartan a nivel parser.
- **Texto de atribución**:

  > STEPBible.org / Tyndale House Cambridge — TAHOT (Translators
  > Amalgamated Hebrew OT, Leningrad + Qere), distribuido bajo CC BY 4.0.

---

## Textos compuestos por archivo `.bb`

Estos son los textos que el manifest expone en cada entrada
`lexicons[].attribution_text` / `alignments[].attribution_text`. La app los
usa como **string único** del footer cuando muestra una palabra del .bb
correspondiente.

| `data_id`                       | `attribution_text`                                                                                                                                                          |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `lexicon_grc`                   | Léxico griego: STEPBible.org / Tyndale House Cambridge (CC BY 4.0) + Strong's Greek Dictionary (1890, PD/CC0 vía OpenScriptures).                                            |
| `lexicon_grc_lsj`               | Léxico LSJ completo: Liddell-Scott-Jones (PD) formateado por STEPBible.org / Tyndale House Cambridge (CC BY 4.0).                                                            |
| `lexicon_hbo`                   | Léxico hebreo: STEPBible.org / Tyndale House Cambridge (TBESH, CC BY 4.0) + Brown-Driver-Briggs (1906, PD; digitalización CC BY 4.0 por Open Scriptures Hebrew Bible).      |
| `alignment_grc_nt_wh`           | Alineamiento NT WH: STEPBible.org / Tyndale House Cambridge — TAGNT (CC BY 4.0).                                                                                            |
| `alignment_grc_nt_tregelles`    | Alineamiento NT Tregelles: STEPBible.org / Tyndale House Cambridge — TAGNT (CC BY 4.0).                                                                                     |
| `alignment_grc_nt_tr`           | Alineamiento NT TR: STEPBible.org / Tyndale House Cambridge — TAGNT (CC BY 4.0).                                                                                            |
| `alignment_hbo_ot_wlc`          | Alineamiento AT WLC: STEPBible.org / Tyndale House Cambridge — TAHOT (CC BY 4.0).                                                                                           |

---

## Bloque para la pantalla "Sobre Berea"

Texto sugerido para insertar en la sección de créditos de la app, una vez
que cualquier `.bb` léxico esté descargado:

> **Datos léxicos e interlineales**
>
> Berea utiliza los siguientes recursos académicos abiertos. Cada uno
> mantiene su licencia original; las cards del bottom sheet léxico
> indican la fuente exacta de cada definición y glosa mostrada.
>
> - **STEPBible.org / Tyndale House Cambridge** — léxicos TBESG (griego) y
>   TBESH (hebreo), formateo LSJ completo (TFLSJ), corpus de alineamiento
>   TAGNT (Nuevo Testamento) y TAHOT (Antiguo Testamento). Distribuidos
>   bajo Creative Commons Attribution 4.0.
>   <https://github.com/STEPBible/STEPBible-Data>
>
> - **OpenScriptures** — digitalización del Strong's Greek Dictionary
>   (1890, dominio público; digitalización CC0).
>   <https://github.com/openscriptures/strongs>
>
> - **Open Scriptures Hebrew Bible Project** — digitalización del
>   Brown-Driver-Briggs Hebrew Lexicon (1906, dominio público;
>   digitalización CC BY 4.0).
>   <https://github.com/openscriptures/HebrewLexicon>
>
> Berea distribuye estos datos sin modificar sus definiciones ni glosas;
> únicamente los re-empaqueta como archivos `.bb` (gzipped JSON
> determinista) para consulta offline. El código del pipeline de
> empaquetado está disponible en
> <https://github.com/berea-app/berea-textos-pd>.
