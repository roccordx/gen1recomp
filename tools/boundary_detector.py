from __future__ import annotations

from analysis import (
    BankAnalysis,
    BankBoundaryAnalysis,
    BoundarySegment,
    RomAnalysis,
    RomBoundaryAnalysis,
)


class BoundaryDetector:

    def analyze_bank(
        self,
        bank: BankAnalysis,
    ) -> BankBoundaryAnalysis:

        result = BankBoundaryAnalysis(
            bank=bank.bank,
        )

        ordered = sorted(
            bank.matches,
            key=lambda s: s.match.symbol.address,
        )

        if not ordered:
            return result

        current_offset = None
        current_start = None
        current_symbols = []

        previous_address = None

        for symbol in ordered:

            best = symbol.match.best

            if best is None:
                continue

            address = symbol.match.symbol.address
            offset = best.offset

            if current_offset is None:
                current_offset = offset
                current_start = address

            elif offset != current_offset:

                result.segments.append(
                    BoundarySegment(
                        start=current_start,
                        end=previous_address,
                        offset=current_offset,
                        symbols=current_symbols,
                    )
                )

                current_offset = offset
                current_start = address
                current_symbols = []

            current_symbols.append(symbol.name)
            previous_address = address

        result.segments.append(
            BoundarySegment(
                start=current_start,
                end=previous_address,
                offset=current_offset,
                symbols=current_symbols,
            )
        )

        return result

    def analyze_rom(
        self,
        analysis: RomAnalysis,
    ) -> RomBoundaryAnalysis:

        result = RomBoundaryAnalysis()

        for bank in analysis.banks:
            result.banks.append(
                self.analyze_bank(bank)
            )

        return result