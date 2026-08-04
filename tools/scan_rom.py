#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

from analyzer import RomAnalyzer
from rom_data import RomImage, SymbolTable
from symbol_database import SymbolDatabase


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--manifest", required=True)

    parser.add_argument(
        "--matcher",
        default="raw",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=5,
    )

    args = parser.parse_args()

    with open(args.manifest, encoding="utf8") as f:
        manifest = json.load(f)

    symbols = SymbolTable(manifest["symbols"])
    db = SymbolDatabase(manifest["symbols"])

    usa = RomImage(args.source, expected_sha1=None)
    ita = RomImage(args.target, expected_sha1=None)

    analyzer = RomAnalyzer(
        usa,
        ita,
        symbols,
        db,
    )

    print()
    print("Scanning ROM...")
    print()

    analysis = analyzer.scan_rom(
        matcher_name=args.matcher,
        top=args.top,
    )

    for bank in analysis.banks:

        print(
            f"Bank {bank.bank:02X} | "
            f"Symbols {bank.total:4d} | "
            f"Reliable {bank.reliable:4d} | "
            f"Review {bank.review:3d} | "
            f"Avg reloc {bank.average_relocation:+6.2f} | "
            f"Avg conf {bank.average_confidence * 100:6.2f}%"
        )

    print()
    print("-" * 80)

    print(f"TOTAL SYMBOLS : {analysis.total_symbols}")
    print(f"RELIABLE     : {analysis.reliable_symbols}")
    print(f"REVIEW       : {analysis.review_symbols}")

    print()


if __name__ == "__main__":
    main()