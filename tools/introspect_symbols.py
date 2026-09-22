#!/usr/bin/env python3
"""Inspect the manifest-backed symbol data used by the ROM tools.

This script intentionally works from the real manifest structure and the current
`rom_data.SymbolTable`, without assuming any nested `manifest["symbols"]`
layout beyond the repository data itself.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from rom_data import SymbolTable


MANIFEST_PATH = ROOT / "rom_manifest.json"
ANCHORS = (
    "_TrainerNameText",
    "_MtMoonB1FUnusedText",
    "_SilphCo5FRocket1EndBattleText",
)


def load_manifest(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    manifest = load_manifest(MANIFEST_PATH)
    symbols = manifest["symbols"]

    print("manifest path:", MANIFEST_PATH)
    print("manifest['symbols'] type:", type(symbols).__name__)
    print("manifest['symbols'] entries:", len(symbols))
    print("sample keys:", list(symbols.keys())[:5])
    sample_items = list(symbols.items())[:3]
    print("sample values:")
    for name, value in sample_items:
        print(f"  {name}: {value!r}  (list_len={len(value)})")

    table = SymbolTable(symbols)
    print("\nSymbolTable.by_name type:", type(table.by_name).__name__)
    print("SymbolTable.by_name size:", len(table.by_name))

    for name in ANCHORS:
        symbol = table[name]
        print(f"{name}: Symbol(bank={symbol.bank}, address={symbol.address:#06x}, name={symbol.name!r})")

    bank_symbols = sorted(
        (symbol for symbol in table.by_name.values() if symbol.bank == 0x20),
        key=lambda symbol: (symbol.address, symbol.name),
    )
    print(f"\nbank 0x20 count: {len(bank_symbols)}")
    print("bank 0x20 first rows:")
    for symbol in bank_symbols[:10]:
        print(f"  {symbol.name}: {symbol.address:#06x}")

    print("\nbank 0x20 anchor neighborhood:")
    for name in ANCHORS:
        symbol = table[name]
        matches = [
            s for s in bank_symbols
            if symbol.address - 0x20 <= s.address <= symbol.address + 0x20
        ]
        print(f"  {name}: {[(s.name, s.address) for s in matches]}")

    try:
        from symbol_database import SymbolDatabase
    except ModuleNotFoundError:
        print("\nSymbolDatabase: not present in the current checkout.")
        print("Historical implementation exists on origin/feature/italian-rom-support and wraps the same manifest dict into ordered SymbolInfo rows.")
        return 0

    db = SymbolDatabase(symbols)
    print("\nSymbolDatabase ok:", type(db).__name__)
    print("db.bank(0x20) count:", len(db.bank(0x20)))
    print("db.bank(0x20) first rows:")
    for info in db.bank(0x20)[:10]:
        print(f"  {info.name}: {info.address:#06x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
