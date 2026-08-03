from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from rom_data import Symbol


@dataclass(frozen=True)
class SymbolInfo:
    name: str
    bank: int
    address: int


class SymbolDatabase:
    def __init__(self, symbols_data: Dict[str, list]):
        self._symbols = symbols_data
        self._banks: Dict[int, List[SymbolInfo]] = {}

        for name, (bank, address) in symbols_data.items():
            self._banks.setdefault(bank, []).append(
                SymbolInfo(
                    name=name,
                    bank=bank,
                    address=address,
                )
            )

        for symbols in self._banks.values():
            symbols.sort(key=lambda s: s.address)

    # ------------------------------------------------------------
    # Query
    # ------------------------------------------------------------

    def bank(self, bank: int) -> List[SymbolInfo]:
        """
        Restituisce tutti i simboli appartenenti al bank.
        """

        return list(self._banks.get(bank, []))

    def next(self, symbol: Symbol) -> Optional[SymbolInfo]:

        bank_symbols = self._banks.get(symbol.bank)

        if bank_symbols is None:
            return None

        for index, info in enumerate(bank_symbols):

            if info.address != symbol.address:
                continue

            if index + 1 >= len(bank_symbols):
                return None

            return bank_symbols[index + 1]

        return None

    def length(self, symbol: Symbol) -> Optional[int]:

        nxt = self.next(symbol)

        if nxt is None:
            return None

        return nxt.address - symbol.address

    def window(self, symbol: Symbol, fallback: int) -> int:
        """
        Restituisce la lunghezza del simbolo.

        Se il simbolo è l'ultimo del bank,
        utilizza il fallback.
        """

        length = self.length(symbol)

        if length is None:
            return fallback

        return length