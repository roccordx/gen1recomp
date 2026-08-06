from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from matcher import SymbolMatch


@dataclass(frozen=True)
class SymbolAnalysis:
    name: str
    match: SymbolMatch

    @property
    def best(self):
        return self.match.best

    @property
    def confidence(self):
        return self.match.confidence

    @property
    def relocation(self):
        return self.match.relocation

    @property
    def reliable(self):
        return self.match.reliable

    @property
    def score(self):
        best = self.match.best
        return best.score if best is not None else None

    @property
    def address(self):
        best = self.match.best
        return best.address if best is not None else None


@dataclass
class BankAnalysis:
    bank: int

    total: int = 0
    reliable: int = 0
    review: int = 0

    average_score: float = 0.0
    average_confidence: float = 0.0

    relocations: defaultdict[int, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )

    @property
    def average_relocation(self) -> float:

        if not self.relocations:
            return 0.0

        total = 0
        count = 0

        for reloc, names in self.relocations.items():
            total += reloc * len(names)
            count += len(names)

        return total / count if count else 0.0

    matches: list[SymbolAnalysis] = field(default_factory=list)


@dataclass
class RomAnalysis:
    banks: list[BankAnalysis] = field(default_factory=list)

    @property
    def total_symbols(self) -> int:
        return sum(bank.total for bank in self.banks)

    @property
    def reliable_symbols(self) -> int:
        return sum(bank.reliable for bank in self.banks)

    @property
    def review_symbols(self) -> int:
        return sum(bank.review for bank in self.banks)


from dataclasses import dataclass, field
@dataclass
class RelocationAnalysis:
    bank: int

    dominant_offset: int | None

    confidence: float

    reliable: int

    review: int

    offsets: dict[int, int]


@dataclass
class RomRelocationAnalysis:
    banks: list[RelocationAnalysis] = field(default_factory=list)

@dataclass
class BoundarySegment:
    start: int
    end: int
    offset: int
    symbols: list[str] = field(default_factory=list)


@dataclass
class BankBoundaryAnalysis:
    bank: int
    segments: list[BoundarySegment] = field(default_factory=list)


@dataclass
class RomBoundaryAnalysis:
    banks: list[BankBoundaryAnalysis] = field(default_factory=list)


@dataclass
class NormalizedSegment:
    start: int
    end: int

    offset: int

    symbols: list[str] = field(default_factory=list)

    structural: bool = True

    outlier: bool = False


@dataclass
class BankNormalizedAnalysis:
    bank: int
    segments: list[NormalizedSegment] = field(default_factory=list)


@dataclass
class RomNormalizedAnalysis:
    banks: list[BankNormalizedAnalysis] = field(default_factory=list)


@dataclass
class BankQualityAnalysis:
    bank: int

    total_segments: int

    structural_segments: int

    outlier_segments: int

    total_symbols: int

    structural_symbols: int

    outlier_symbols: int

    quality: float

    ready: bool


@dataclass
class RomQualityAnalysis:
    banks: list[BankQualityAnalysis] = field(default_factory=list)

    ready_banks: int = 0


@dataclass
class AddressResolution:
    bank: int

    source_address: int

    target_address: int | None

    resolved: bool

    offset: int | None


@dataclass
class RomAddressResolution:
    resolutions: list[AddressResolution] = field(default_factory=list)