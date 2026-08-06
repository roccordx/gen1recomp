from __future__ import annotations

from analysis import (
    BankBoundaryAnalysis,
    BankNormalizedAnalysis,
    BoundarySegment,
    NormalizedSegment,
    RomBoundaryAnalysis,
    RomNormalizedAnalysis,
)


class SegmentNormalizer:

    MIN_SEGMENT_SIZE = 3

    def normalize_bank(
        self,
        bank: BankBoundaryAnalysis,
    ) -> BankNormalizedAnalysis:

        result = BankNormalizedAnalysis(
            bank=bank.bank,
        )

        for segment in bank.segments:

            structural = (
                len(segment.symbols)
                >= self.MIN_SEGMENT_SIZE
            )

            result.segments.append(
                NormalizedSegment(
                    start=segment.start,
                    end=segment.end,
                    offset=segment.offset,
                    symbols=list(segment.symbols),
                    structural=structural,
                    outlier=not structural,
                )
            )

        return result

    def normalize_rom(
        self,
        analysis: RomBoundaryAnalysis,
    ) -> RomNormalizedAnalysis:

        result = RomNormalizedAnalysis()

        for bank in analysis.banks:

            result.banks.append(
                self.normalize_bank(bank)
            )

        return result