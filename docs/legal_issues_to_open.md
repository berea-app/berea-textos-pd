# Issues de decisión legal a abrir en GitHub

Tres puntos del Doc 3 sec 4.3 que requieren tu lectura humana antes de
incorporar el texto correspondiente al pipeline. Para cada uno: copiá y
pegá el bloque en `gh issue create` o desde la UI web del repo, con label
`decision-required`.

---

## Issue 1 · SBLGNT y comercialización

**Título:** `SBLGNT: confirmar que queda fuera del catálogo v1.0`

**Label:** `decision-required`, `legal`

**Cuerpo:**

```markdown
## Contexto

El Documento 3 (sección 4.3) del prompt de v1.1 marca el SBLGNT como
incompatible con la app comercial Berea (USD 6,99) por el EULA de la SBL,
que permite redistribución sin modificación pero restringe uso comercial.

## Decisión propuesta

**No incluir SBLGNT en el catálogo v1.0.** Reemplazos PD claros:
- Tregelles 1879
- Nestle 1904
- Tischendorf VIII (octava ed., 1869–1872)
- Westcott-Hort 1881 (ya planeado)
- Scrivener 1894 (ya planeado)

Si en una versión futura queremos incluir SBLGNT, requiere autorización
escrita de la Society of Biblical Literature.

## Lo que tengo que hacer yo

- [ ] Confirmar la decisión.
- [ ] Si hay posibilidad de gestionar la autorización SBL, abrir un issue
      separado para esa gestión.

## Lo que hace Claude Code

Si confirmás la exclusión, agrego Tregelles, Nestle 1904 y Tischendorf VIII
a `pipeline/catalog.py` para que reemplacen al hueco de SBLGNT en el catálogo
de "originales".
```

---

## Issue 2 · Vulgata Clementina edición Tweedale (atribución)

**Título:** `Vulgata Clementina (Tweedale): texto exacto de atribución`

**Label:** `decision-required`, `legal`

**Cuerpo:**

```markdown
## Contexto

La edición de la Vulgata Clementina mantenida por Michael Tweedale
(`vulsearch.sourceforge.net`) está disponible bajo una licencia libre que
**requiere atribución específica**. No es estrictamente PD, pero es
compatible con redistribución comercial siempre que se acredite la fuente.

## Decisión propuesta

Usar el texto de `vulsearch.sourceforge.net` y exhibir la atribución en:
1. La pantalla "Sobre Berea" (créditos por Biblia).
2. El campo `attribution_text` del manifest entry.
3. El campo `attribution_text` dentro del propio `.bb`.

## Texto sugerido de atribución (preliminar — confirmar con la fuente)

> Vulgata Clementina, edición digital de Michael Tweedale et al.,
> distribuida desde vulsearch.sourceforge.net bajo licencia libre con
> atribución requerida.

## Lo que tengo que hacer yo

- [ ] Verificar la licencia exacta del paquete distribuido por vulsearch.
- [ ] Confirmar el texto de atribución que se acepta como suficiente.
- [ ] Decidir si conviene incluir Vulgata en v1.0 (sí/no/pospone a v1.5).

## Lo que hace Claude Code

Una vez confirmes el texto exacto, lo cargo en `pipeline/catalog.py` con
`attribution_required: true` y lo agrego a la sección "Sobre Berea" de la
app cuando lleguemos a la fase 10.
```

---

## Issue 3 · Regla legal: vida + 95 como regla de oro

**Título:** `Regla legal vida+95: confirmar política para todo el catálogo`

**Label:** `decision-required`, `legal`

**Cuerpo:**

```markdown
## Contexto

Argentina aplica vida + 70 (Ley 11.723). Estados Unidos aplica vida + 95
para obras corporativas y reglas más complejas para obras anteriores a 1929.
La app Berea va a Play Store global.

## Decisión propuesta (ya plasmada en DECISIONS.md D-006)

**Aplicar vida + 95 como regla de oro** para incluir un texto en el catálogo.

Esto deja en PD claro a:
- Reina (m. 1594), Valera (m. 1602), edición RV 1909.
- Torres Amat (m. 1847).
- Pratt (m. 1916, vida+95 desde 2011).
- Westcott (m. 1901), Hort (m. 1892).
- Scrivener (m. 1891).
- Tregelles (m. 1875).
- Tischendorf (m. 1874).
- Eberhard Nestle (m. 1913, ed. Nestle 1904).
- Swete (m. 1917).
- Brenton (m. 1862).

## Casos límite del roadmap

- **Rahlfs (m. 1935)** cumple vida + 95 recién en **2031**. La edición de
  1935 tiene copyright editorial de Württembergische Bibelanstalt, aunque
  ha sido tratada como PD por la academia. **Decidir antes de incluir.**
- **Vulgata Clementina (Tweedale)**: licencia libre con atribución, no PD
  estricto. Tracking en issue separado.

## Lo que tengo que hacer yo

- [ ] Confirmar la regla vida + 95 como política.
- [ ] Decidir caso Rahlfs: posponer a 2031, o aceptar el riesgo legal y usar
      la edición de 1935 como PD de facto.

## Lo que hace Claude Code

Implemento `vida + 95` como check automático en `pipeline/catalog.py`
mediante una validación que aborta el build si una entrada nueva no
declara `author_death_year` y `today.year - author_death_year >= 95`.
```

---

## Cómo abrir los tres con `gh`

```bash
# Asumiendo que ya estás autenticado con `gh auth login`.
cd berea-textos-pd

gh issue create --label decision-required --label legal \
  --title "SBLGNT: confirmar que queda fuera del catálogo v1.0" \
  --body-file <(sed -n '/^## Issue 1/,/^---$/p' docs/legal_issues_to_open.md)

# Repetir para Issue 2 y 3.
```

Para no tener que pelearle al `sed`, lo más simple es copiar y pegar cada
bloque desde la UI web de GitHub (`Issues > New issue`).
