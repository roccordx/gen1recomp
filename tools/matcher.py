from __future__ import annotations

from dataclasses import dataclass

from rom_data import RomImage, Symbol
from symbol_database import SymbolDatabase


def raw_similarity(source: bytes, candidate: bytes) -> float:
    """Return the fraction of bytes that are identical in two windows."""

    if len(source) != len(candidate):
        raise ValueError("source and candidate windows must have the same length")
    if not source:
        return 1.0

    return sum(a == b for a, b in zip(source, candidate)) / len(source)


MATCHERS = {"raw": raw_similarity}


def find_best_matches(source: bytes, target: bytes, matcher, limit: int = 10):
    """Score every target window and return the best ``(score, offset)`` pairs."""

    if limit < 1:
        return []
    if not source or len(source) > len(target):
        return []

    matches = [
        (matcher(source, target[offset:offset + len(source)]), offset)
        for offset in range(len(target) - len(source) + 1)
    ]
    return sorted(matches, key=lambda match: (-match[0], match[1]))[:limit]


@dataclass(frozen=True)
class MatchResult:
    score: float
    address: int
    offset: int


@dataclass(frozen=True)
class SymbolMatch:
    symbol: Symbol
    window: int
    results: list[MatchResult]

    @property
    def best(self) -> MatchResult | None:
        if not self.results:
            return None
        return self.results[0]

    @property
    def confidence(self) -> float | None:
        """
        Restituisce quanto il miglior risultato è superiore
        al secondo classificato.

        Più il valore è alto, maggiore è la confidenza
        del matching.
        """

        if len(self.results) < 2:
            return None

        return self.results[0].score - self.results[1].score


class SymbolMatcher:

    def __init__(
        self,
        source: RomImage,
        target: RomImage,
        database: SymbolDatabase,
    ):
        self.source = source
        self.target = target
        self.database = database

    def find(
        self,
        symbol: Symbol,
        matcher_name: str = "raw",
        top: int = 10,
        fallback_window: int = 128,
    ) -> SymbolMatch:

        window = self.database.window(
            symbol,
            fallback=fallback_window,
        )

        source_data = self.source.bytes(
            symbol.bank,
            symbol.address,
            window,
        )

        bank_start = 0x0000 if symbol.bank == 0 else 0x4000

        target_bank = self.target.bytes(
            symbol.bank,
            bank_start,
            0x4000,
        )

        matcher = MATCHERS[matcher_name]

        matches = find_best_matches(
            source_data,
            target_bank,
            matcher,
            limit=top,
        )

        results = []

        for score, offset in matches:

            cpu_address = bank_start + offset

            results.append(
                MatchResult(
                    score=score,
                    address=cpu_address,
                    offset=cpu_address - symbol.address,
                )
            )

        return SymbolMatch(
            symbol=symbol,
            window=window,
            results=results,
        )