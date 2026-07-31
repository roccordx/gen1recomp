#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

from rom_data import RomImage, SymbolTable
from matcher import MATCHERS, find_best_matches
from symbol_database import SymbolDatabase

WINDOW_SIZE = 128
TOP_RESULTS = 10


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--symbol", required=True)

    parser.add_argument(
        "--window",
        type=int,
        default=WINDOW_SIZE,
        help="Fallback se non è possibile calcolare la lunghezza del simbolo",
    )

    parser.add_argument(
        "--matcher",
        choices=MATCHERS.keys(),
        default="raw",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=TOP_RESULTS,
        help="Numero di risultati da mostrare",
    )

    args = parser.parse_args()

    with open(args.manifest, encoding="utf8") as f:
        manifest = json.load(f)

    symbols = SymbolTable(manifest["symbols"])
    symbol = symbols[args.symbol]

    db = SymbolDatabase(manifest["symbols"])

    real_length = db.length(symbol)
    next_symbol = db.next(symbol)

    if next_symbol is None:
        print("Next symbol : None")
    else:
        print(f"Next name    : {next_symbol.name}")
        print(f"Next bank    : {next_symbol.bank:02X}")
        print(f"Next address : ${next_symbol.address:04X}")

    window = db.window(
        symbol,
        fallback=args.window,
    )

    usa = RomImage(args.source, expected_sha1=None)
    ita = RomImage(args.target, expected_sha1=None)

    source_data = usa.bytes(
        symbol.bank,
        symbol.address,
        window,
    )

    bank_start = 0x0000 if symbol.bank == 0 else 0x4000

    target_bank = ita.bytes(
        symbol.bank,
        bank_start,
        0x4000,
    )

    matcher = MATCHERS[args.matcher]

    matches = find_best_matches(
        source_data,
        target_bank,
        matcher,
        limit=args.top,
    )

    print()
    print(f"Symbol      : {symbol.name}")
    print(f"Matcher     : {args.matcher}")
    print(f"Bank        : {symbol.bank:02X}")
    print(f"Original    : ${symbol.address:04X}")
    print(f"Real length : {real_length}")
    print(f"Window used : {window}")
    print()

    print("Top matches")
    print("----------------------------------------------------------------")
    print("Rank  Address  Offset  Similarity")
    print("----------------------------------------------------------------")

    for rank, (score, offset) in enumerate(matches, start=1):

        cpu_address = bank_start + offset
        delta = cpu_address - symbol.address

        print(
            f"{rank:>4}  "
            f"${cpu_address:04X}   "
            f"{delta:+6d}   "
            f"{score * 100:7.2f}%"
        )

    print()


if __name__ == "__main__":
    main()