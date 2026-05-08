#!/usr/bin/env python3
"""Generate ``canon/numbering_alias.json`` from a programmatic specification.

The dataset is small but mechanical: writing it by hand invites typos and
makes it impossible to audit. We generate it from the canonical MT↔LXX
Psalm rule and a short list of split/merge cases.

Coverage in v1.0 — Psalms only.

Why no Joel / Malachi: every Vulgate-numbered edition currently in the
catalogue (DRC, Vulgata Clementina, Torres Amat) ships those books with
the modern (MT-aligned) chapter numbering, not the historical Vulgate
3-chapter Joel / 3-chapter Malachi pattern. Adding aliases for chapters
that nobody actually uses would mislead the reader.

Why no 1 Samuel 23/24: the divergence is one verse and varies between
editions (DRC and Vulgata Clementina share one pattern; Torres Amat
uses another). A blanket alias would be wrong for at least one edition;
verse-level aliases are out of scope for v1.0.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "canon" / "numbering_alias.json"


def generate_psalm_chapter_aliases() -> list[dict]:
    """Sal 11..113 MT ↔ Sal 10..112 Vulgata (offset −1 after merge of MT 9+10).
    Sal 117..146 MT ↔ Sal 116..145 Vulgata (offset −1 after merge of MT 114+115).
    Other chapters are either identical or covered by split_or_merge."""
    out: list[dict] = []
    for mt_ch in range(11, 114):
        out.append({"book": "psa", "mt": mt_ch, "vulgata": mt_ch - 1})
    for mt_ch in range(117, 147):
        out.append({"book": "psa", "mt": mt_ch, "vulgata": mt_ch - 1})
    return out


def generate_psalm_split_or_merge() -> list[dict]:
    return [
        {
            "book": "psa",
            "mt_chapters": [9, 10],
            "vulgata_chapters": [9],
            "type": "merged_in_vulgata",
            "note": (
                "Psalms 9 and 10 of the Masoretic Text are a single psalm "
                "(Psalm 9) in the LXX/Vulgate."
            ),
        },
        {
            "book": "psa",
            "mt_chapters": [114, 115],
            "vulgata_chapters": [113],
            "type": "merged_in_vulgata",
            "note": (
                "Psalms 114 and 115 MT are a single Psalm 113 in the LXX/Vulgate."
            ),
        },
        {
            "book": "psa",
            "mt_chapters": [116],
            "vulgata_chapters": [114, 115],
            "type": "split_in_vulgata",
            "note": (
                "Psalm 116 MT is split into Psalms 114 and 115 in the LXX/Vulgate. "
                "Verses 1-9 are Psalm 114, verses 10-19 are Psalm 115."
            ),
        },
        {
            "book": "psa",
            "mt_chapters": [147],
            "vulgata_chapters": [146, 147],
            "type": "split_in_vulgata",
            "note": (
                "Psalm 147 MT is split into Psalms 146 and 147 in the LXX/Vulgate. "
                "Verses 1-11 are Psalm 146, verses 12-20 are Psalm 147."
            ),
        },
    ]


def main() -> None:
    payload = {
        "schema_version": "1.0",
        "description": (
            "Cross-tradition chapter aliasing between MT-numbered and "
            "LXX/Vulgate-numbered Bibles. Covers the Psalter only in v1.0; "
            "Joel, Malachi and 1 Samuel are excluded because the editions "
            "currently distributed by Berea use MT numbering for those books."
        ),
        "schemes": {
            "mt": (
                "Hebrew Masoretic chapter numbering. Used by editions that "
                "follow the Hebrew Bible structure: Reina-Valera 1909, "
                "King James Version, American Standard Version, Young's "
                "Literal Translation, Darby Bible, Westminster Leningrad "
                "Codex (OSHB), and the critical Greek New Testaments."
            ),
            "vulgata": (
                "LXX / Vulgate chapter numbering. Used by editions in the "
                "Catholic / Septuagint tradition: Douay-Rheims, Torres Amat, "
                "Vulgata Clementina, Brenton's English Septuagint."
            ),
        },
        "chapter_aliases": generate_psalm_chapter_aliases(),
        "split_or_merge": generate_psalm_split_or_merge(),
    }

    OUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  chapter_aliases: {len(payload['chapter_aliases'])}")
    print(f"  split_or_merge:  {len(payload['split_or_merge'])}")


if __name__ == "__main__":
    main()
