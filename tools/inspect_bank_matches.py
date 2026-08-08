#!/usr/bin/env python3

"""Print the raw matcher results for one ROM bank before later processing."""

from __future__ import annotations

import argparse
from collections import Counter
import json

from analyzer import RomAnalyzer
from rom_data import RomImage, SymbolTable
from symbol_database import SymbolDatabase


def format_match(match) -> str:
    """Return the existing match result in the diagnostic's display format."""

    if match is None:
        return "None"

    return (
        f"score={match.score:.6f}  "
        f"CPU target address=${match.address:04X}  "
        f"relocation offset={match.offset:+d}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect raw SymbolMatcher results for one bank before boundary "
            "detection and segment normalization."
        )
    )
    parser.add_argument(
        "bank",
        nargs="?",
        default="09",
        type=lambda value: int(value, 16),
        help="ROM bank in hexadecimal (default: 09)",
    )
    args = parser.parse_args()

    with open("tools/rom_manifest.json", encoding="utf8") as source:
        manifest = json.load(source)

    symbols = SymbolTable(manifest["symbols"])
    database = SymbolDatabase(manifest["symbols"])
    bank_symbols = database.bank(args.bank)

    if not bank_symbols:
        print(f"Error: bank {args.bank:02X} does not exist in the symbol database.")
        return 1

    usa = RomImage("red-usa.gb", expected_sha1=None)
    ita = RomImage("red-ita.gb", expected_sha1=None)
    analysis = RomAnalyzer(usa, ita, symbols, database).scan_bank(args.bank)

    matches = sorted(
        analysis.matches,
        key=lambda symbol: symbol.match.symbol.address,
    )
    confidences = []
    offsets = Counter()
    matched = 0
    reliable = 0
    exact = 0

    print(f"Bank {args.bank:02X} raw matcher results")
    print("=" * 72)

    for symbol_analysis in matches:
        match = symbol_analysis.match
        best = match.best
        confidence = match.confidence

        if best is not None:
            matched += 1
            offsets[best.offset] += 1
        if match.reliable:
            reliable += 1
        if match.exact:
            exact += 1
        if confidence is not None:
            confidences.append(confidence)

        print()
        print(f"Source address : ${match.symbol.address:04X}")
        print(f"Symbol name    : {match.symbol.name}")
        print(f"Window size    : {match.window}")
        print(f"Best match     : {format_match(best)}")
        print(f"Second match   : {format_match(match.second)}")
        print(
            "Confidence     : "
            f"{confidence:.6f}" if confidence is not None else "Confidence     : None"
        )
        print(f"Reliable       : {match.reliable}")
        print(f"Exact          : {match.exact}")

    average_confidence = (
        sum(confidences) / len(confidences) if confidences else None
    )

    print()
    print("=" * 72)
    print("Summary")
    print(f"Total symbols             : {len(matches)}")
    print(f"Symbols with a best match : {matched}")
    print(f"Symbols with reliable=True: {reliable}")
    print(f"Symbols with exact=True   : {exact}")
    if average_confidence is None:
        print("Average confidence        : None")
    else:
        print(f"Average confidence        : {average_confidence:.6f}")

    print()
    print("Offset distribution")
    for offset, count in sorted(offsets.items(), key=lambda item: (-item[1], item[0])):
        print(f"offset {offset:+d} : {count} symbols")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
