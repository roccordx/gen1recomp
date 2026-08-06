from __future__ import annotations

from analysis import (
    BankNormalizedAnalysis,
    BankQualityAnalysis,
    RomNormalizedAnalysis,
    RomQualityAnalysis,
)


class BankQualityAnalyzer:

    READY_THRESHOLD = 0.90

    def analyze_bank(
        self,
        bank: BankNormalizedAnalysis,
    ) -> BankQualityAnalysis:

        total_segments = len(bank.segments)

        structural_segments = sum(
            1
            for segment in bank.segments
            if segment.structural
        )

        outlier_segments = total_segments - structural_segments

        total_symbols = sum(
            len(segment.symbols)
            for segment in bank.segments
        )

        structural_symbols = sum(
            len(segment.symbols)
            for segment in bank.segments
            if segment.structural
        )

        outlier_symbols = total_symbols - structural_symbols

        quality = 0.0

        if total_symbols:
            quality = structural_symbols / total_symbols

        return BankQualityAnalysis(
            bank=bank.bank,
            total_segments=total_segments,
            structural_segments=structural_segments,
            outlier_segments=outlier_segments,
            total_symbols=total_symbols,
            structural_symbols=structural_symbols,
            outlier_symbols=outlier_symbols,
            quality=quality,
            ready=quality >= self.READY_THRESHOLD,
        )

    def analyze_rom(
        self,
        analysis: RomNormalizedAnalysis,
    ) -> RomQualityAnalysis:

        result = RomQualityAnalysis()

        for bank in analysis.banks:

            quality = self.analyze_bank(bank)

            result.banks.append(quality)

            if quality.ready:
                result.ready_banks += 1

        return result