#!/usr/bin/env python3

"""Diagnostic experiment for short-symbol context matching in Bank 09."""

from __future__ import annotations

import argparse
import collections
import json
from typing import Callable

from matcher import find_best_matches, raw_similarity
from rom_data import RomImage, SymbolTable, Symbol
from symbol_database import SymbolDatabase

TEST_WINDOWS = (32, 64, 128)
RELIABLE_CONFIDENCE = 0.30
BANK = 0x09


def bank_start(bank: int) -> int:
    return 0x0000 if bank == 0 else 0x4000


def load_manifest(path: str) -> dict:
    with open(path, encoding="utf8") as source:
        return json.load(source)


def select_short_symbols(symbols: SymbolTable, database: SymbolDatabase) -> list[Symbol]:
    return [
        symbol
        for symbol in symbols.all_symbols()
        if symbol.bank == BANK
        and not symbol.name.startswith("TypeNames.")
        and database.window(symbol, fallback=128) <= 16
    ]


def best_matches(source_rom: RomImage, target_bank: bytes, symbol: Symbol, window: int, top: int = 2) -> list[tuple[float, int]]:
    source_data = source_rom.bytes(symbol.bank, symbol.address, window)
    return find_best_matches(source_data, target_bank, raw_similarity, limit=top)


def format_score(value: float | None) -> str:
    return f"{value:.6f}" if value is not None else "None"


def format_offset(offset: int | None) -> str:
    return f"{offset:+d}" if offset is not None else "None"


def print_result(symbol: Symbol, window: int, matches: list[tuple[float, int]]) -> tuple[int | None, bool, float | None]:
    bank_offset = bank_start(symbol.bank)
    best = matches[0] if matches else None
    second = matches[1] if len(matches) > 1 else None

    if best is None:
        best_offset = None
        best_score = None
    else:
        best_score, best_target_offset = best
        best_address = bank_offset + best_target_offset
        best_offset = best_address - symbol.address

    second_score = second[0] if second is not None else None
    confidence = None if second_score is None or best_score is None else best_score - second_score
    reliable = confidence is not None and confidence >= RELIABLE_CONFIDENCE

    print(
        f"symbol={symbol.name} "
        f"source={symbol.bank:02X}:${symbol.address:04X} "
        f"window={window} "
        f"best_offset={format_offset(best_offset)} "
        f"best_score={format_score(best_score)} "
        f"second_best_score={format_score(second_score)} "
        f"confidence={format_score(confidence)} "
        f"reliable={reliable}"
    )

    return best_offset, reliable, confidence


def summarize(results: dict[int, list[tuple[int | None, bool, float | None]]]) -> None:
    print()
    for window in sorted(results):
        window_rows = results[window]
        count = len(window_rows)
        baseline_offsets = [row[0] for row in results[128]]
        same_as_128 = sum(
            1
            for (offset, _, _), baseline in zip(window_rows, baseline_offsets)
            if offset == baseline
        )
        reliable_count = sum(1 for _, reliable, _ in window_rows if reliable)
        confidences = [confidence for _, _, confidence in window_rows if confidence is not None]
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        print(f"Window {window}")
        print(f"  symbols tested: {count}")
        print(f"  offsets matching window 128: {same_as_128}")
        print(f"  reliable matches: {reliable_count}")
        print(f"  average confidence: {average_confidence:.6f}")

    distribution = collections.Counter(
        offset for offset, _, _ in results[128] if offset is not None
    )
    print("\nWindow 128 offset distribution:")
    for offset, count in sorted(distribution.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {format_offset(offset):>5} : {count} symbols")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test whether short symbols in Bank 09 benefit from larger matching context."
    )
    parser.add_argument(
        "--manifest",
        default="tools/rom_manifest.json",
        help="Path to the ROM manifest JSON file.",
    )
    parser.add_argument(
        "--source-rom",
        default="red-usa.gb",
        help="Path to the source ROM image.",
    )
    parser.add_argument(
        "--target-rom",
        default="red-ita.gb",
        help="Path to the target ROM image.",
    )
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    symbols = SymbolTable(manifest["symbols"])
    database = SymbolDatabase(manifest["symbols"])

    source_rom = RomImage(args.source_rom, expected_sha1=None)
    target_rom = RomImage(args.target_rom, expected_sha1=None)
    target_bank = target_rom.bytes(BANK, bank_start(BANK), 0x4000)

    selected = select_short_symbols(symbols, database)
    if not selected:
        print("No short symbols found in bank 09.")
        return 1

    print(f"Short-symbol context experiment: {len(selected)} symbols in bank 09")

    results: dict[int, list[tuple[int | None, bool, float | None]]] = collections.defaultdict(list)

    for symbol in selected:
        original = database.window(symbol, fallback=128)
        windows = [original] + list(TEST_WINDOWS)
        for window in windows:
            matches = best_matches(source_rom, target_bank, symbol, window, top=2)
            result = print_result(symbol, window, matches)
            results[window].append(result)

    summarize(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
