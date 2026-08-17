from __future__ import annotations

from dataclasses import dataclass
from heapq import nsmallest
from operator import eq
import time
from typing import ClassVar

from rom_data import RomImage, Symbol
from symbol_database import SymbolDatabase


def raw_similarity(source: bytes, candidate: bytes) -> float:
    """Return the fraction of bytes that are identical in two windows."""

    if len(source) != len(candidate):
        raise ValueError("source and candidate windows must have the same length")
    if not source:
        return 1.0

    return sum(map(eq, source, candidate)) / len(source)


MATCHERS = {"raw": raw_similarity}


_profiler = None


def _candidate_slice(target: bytes, offset: int, window: int) -> bytes:

    profiler = _profiler

    if profiler is None:
        return target[offset:offset + window]

    start = time.perf_counter()
    candidate = target[offset:offset + window]
    profiler.record_slice_creation(time.perf_counter() - start)
    return candidate

def find_best_matches(source: bytes, target: bytes, matcher, limit: int = 10):
    """Score every target window and return the best ``(score, offset)`` pairs."""

    if limit < 1:
        return []
    if not source or len(source) > len(target):
        return []

    profiler = _profiler
    window = len(source)
    candidate_count = len(target) - window + 1

    if profiler is None and matcher is raw_similarity:
        return nsmallest(
            limit,
            (
                (matcher(source, target[offset:offset + window]), offset)
                for offset in range(candidate_count)
            ),
            key=lambda match: (-match[0], match[1]),
        )

    if profiler is None:
        matches = [
            (matcher(source, target[offset:offset + window]), offset)
            for offset in range(candidate_count)
        ]
        return sorted(matches, key=lambda match: (-match[0], match[1]))[:limit]

    profiler.record_candidate_windows(candidate_count)
    candidate_start = time.perf_counter()

    matches = [
        (matcher(source, _candidate_slice(target, offset, window)), offset)
        for offset in range(candidate_count)
    ]

    profiler.record_candidate_list(time.perf_counter() - candidate_start)
    sort_start = time.perf_counter()
    results = sorted(matches, key=lambda match: (-match[0], match[1]))[:limit]
    profiler.record_sorting(time.perf_counter() - sort_start)
    return results


@dataclass(frozen=True)
class MatchResult:
    score: float
    address: int
    offset: int


@dataclass(frozen=True)
class MatchValidation:
    """Centralized thresholds for accepting an automatic symbol match.

    A match is reliable only when it has both a strong absolute score and
    enough separation from the second-best candidate.  A single candidate is
    kept for diagnostics but is not reliable because ambiguity cannot be
    measured.
    """

    MIN_BEST_SCORE: ClassVar[float] = 0.70
    MIN_CONFIDENCE: ClassVar[float] = 0.30


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

    @property
    def second(self) -> MatchResult | None:
        if len(self.results) < 2:
            return None
        return self.results[1]

    @property
    def relocation(self) -> int | None:
        best = self.best
        if best is None:
            return None
        return best.offset

    @property
    def matched(self) -> bool:
        return self.best is not None

    @property
    def exact(self) -> bool:
        best = self.best
        return best is not None and best.score == 1.0

    @property
    def reliable(self) -> bool:
        confidence = self.confidence

        if confidence is None:
            return False

        best = self.best

        if best is None:
            return False

        return (
            best.score >= MatchValidation.MIN_BEST_SCORE
            and confidence >= MatchValidation.MIN_CONFIDENCE
        )

class SymbolMatcher:

    CONTEXT_WINDOWS = (32, 64, 128)
    GROUP_RADIUS = 2

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

        natural_window = self.database.window(
            symbol,
            fallback=fallback_window,
        )

        primary = self._find(symbol, natural_window, matcher_name, top)

        if primary.reliable or primary.exact:
            return primary

        for window in self.CONTEXT_WINDOWS:
            if window <= natural_window:
                continue

            group = self._local_group(symbol, self.GROUP_RADIUS)
            group_matches = {
                member: self._find(member, window, matcher_name, top)
                for member in group
            }

            consensus_match = group_matches[symbol]
            if self._has_local_consensus(symbol, group_matches):
                return consensus_match

        return primary

    def _find(
        self,
        symbol: Symbol,
        window: int,
        matcher_name: str,
        top: int,
    ) -> SymbolMatch:

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

    def _local_group(self, symbol: Symbol, radius: int) -> list[Symbol]:
        bank_symbols = self.database.bank(symbol.bank)
        index = None

        for idx, info in enumerate(bank_symbols):
            if info.address == symbol.address and info.name == symbol.name:
                index = idx
                break

        if index is None:
            return [symbol]

        start = max(0, index - radius)
        end = min(len(bank_symbols), index + radius + 1)

        return [
            Symbol(member.bank, member.address, member.name)
            for member in bank_symbols[start:end]
        ]

    def _has_local_consensus(
        self,
        focal: Symbol,
        group_matches: dict[Symbol, SymbolMatch],
    ) -> bool:
        focal_match = group_matches.get(focal)
        if focal_match is None or focal_match.best is None or not focal_match.reliable:
            return False

        focal_offset = focal_match.best.offset
        support = sum(
            1
            for member, match in group_matches.items()
            if (
                member != focal
                and match.best is not None
                and match.reliable
                and match.best.offset == focal_offset
            )
        )

        if support < 2:
            return False

        counts: dict[int, int] = {}
        for member, match in group_matches.items():
            if member == focal or match.best is None or not match.reliable:
                continue
            offset = match.best.offset
            counts[offset] = counts.get(offset, 0) + 1

        max_other = max(
            (count for offset, count in counts.items() if offset != focal_offset),
            default=0,
        )

        if support <= max_other:
            return False

        neighbor_count = sum(
            1
            for member, match in group_matches.items()
            if member != focal and match.best is not None and match.reliable
        )

        if support <= neighbor_count / 2:
            return False

        return True
