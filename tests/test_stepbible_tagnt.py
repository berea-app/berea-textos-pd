"""Parser-level tests for the STEPBible TAGNT parser."""

from __future__ import annotations

from pipeline.parsers.stepbible_tagnt import (
    _editions_set,
    _meaning_variant_for,
    _parse_word_row,
    _spelling_for,
)


def test_editions_set_handles_decorative_plus_prefix():
    assert _editions_set("Tyn+WH+Treg+Byz") == {"Tyn", "WH", "Treg", "Byz"}
    assert _editions_set("+TR") == {"TR"}


def test_spelling_for_picks_target_edition():
    field = "Tyn+WH: Δαυεὶδ ; +TR: Δαβὶδ ;"
    assert _spelling_for("WH", field) == "Δαυεὶδ"
    assert _spelling_for("TR", field) == "Δαβὶδ"
    assert _spelling_for("Treg", field) is None


def test_meaning_variant_for_picks_target_edition():
    field = "ἁγίων (O=hagiōn) saints. - G0040=A-GPM in: Tyn+WH+Treg+Byz"
    assert _meaning_variant_for("WH", field) == "ἁγίων"
    assert _meaning_variant_for("Treg", field) == "ἁγίων"
    assert _meaning_variant_for("TR", field) is None


def test_parse_word_row_filters_by_edition():
    cols = (
        "Mat.1.1#01=NKO\tΒίβλος (Biblos)\t[The] book\tG0976=N-NSF\tβίβλος=book\t"
        "NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz\t\t\t\t\t\t\t\t\t"
    ).split("\t")
    row = _parse_word_row(cols, edition="WH")
    assert row is not None
    (book_id, chapter, verse), word = row
    assert (book_id, chapter, verse) == ("mat", 1, 1)
    assert word == "Βίβλος"


def test_parse_word_row_returns_none_when_edition_absent():
    cols = (
        "Jhn.3.16#11=ko\tαὐτοῦ (autou)\tof him\tG0846=P-GSM\tαὐτός=he\t"
        "Treg+TR+Byz\t\t\t\t\t\t\t\t\t"
    ).split("\t")
    assert _parse_word_row(cols, edition="WH") is None
    row = _parse_word_row(cols, edition="Treg")
    assert row is not None and row[1] == "αὐτοῦ"


def test_parse_word_row_falls_back_to_meaning_variant():
    cols = (
        "Rev.22.21#11=K(O)\tὑμῶν. (humōn)\tof you\tG4771=P-2GP\tσύ=you\tTR\t"
        "ἁγίων (O=hagiōn) saints. - G0040=A-GPM in: Tyn+WH+Treg+Byz\t\tde ustedes"
        "\t\t\t\t\t\t"
    ).split("\t")
    row = _parse_word_row(cols, edition="WH")
    assert row is not None
    assert row[1] == "ἁγίων"
