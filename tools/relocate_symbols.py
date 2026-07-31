#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

from rom_data import RomImage, SymbolTable


def hex_dump(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Offset da applicare all'indirizzo della ROM target",
    )

    args = parser.parse_args()

    with open(args.manifest, encoding="utf8") as f:
        manifest = json.load(f)

    symbols = SymbolTable(manifest["symbols"])
    symbol = symbols[args.symbol]

    source = RomImage(args.source, expected_sha1=None)
    target = RomImage(args.target, expected_sha1=None)

    target_addr = symbol.address + args.offset

    print(f"Symbol      : {symbol.name}")
    print(f"Bank        : {symbol.bank:02X}")
    print(f"USA Addr    : ${symbol.address:04X}")
    print(f"ITA Addr    : ${target_addr:04X}")
    print(f"Offset      : {args.offset:+d}")
    print()

    usa = source.bytes(symbol.bank, symbol.address, 32)
    ita = target.bytes(symbol.bank, target_addr, 32)

    print("USA")
    print(hex_dump(usa))
    print()

    print("ITA")
    print(hex_dump(ita))
    print()

    matches = sum(a == b for a, b in zip(usa, ita))
    print(f"Byte uguali : {matches}/{len(usa)}")


if __name__ == "__main__":
    main()