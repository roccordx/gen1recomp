from __future__ import annotations

from collections import Counter

from analysis import (
    BankAnalysis,
    RelocationAnalysis,
    RomAnalysis,
    RomRelocationAnalysis,
)


class RelocationAnalyzer:

    def analyze_bank(
        self,
        analysis: BankAnalysis,
    ) -> RelocationAnalysis:

        histogram = Counter()

        for offset, symbols in analysis.relocations.items():
            histogram[offset] = len(symbols)

        if not histogram:
            return RelocationAnalysis(
                bank=analysis.bank,
                dominant_offset=None,
                confidence=0.0,
                reliable=analysis.reliable,
                review=analysis.review,
                offsets={},
            )

        dominant_offset, dominant_count = histogram.most_common(1)[0]

        confidence = 0.0

        if analysis.reliable:
            confidence = dominant_count / analysis.reliable

        return RelocationAnalysis(
            bank=analysis.bank,
            dominant_offset=dominant_offset,
            confidence=confidence,
            reliable=analysis.reliable,
            review=analysis.review,
            offsets=dict(sorted(histogram.items())),
        )

    def analyze_rom(
        self,
        analysis: RomAnalysis,
    ) -> RomRelocationAnalysis:

        result = RomRelocationAnalysis()

        for bank in analysis.banks:
            result.banks.append(
                self.analyze_bank(bank)
            )

        return result