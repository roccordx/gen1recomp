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
        "--bank",
        type=lambda x: int(x, 16),
        required=True,
        help="ROM bank (hex), es: 06",
    )

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
    print(f"Scanning bank ${args.bank:02X}")
    print()

    print(
        f"{'Symbol':40}"
        f"{'Found':>10}"
        f"{'Reloc':>8}"
        f"{'Score':>10}"
        f"{'Conf':>10}"
        f"{'OK':>8}"
    )

    print("-" * 90)

    analysis = analyzer.scan_bank(
    args.bank,
    matcher_name=args.matcher,
    top=args.top,
)

    for symbol in analysis.matches:

        if symbol.best is None:
            continue

        confidence_text = (
            f"{symbol.confidence * 100:7.2f}%"
            if symbol.confidence is not None
            else "   N/A"
        )

        ok = "YES" if symbol.reliable else "NO"

        print(
            f"{symbol.name:40}"
            f"${symbol.address:04X}"
            f"{symbol.relocation:+8d}"
            f"{symbol.score * 100:9.2f}%"
            f"{confidence_text:>10}"
            f"{ok:>8}"
        )

    print()


if __name__ == "__main__":
    main()