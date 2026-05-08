"""Command-line entry point.

Examples:
    python -m pipeline.cli build --bible rv1909
    python -m pipeline.cli build --all
    python -m pipeline.cli manifest
"""

from __future__ import annotations

import argparse
import sys

from .build import build_one, regenerate_manifest
from .catalog import CATALOG


def _cmd_build(args: argparse.Namespace) -> int:
    if args.all:
        for bible_id in CATALOG:
            path, report = build_one(bible_id)
            print(f"[{bible_id}] {path} ({report.book_count} books, {report.verse_count} verses)")
            for w in report.warnings:
                print(f"  ! {w}", file=sys.stderr)
        regenerate_manifest()
        return 0

    if not args.bible:
        print("error: must pass --bible <id> or --all", file=sys.stderr)
        return 2

    path, report = build_one(args.bible)
    print(f"[{args.bible}] {path} ({report.book_count} books, {report.verse_count} verses)")
    for w in report.warnings:
        print(f"  ! {w}", file=sys.stderr)
    regenerate_manifest()
    return 0


def _cmd_manifest(_args: argparse.Namespace) -> int:
    path = regenerate_manifest()
    print(f"manifest written: {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="build one or all Bibles")
    p_build.add_argument("--bible", help="bible_id to build")
    p_build.add_argument("--all", action="store_true", help="build every bible in CATALOG")
    p_build.set_defaults(func=_cmd_build)

    p_manifest = sub.add_parser("manifest", help="regenerate the manifest only")
    p_manifest.set_defaults(func=_cmd_manifest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
