#!/usr/bin/env python3

"""Diagnostic experiment for TypeNames context matching in Bank 09."""

from __future__ import annotations

import argparse
import collections
import json
from typing import Iterable

from matcher import find_best_matches, raw_similarity
from rom_data import RomImage, SymbolTable, Symbol
from symbol_database import SymbolDatabase

WINDOW_SIZES = (32, 64, 128)
RELIABLE_CONFIDENCE = 0.30


def bank_start(bank: int) -> int:
    return 0x0000 if bank == 0 else 0x4000


def load_manifest(path: str) -> dict:
    with open(path, encoding="utf8") as source:
        return json.load(source)


def typename_symbols(symbols: SymbolTable) -> list[Symbol]:
    return [
        symbol
        for symbol in symbols.prefixed("TypeNames.")
        if symbol.bank == 0x09
    ]


def symbol_window(database: SymbolDatabase, symbol: Symbol) -> int:
    return database.window(symbol, fallback=128)


def best_matches_for_window(
    source_rom: RomImage,
    target_bank: bytes,
    symbol: Symbol,
    window: int,
    top: int = 2,
) -> list[tuple[float, int]]:
    source_data = source_rom.bytes(symbol.bank, symbol.address, window)
    return find_best_matches(source_data, target_bank, raw_similarity, limit=top)


def format_offset(value: int) -> str:
    return f"{value:+d}"


def print_symbol_result(symbol: Symbol, window: int, matches: list[tuple[float, int]]) -> tuple[int, bool, float | None]:
    bank_start_addr = bank_start(symbol.bank)
    best = matches[0] if matches else None
    second = matches[1] if len(matches) > 1 else None

    if best is None:
        best_address = None
        best_offset = None
        best_score = None
        second_score = None
        confidence = None
        reliable = False
    else:
        best_score, best_offset_raw = best
        best_address = bank_start_addr + best_offset_raw
        best_offset = best_address - symbol.address
        second_score = second[0] if second is not None else None
        confidence = None if second_score is None else best_score - second_score
        reliable = confidence is not None and confidence >= RELIABLE_CONFIDENCE

    best_score_text = f"{best_score:.6f}" if best_score is not None else "None"
    second_score_text = f"{second_score:.6f}" if second_score is not None else "None"
    confidence_text = f"{confidence:.6f}" if confidence is not None else "None"

    print(
        f"symbol={symbol.name} "
        f"source={symbol.bank:02X}:${symbol.address:04X} "
        f"window={window} "
        f"best_target={best_address:04X} "
        f"best_offset={format_offset(best_offset) if best_offset is not None else 'None'} "
        f"best_score={best_score_text} "
        f"second_best_score={second_score_text} "
        f"confidence={confidence_text} "
        f"reliable={reliable}"
    )

    return best_offset if best_offset is not None else 0, reliable, confidence


def summarize_window(window: int, rows: list[tuple[int, bool, float | None]]) -> None:
    distribution = collections.Counter(offset for offset, _, _ in rows)
    if not distribution:
        print(f"Window {window}: no results")
        return

    sorted_offsets = sorted(distribution.items(), key=lambda item: (-item[1], item[0]))
    print(f"\nWindow {window} offset distribution:")
    for offset, count in sorted_offsets:
        print(f"  {format_offset(offset):>4} : {count} symbols")

    plus11_count = distribution.get(11, 0)
    reliable_count = sum(1 for _, reliable, _ in rows if reliable)
    confidences = [confidence for _, _, confidence in rows if confidence is not None]
    average_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    print(f"  number of symbols whose best offset is +11: {plus11_count}")
    print(f"  number of symbols with reliable=True: {reliable_count}")
    print(f"  average confidence: {average_confidence:.6f}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnostic experiment for TypeNames context matching in Bank 09."
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

    typename_symbols_list = typename_symbols(symbols)
    if not typename_symbols_list:
        print("No TypeNames symbols found in bank 09.")
        return 1

    target_bank = target_rom.bytes(0x09, bank_start(0x09), 0x4000)

    print(
        f"TypeNames context experiment: {len(typename_symbols_list)} symbols in bank 09"
    )

    all_summary: dict[int, list[tuple[int, bool, float | None]]] = collections.defaultdict(list)

    for symbol in typename_symbols_list:
        original = symbol_window(database, symbol)
        tested_windows = [original] + list(WINDOW_SIZES)

        for window in tested_windows:
            matches = best_matches_for_window(
                source_rom,
                target_bank,
                symbol,
                window,
                top=2,
            )
            best_offset, reliable, confidence = print_symbol_result(symbol, window, matches)
            all_summary[window].append((best_offset, reliable, confidence))

    for window in sorted(all_summary):
        summarize_window(window, all_summary[window])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
