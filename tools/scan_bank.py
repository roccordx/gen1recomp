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
        default=1,
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
    print(f"Scanning bank ${args.bank:02X}")
    print()

    print(
        f"{'Symbol':40}"
        f"{'Found':>10}"
        f"{'Offset':>10}"
        f"{'Score':>10}"
    )

    print("-" * 72)

    for info in db.bank(args.bank):

        symbol = symbols[info.name]

        result = matcher.find(
            symbol,
            matcher_name=args.matcher,
            top=args.top,
        )

        best = result.best

        if best is None:
            continue

        print(
            f"{info.name:40}"
            f"${best.address:04X}"
            f"{best.offset:+10d}"
            f"{best.score*100:9.2f}%"
        )

    print()


if __name__ == "__main__":
    main()