#!/usr/bin/env python3

"""Diagnostic experiment for Bank 09 TypeNames group context matching."""

from __future__ import annotations

import argparse
import collections
import json
from typing import Optional

from matcher import MatchResult, SymbolMatcher, SymbolMatch, find_best_matches, raw_similarity
from rom_data import RomImage, SymbolTable, Symbol
from symbol_database import SymbolDatabase

CONTEXT_WINDOWS = (32, 64, 128)
BANK = 0x09
TOP_RESULTS = 2
LOCAL_RADIUS = 2


def load_manifest(path: str) -> dict:
    with open(path, encoding="utf8") as source:
        return json.load(source)


def typename_group(symbols: SymbolTable) -> list[Symbol]:
    return [
        symbol
        for symbol in symbols.prefixed("TypeNames.")
        if symbol.bank == BANK
    ]


def format_offset(offset: Optional[int]) -> str:
    return f"{offset:+d}" if offset is not None else "None"


def format_score(value: Optional[float]) -> str:
    return f"{value:.6f}" if value is not None else "None"


def bank_start(bank: int) -> int:
    return 0x0000 if bank == 0 else 0x4000


def contextual_match(
    matcher: SymbolMatcher,
    symbol: Symbol,
    window: int,
) -> tuple[Optional[int], float, Optional[float], Optional[float]]:
    source_data = matcher.source.bytes(symbol.bank, symbol.address, window)
    target_bank = matcher.target.bytes(symbol.bank, bank_start(symbol.bank), 0x4000)
    matches = find_best_matches(source_data, target_bank, raw_similarity, limit=TOP_RESULTS)

    results: list[MatchResult] = []
    for score, offset in matches:
        cpu_address = bank_start(symbol.bank) + offset
        results.append(
            MatchResult(
                score=score,
                address=cpu_address,
                offset=cpu_address - symbol.address,
            )
        )

    match = SymbolMatch(symbol=symbol, window=window, results=results)
    best = match.best
    second = match.second
    best_offset = None
    best_score = 0.0
    second_score = None
    confidence = None

    if best is not None:
        best_offset = best.offset
        best_score = best.score
    if second is not None:
        second_score = second.score
    if best is not None and second_score is not None:
        confidence = best_score - second_score

    return best_offset, best_score, second_score, confidence


def print_symbol_context(
    symbol: Symbol,
    window: int,
    best_offset: Optional[int],
    best_score: float,
    second_score: Optional[float],
    confidence: Optional[float],
) -> None:
    print(
        f"symbol={symbol.name}"
        f" source={symbol.bank:02X}:${symbol.address:04X}"
        f" window={window}"
        f" best_offset={format_offset(best_offset)}"
        f" best_score={format_score(best_score)}"
        f" second_score={format_score(second_score)}"
        f" confidence={format_score(confidence)}"
    )


def local_group(symbols: list[Symbol], index: int) -> list[Symbol]:
    return symbols[max(0, index - LOCAL_RADIUS) : index + LOCAL_RADIUS + 1]


def summarize_distribution(distribution: collections.Counter, total: int) -> None:
    print("\nOffset distribution:")
    for offset, count in sorted(distribution.items(), key=lambda item: (-item[1], item[0])):
        percent = count / total * 100
        print(f"  {format_offset(offset):>7} : {count:3} symbols ({percent:5.1f}%)")


def analyze_group(symbols: list[Symbol], matcher: SymbolMatcher) -> None:
    for window in CONTEXT_WINDOWS:
        print(f"\n=== context window {window} ===")
        results = []
        distribution = collections.Counter()
        plus11_count = 0

        for symbol in symbols:
            best_offset, best_score, second_score, confidence = contextual_match(
                matcher,
                symbol,
                window,
            )
            print_symbol_context(symbol, window, best_offset, best_score, second_score, confidence)
            results.append((symbol, best_offset, best_score, second_score, confidence))
            if best_offset is not None:
                distribution[best_offset] += 1
                if best_offset == 11:
                    plus11_count += 1

        print(f"\nWindow {window} group distribution ({len(symbols)} symbols):")
        summarize_distribution(distribution, len(symbols))

        max_count = max(distribution.values()) if distribution else 0
        largest_offsets = [offset for offset, count in distribution.items() if count == max_count]
        largest_offsets_text = ", ".join(format_offset(offset) for offset in sorted(largest_offsets))
        print(
            f"largest cluster: {largest_offsets_text} with {max_count} symbols"
        )
        print(f"count choosing +11: {plus11_count}\n")

        print("Local consensus per focal symbol:")
        for index, (symbol, best_offset, _, _, _) in enumerate(results):
            group = local_group(symbols, index)
            same_count = sum(
                1 for neighbor in group if contextual_match(matcher, neighbor, window)[0] == best_offset
            )
            print(
                f"  symbol={symbol.name}"
                f" best_offset={format_offset(best_offset)}"
                f" local_group_size={len(group)}"
                f" matching_neighbors={same_count}"
                f" local_consensus_ratio={same_count / len(group):.3f}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnostic group context matching experiment for Bank 09 TypeNames."
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
    group = typename_group(symbols)
    if not group:
        print("No TypeNames symbols found in bank 09.")
        return 1

    matcher = SymbolMatcher(
        RomImage(args.source_rom, expected_sha1=None),
        RomImage(args.target_rom, expected_sha1=None),
        SymbolDatabase(manifest["symbols"]),
    )

    analyze_group(group, matcher)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
