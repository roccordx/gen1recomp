from __future__ import annotations

from analysis import (
    QualityExplanation,
    RomQualityExplanation,
)


class QualityExplainer:

    def explain(self, quality) -> RomQualityExplanation:

        result = RomQualityExplanation()

        for bank in quality.banks:

            reasons = []

            if not bank.ready:

                if bank.quality < 0.90:
                    reasons.append(
                        f"quality below threshold ({bank.quality:.2%})"
                    )

                if bank.outlier_symbols:
                    reasons.append(
                        f"{bank.outlier_symbols} outlier symbols"
                    )

                if bank.outlier_segments:
                    reasons.append(
                        f"{bank.outlier_segments} outlier segments"
                    )

            result.banks.append(

                QualityExplanation(

                    bank=bank.bank,

                    ready=bank.ready,

                    quality=bank.quality,

                    total_segments=bank.total_segments,

                    structural_segments=bank.structural_segments,

                    total_symbols=bank.total_symbols,

                    structural_symbols=bank.structural_symbols,

                    reasons=reasons,
                )

            )

        return result