#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

from matcher import SymbolMatcher
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

    matcher = SymbolMatcher(
        usa,
        ita,
        db,
    )

    print()
    print("Scanning ROM...")
    print()

    total_symbols = 0
    reliable_symbols = 0

    for bank in sorted(db._banks.keys()):

        bank_symbols = db.bank(bank)

        bank_total = 0
        bank_reliable = 0

        relocation_sum = 0
        confidence_sum = 0.0
        confidence_count = 0

        for info in bank_symbols:

            symbol = symbols[info.name]

            result = matcher.find(
                symbol,
                matcher_name=args.matcher,
                top=args.top,
            )

            bank_total += 1
            total_symbols += 1

            if result.reliable:
                bank_reliable += 1
                reliable_symbols += 1

            if result.relocation is not None:
                relocation_sum += result.relocation

            if result.confidence is not None:
                confidence_sum += result.confidence
                confidence_count += 1

        review = bank_total - bank_reliable

        avg_relocation = (
            relocation_sum / bank_total
            if bank_total else 0
        )

        avg_confidence = (
            confidence_sum / confidence_count * 100
            if confidence_count else 0
        )

        print(
            f"Bank {bank:02X} | "
            f"Symbols {bank_total:4d} | "
            f"Reliable {bank_reliable:4d} | "
            f"Review {review:3d} | "
            f"Avg reloc {avg_relocation:+6.2f} | "
            f"Avg conf {avg_confidence:6.2f}%"
        )

    print()
    print("-" * 80)
    print(
        f"TOTAL SYMBOLS : {total_symbols}"
    )
    print(
        f"RELIABLE     : {reliable_symbols}"
    )
    print(
        f"REVIEW       : {total_symbols - reliable_symbols}"
    )
    print()


if __name__ == "__main__":
    main()