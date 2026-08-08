#!/usr/bin/env python3

"""Compare raw matching results for explicit source window sizes."""

from __future__ import annotations

import argparse
import json

from matcher import find_best_matches, raw_similarity
from rom_data import RomImage, SymbolTable
from symbol_database import SymbolDatabase


WINDOW_SIZES = (5, 8, 16, 32, 64, 128)
TOP_MATCHES = 5


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test raw-match discrimination as a source window grows."
    )
    parser.add_argument(
        "bank",
        nargs="?",
        default="09",
        type=lambda value: int(value, 16),
        help="ROM bank in hexadecimal (default: 09)",
    )
    parser.add_argument(
        "address",
        nargs="?",
        default="0x7E02",
        type=lambda value: int(value, 16),
        help="CPU address in hexadecimal (default: 0x7E02)",
    )
    args = parser.parse_args()

    with open("tools/rom_manifest.json", encoding="utf8") as source:
        manifest = json.load(source)

    symbols = SymbolTable(manifest["symbols"])
    database = SymbolDatabase(manifest["symbols"])

    if not database.bank(args.bank):
        print(f"Error: bank {args.bank:02X} does not exist in the symbol database.")
        return 1

    names = symbols.names_at(args.bank, args.address)
    if not names:
        print(f"Error: no symbol exists at {args.bank:02X}:${args.address:04X}.")
        return 1

    symbol = symbols[names[0]]
    source_rom = RomImage("red-usa.gb", expected_sha1=None)
    target_rom = RomImage("red-ita.gb", expected_sha1=None)
    bank_start = 0x0000 if symbol.bank == 0 else 0x4000
    target_bank = target_rom.bytes(symbol.bank, bank_start, 0x4000)

    print(f"Symbol: {symbol.name} ({symbol.bank:02X}:${symbol.address:04X})")

    for window in WINDOW_SIZES:
        source_data = source_rom.bytes(symbol.bank, symbol.address, window)
        matches = find_best_matches(
            source_data,
            target_bank,
            raw_similarity,
            limit=TOP_MATCHES,
        )

        print(f"\nWindow {window}")
        for rank, (score, offset) in enumerate(matches, start=1):
            address = bank_start + offset
            relocation = address - symbol.address
            print(
                f"  {rank}: ${address:04X} {relocation:+d} {score:.6f}"
            )

        best = matches[0] if matches else None
        second = matches[1] if len(matches) > 1 else None
        if best is None:
            print("  Best: None")
            print("  Second-best score: None")
            print("  Confidence: None")
            continue

        best_score, best_offset = best
        best_address = bank_start + best_offset
        print(
            f"  Best: score={best_score:.6f} "
            f"target=${best_address:04X} "
            f"offset={best_address - symbol.address:+d}"
        )
        if second is None:
            print("  Second-best score: None")
            print("  Confidence: None")
        else:
            second_score, _ = second
            print(f"  Second-best score: {second_score:.6f}")
            print(f"  Confidence: {best_score - second_score:.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
