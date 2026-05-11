"""Pipeline para datos léxicos y de alineamiento (módulo v1.5 de Berea).

Mientras ``pipeline/parsers/`` produce archivos ``.bb`` de Biblias (texto
versículo a versículo), ``pipeline/lexicon/`` produce archivos ``.bb`` con
dos contenidos distintos:

- **Lexicón**: entradas de diccionario por lema y código Strong's
  (``lexicon_grc.bb``, ``lexicon_hbo.bb``). Fuentes: STEPBible TBESG/TBESH,
  TFLSJ, openscriptures (Strong's Greek Dictionary, Brown-Driver-Briggs).
- **Alineamiento**: mapeo palabra a palabra entre texto original y coordenada
  canónica (``lexicon_alignment_grc_nt.bb``, ``lexicon_alignment_hbo_ot.bb``).
  Fuentes: STEPBible TAGNT, TAHOT.

Los archivos resultantes son JSON gzipped (mismo wrapper ``.bb`` que las
Biblias) pero con ``type`` distinto en el header — la app consume el manifest
y bifurca según el campo.
"""
