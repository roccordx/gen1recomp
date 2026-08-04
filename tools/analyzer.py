from __future__ import annotations

from analysis import (
    BankAnalysis,
    RomAnalysis,
    SymbolAnalysis,
)
from matcher import SymbolMatcher
from rom_data import RomImage, SymbolTable
from symbol_database import SymbolDatabase


class RomAnalyzer:

    def __init__(
        self,
        source: RomImage,
        target: RomImage,
        symbols: SymbolTable,
        database: SymbolDatabase,
    ):
        self.symbols = symbols
        self.database = database

        self.matcher = SymbolMatcher(
            source,
            target,
            database,
        )

    def scan_bank(
        self,
        bank: int,
        matcher_name: str = "raw",
        top: int = 5,
    ) -> BankAnalysis:

        analysis = BankAnalysis(bank=bank)

        score_sum = 0.0
        score_count = 0

        confidence_sum = 0.0
        confidence_count = 0

        for info in self.database.bank(bank):

            symbol = self.symbols[info.name]

            result = self.matcher.find(
                symbol,
                matcher_name=matcher_name,
                top=top,
            )

            analysis.matches.append(
                SymbolAnalysis(
                    name=info.name,
                    match=result,
                )
            )

            analysis.total += 1

            if result.reliable:
                analysis.reliable += 1
            else:
                analysis.review += 1

            best = result.best

            if best is not None:
                score_sum += best.score
                score_count += 1

            if result.confidence is not None:
                confidence_sum += result.confidence
                confidence_count += 1

            if result.reliable:
                analysis.relocations[result.relocation].append(info.name)

        if score_count:
            analysis.average_score = score_sum / score_count

        if confidence_count:
            analysis.average_confidence = (
                confidence_sum / confidence_count
            )

        return analysis

    def scan_rom(
        self,
        matcher_name: str = "raw",
        top: int = 5,
    ) -> RomAnalysis:

        analysis = RomAnalysis()

        for bank in sorted(self.database._banks.keys()):

            analysis.banks.append(
                self.scan_bank(
                    bank,
                    matcher_name=matcher_name,
                    top=top,
                )
            )

        return analysis