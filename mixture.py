#!/usr/bin/env python3
"""Prepare external DORT mixture files from an Excel workbook.

This is the API-backed replacement for the original standalone spreadsheet
script.  With no options it preserves the established defaults::

    python mixture.py mixtures.xlsx

which reads sheet ``Read`` with columns ``Nuclide``, ``MAT No.``, followed by
mixture-density columns, assumes P5, and writes::

    mix.inp
    Mixture_Names.txt
    dort_mix_cards.txt

The heavy lifting is implemented in :mod:`mixtures` so the same spreadsheet
workflow is available from normal Python model scripts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mixtures import MixtureRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate mix.inp and local DORT mixture mapping cards from Excel."
    )
    parser.add_argument(
        "workbook",
        nargs="?",
        default="mixtures.xlsx",
        help="Excel workbook containing the mixture table (default: mixtures.xlsx).",
    )
    parser.add_argument(
        "--sheet",
        default="Read",
        help="Worksheet containing the mixture table (default: Read).",
    )
    parser.add_argument(
        "--order",
        type=int,
        default=5,
        help="Legendre scattering order L used for table numbering (default: 5).",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory for generated files (default: current directory).",
    )
    parser.add_argument(
        "--validate",
        metavar="MIXF.CR",
        help="Optionally validate an already generated mixf.cr file.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    registry = MixtureRegistry.from_excel(args.workbook, sheet_name=args.sheet)

    files = registry.write_preparation_files(args.output_dir, args.order)

    print(registry.layout_text(args.order))
    print()
    for label, path in files.items():
        print(f"{label:14s}: {path}")

    if args.validate:
        print()
        check = registry.validate_mix_file(args.validate, args.order)
        print(check.summary_text())
        if not check.valid:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
