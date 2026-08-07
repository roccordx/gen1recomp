from __future__ import annotations

from analysis import (
    GeneratedSymbol,
    SymbolMap,
)
from address_resolver import AddressResolver
from rom_data import SymbolTable


class SymbolMapGenerator:

    def __init__(
        self,
        symbols: SymbolTable,
        resolver: AddressResolver,
    ):
        self.symbols = symbols
        self.resolver = resolver

    def generate(self) -> SymbolMap:

        result = SymbolMap()

        for symbol in self.symbols.all_symbols():

            resolved = self.resolver.resolve(
                symbol.bank,
                symbol.address,
            )

            if not resolved.resolved:
                continue

            result.symbols.append(
                GeneratedSymbol(
                    bank=symbol.bank,
                    source_address=symbol.address,
                    target_address=resolved.target_address,
                    name=symbol.name,
                )
            )

        return result