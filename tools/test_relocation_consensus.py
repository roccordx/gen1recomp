#!/usr/bin/env python3

"""Diagnostic experiment for relocation consensus among Bank 09 TypeNames."""

from __future__ import annotations

import argparse
import collections
import json
from dataclasses import dataclass
from typing import Iterable

from matcher import MatchResult, SymbolMatcher, SymbolMatch, find_best_matches, raw_similarity
from rom_data import RomImage, SymbolTable, Symbol
from symbol_database import SymbolDatabase

BANK = 0x09
CANDIDATE_TOP = 10
NEIGHBOR_RADIUS = 2


@dataclass(frozen=True)
class CandidateSupport:
    candidate_offset: int
    focal_score: float
    focal_rank: int
    supporting_neighbors: list[str]
    neighbor_details: list[tuple[str, int, float, float | None]]
    support_count: int
    normalized_support: float
    confidence_weighted_support: float
    rank_weighted_support: float


def load_manifest(path: str) -> dict:
    with open(path, encoding="utf8") as source:
        return json.load(source)


def bank_start(bank: int) -> int:
    return 0x0000 if bank == 0 else 0x4000


def typename_symbols(symbols: SymbolTable) -> list[Symbol]:
    return [
        symbol
        for symbol in symbols.prefixed("TypeNames.")
        if symbol.bank == BANK
    ]


def symbol_window(database: SymbolDatabase, symbol: Symbol) -> int:
    return database.window(symbol, fallback=128)


def format_offset(offset: int | None) -> str:
    return f"{offset:+d}" if offset is not None else "None"


def format_score(score: float | None) -> str:
    return f"{score:.6f}" if score is not None else "None"


def find_symbol_index(bank_symbols: list[Symbol], symbol: Symbol) -> int | None:
    for index, candidate in enumerate(bank_symbols):
        if candidate.bank == symbol.bank and candidate.address == symbol.address:
            return index
    return None


def select_neighbors(bank_symbols: list[Symbol], index: int) -> list[Symbol]:
    previous_symbols = bank_symbols[max(0, index - NEIGHBOR_RADIUS) : index]
    next_symbols = bank_symbols[index + 1 : index + 1 + NEIGHBOR_RADIUS]
    return previous_symbols + next_symbols


def contextual_match(
    matcher: SymbolMatcher,
    symbol: Symbol,
    window: int,
) -> SymbolMatch:
    source_data = matcher.source.bytes(symbol.bank, symbol.address, window)
    target_bank = matcher.target.bytes(symbol.bank, bank_start(symbol.bank), 0x4000)
    matches = find_best_matches(source_data, target_bank, raw_similarity, limit=CANDIDATE_TOP)

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

    return SymbolMatch(symbol=symbol, window=window, results=results)


def compute_candidate_support(
    focal_match,
    focal_symbol: Symbol,
    neighbor_symbols: list[Symbol],
    matcher: SymbolMatcher,
    target_bank: bytes,
) -> list[CandidateSupport]:
    focal_candidates: list[tuple[int, float, int]] = []

    for rank, result in enumerate(focal_match.results, start=1):
        focal_candidates.append((result.offset, result.score, rank))

    neighbor_matches = {}
    for neighbor in neighbor_symbols:
        neighbor_match = contextual_match(
            matcher,
            neighbor,
            symbol_window(matcher.database, neighbor),
        )
        neighbor_matches[neighbor.name] = neighbor_match

    candidate_supports: list[CandidateSupport] = []
    neighbor_count = len(neighbor_symbols)

    for candidate_offset, focal_score, focal_rank in focal_candidates:
        supporting_neighbors = []
        neighbor_details = []
        confidence_weighted_support = 0.0
        rank_weighted_support = 0.0

        for neighbor in neighbor_symbols:
            neighbor_match = neighbor_matches[neighbor.name]
            neighbor_offset_ranks = [result.offset for result in neighbor_match.results]
            if candidate_offset in neighbor_offset_ranks:
                neighbor_index = neighbor_offset_ranks.index(candidate_offset)
                neighbor_rank = neighbor_index + 1
                neighbor_best = neighbor_match.best
                neighbor_best_offset = neighbor_best.offset if neighbor_best is not None else None
                neighbor_best_score = neighbor_best.score if neighbor_best is not None else 0.0
                neighbor_confidence = neighbor_match.confidence
                supporting_neighbors.append(neighbor.name)
                neighbor_details.append(
                    (
                        neighbor.name,
                        neighbor_rank,
                        neighbor_best_score,
                        neighbor_confidence,
                    )
                )
                confidence_weighted_support += max(neighbor_confidence or 0.0, 0.0)
                rank_weighted_support += 1.0 / neighbor_rank

        support_count = len(supporting_neighbors)
        normalized_support = support_count / neighbor_count if neighbor_count else 0.0

        candidate_supports.append(
            CandidateSupport(
                candidate_offset=candidate_offset,
                focal_score=focal_score,
                focal_rank=focal_rank,
                supporting_neighbors=supporting_neighbors,
                neighbor_details=neighbor_details,
                support_count=support_count,
                normalized_support=normalized_support,
                confidence_weighted_support=confidence_weighted_support,
                rank_weighted_support=rank_weighted_support,
            )
        )

    return candidate_supports


def print_candidate_support(
    symbol: Symbol,
    focal_match,
    candidate_supports: list[CandidateSupport],
    database: SymbolDatabase,
) -> None:
    print("\nFocal symbol:", symbol.name)
    print(
        f"  source={symbol.bank:02X}:${symbol.address:04X}"
        f" window={symbol_window(database, symbol)}"
    )
    print(
        f"  focal best offset={format_offset(focal_match.best.offset if focal_match.best is not None else None)}"
        f" focal confidence={format_score(focal_match.confidence)}"
    )

    support_sorted = sorted(
        candidate_supports,
        key=lambda support: (-support.support_count, -support.confidence_weighted_support, support.candidate_offset),
    )

    for candidate in support_sorted:
        print(
            f"  candidate offset={format_offset(candidate.candidate_offset)}"
            f" focal score={format_score(candidate.focal_score)}"
            f" focal rank={candidate.focal_rank}"
            f" support_count={candidate.support_count}"
            f" normalized_support={candidate.normalized_support:.3f}"
            f" confidence_weighted_support={candidate.confidence_weighted_support:.6f}"
            f" rank_weighted_support={candidate.rank_weighted_support:.6f}"
        )
        print(f"    neighbors={candidate.supporting_neighbors}")
        for neighbor_name, neighbor_rank, neighbor_score, neighbor_confidence in candidate.neighbor_details:
            print(
                f"      {neighbor_name}:"
                f" rank={neighbor_rank}"
                f" score={format_score(neighbor_score)}"
                f" confidence={format_score(neighbor_confidence)}"
            )

    plus11 = next(
        (candidate for candidate in candidate_supports if candidate.candidate_offset == 11),
        None,
    )
    if plus11 is not None:
        if plus11.support_count >= 3:
            support_phrase = "strong neighbor support"
        elif plus11.support_count >= 1:
            support_phrase = "weak neighbor support"
        else:
            support_phrase = "no neighbor support"
        print(
            f"  candidate +11: {support_phrase}"
            f" (support_count={plus11.support_count},"
            f" normalized={plus11.normalized_support:.3f},"
            f" confidence_weighted={plus11.confidence_weighted_support:.6f})"
        )
    else:
        print("  candidate +11: not present in focal top 10 results")


def summarize_focal(
    symbol: Symbol,
    focal_match,
    candidate_supports: list[CandidateSupport],
) -> tuple[str, dict[str, object]]:
    if not candidate_supports:
        return symbol.name, {
            "best_offset": None,
            "confidence": focal_match.confidence,
            "strongest_offset": None,
            "support_count": 0,
            "normalized_support": 0.0,
            "confidence_weighted_support": 0.0,
            "rank_weighted_support": 0.0,
        }

    strongest_by_support = max(
        candidate_supports,
        key=lambda candidate: (
            candidate.support_count,
            candidate.confidence_weighted_support,
            candidate.rank_weighted_support,
        ),
    )

    return symbol.name, {
        "best_offset": strongest_by_support.candidate_offset,
        "confidence": focal_match.confidence,
        "strongest_offset": strongest_by_support.candidate_offset,
        "support_count": strongest_by_support.support_count,
        "normalized_support": strongest_by_support.normalized_support,
        "confidence_weighted_support": strongest_by_support.confidence_weighted_support,
        "rank_weighted_support": strongest_by_support.rank_weighted_support,
    }


def print_summary(summaries: dict[str, dict[str, object]]) -> None:
    print("\nSUMMARY")
    for symbol_name, summary in summaries.items():
        print(
            f"{symbol_name}:"
            f" best_offset={format_offset(summary['best_offset'])}"
            f" confidence={format_score(summary['confidence'])}"
            f" strongest_offset={format_offset(summary['strongest_offset'])}"
            f" support_count={summary['support_count']}"
            f" normalized_support={summary['normalized_support']:.3f}"
            f" confidence_weighted_support={summary['confidence_weighted_support']:.6f}"
            f" rank_weighted_support={summary['rank_weighted_support']:.6f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnostic relocation consensus experiment for Bank 09 TypeNames."
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
    matcher = SymbolMatcher(
        RomImage(args.source_rom, expected_sha1=None),
        RomImage(args.target_rom, expected_sha1=None),
        database,
    )

    typename_list = typename_symbols(symbols)
    if not typename_list:
        print("No TypeNames symbols found in bank 09.")
        return 1

    print(f"TypeNames relocation consensus experiment: {len(typename_list)} focal symbols")

    bank_symbols = [symbols[info.name] for info in database.bank(BANK)]

    summaries: dict[str, dict[str, object]] = {}
    focal_count = 0

    for symbol in typename_list:
        index = find_symbol_index(bank_symbols, symbol)
        if index is None:
            continue

        focal_match = contextual_match(
            matcher,
            symbol,
            symbol_window(database, symbol),
        )
        if focal_match.reliable or focal_match.exact:
            continue

        focal_count += 1
        neighbors = select_neighbors(bank_symbols, index)
        print(f"\n--- focal symbol={symbol.name} ({len(neighbors)} neighbors) ---")

        candidate_supports = compute_candidate_support(
            focal_match,
            symbol,
            neighbors,
            matcher,
            matcher.target.bytes(BANK, bank_start(BANK), 0x4000),
        )
        print_candidate_support(symbol, focal_match, candidate_supports, database)

        _, summary = summarize_focal(symbol, focal_match, candidate_supports)
        summaries[symbol.name] = summary

        support_sorted = sorted(
            candidate_supports,
            key=lambda candidate: (-candidate.support_count, candidate.candidate_offset),
        )
        print("\n  candidates sorted by support count descending:")
        for candidate in support_sorted:
            print(
                f"    {format_offset(candidate.candidate_offset)} support_count={candidate.support_count}"
            )

        confidence_sorted = sorted(
            candidate_supports,
            key=lambda candidate: (-candidate.confidence_weighted_support, candidate.candidate_offset),
        )
        print("\n  candidates sorted by confidence-weighted support descending:")
        for candidate in confidence_sorted:
            print(
                f"    {format_offset(candidate.candidate_offset)}"
                f" confidence_weighted_support={candidate.confidence_weighted_support:.6f}"
            )

    print_summary(summaries)
    print(f"\nFocal symbols tested: {focal_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
