#!/usr/bin/env python3

"""Regression tests for SymbolMatcher group-context fallback behavior."""

from __future__ import annotations

import sys

from matcher import MatchResult, SymbolMatch, SymbolMatcher
from rom_data import Symbol
from symbol_database import SymbolDatabase

ROM_BANK_SIZE = 0x4000


class FakeSymbolDatabase(SymbolDatabase):
    def __init__(self, symbols_data: dict[str, list[int]], windows: dict[str, int]):
        super().__init__(symbols_data)
        self._windows = windows

    def window(self, symbol: Symbol, fallback: int) -> int:
        return self._windows.get(symbol.name, fallback)


class StubSymbolMatcher(SymbolMatcher):
    def __init__(self, database: FakeSymbolDatabase, stub_matches: dict[str, dict[int, SymbolMatch]]):
        super().__init__(DummyRom(b""), DummyRom(b""), database)
        self.stub_matches = stub_matches
        self.calls: list[tuple[str, int]] = []

    def _find(
        self,
        symbol: Symbol,
        window: int,
        matcher_name: str,
        top: int,
    ) -> SymbolMatch:
        self.calls.append((symbol.name, window))
        symbol_matches = self.stub_matches.get(symbol.name)
        if symbol_matches is None:
            raise AssertionError(
                f"Missing stub matches for {symbol.name}"
            )
        if window not in symbol_matches:
            return SymbolMatch(symbol=symbol, window=window, results=[])
        return symbol_matches[window]


def make_symbol_match(
    symbol: Symbol,
    window: int,
    results: list[tuple[float, int]],
) -> SymbolMatch:
    if len(results) == 1:
        score, offset = results[0]
        results = [(score, offset), (0.0, offset + 0x100)]

    return SymbolMatch(
        symbol=symbol,
        window=window,
        results=[
            MatchResult(
                score=score,
                address=symbol.address + offset,
                offset=offset,
            )
            for score, offset in results
        ],
    )


class DummyRom:
    def __init__(self, data: bytes):
        self.data = data

    def bytes(self, bank: int, address: int, length: int) -> bytes:
        if bank == 0:
            offset = address
        else:
            offset = bank * ROM_BANK_SIZE + (address - 0x4000)
        return self.data[offset : offset + length]


def rom_offset(bank: int, address: int) -> int:
    if bank == 0:
        return address
    return bank * ROM_BANK_SIZE + (address - 0x4000)


def build_pattern(base: int, length: int) -> bytes:
    return bytes(((base + i) & 0xFF) for i in range(length))


def test_group_fallback_selects_consensus() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020, 0x4030, 0x4040]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4020, "Symbol2")
    natural_window = 16
    first_context = 32
    second_context = 64
    consensus_offset = 11

    stub_matches = {}
    for name, location in symbols.items():
        symbol = Symbol(bank, location[1], name)
        stub_matches[name] = {
            natural_window: make_symbol_match(symbol, natural_window, [(0.25, 0)]),
            first_context: make_symbol_match(symbol, first_context, [(0.3, 0)]),
            second_context: make_symbol_match(symbol, second_context, [(0.3, 0)]),
        }

    stub_matches["Symbol1"][first_context] = make_symbol_match(
        Symbol(bank, 0x4010, "Symbol1"),
        first_context,
        [(0.42, 11)],
    )
    stub_matches["Symbol3"][first_context] = make_symbol_match(
        Symbol(bank, 0x4030, "Symbol3"),
        first_context,
        [(0.45, 11)],
    )
    stub_matches["Symbol4"][first_context] = make_symbol_match(
        Symbol(bank, 0x4040, "Symbol4"),
        first_context,
        [(0.5, 20)],
    )
    stub_matches["Symbol0"][second_context] = make_symbol_match(
        Symbol(bank, 0x4000, "Symbol0"),
        second_context,
        [(0.7, consensus_offset)],
    )
    stub_matches["Symbol1"][second_context] = make_symbol_match(
        Symbol(bank, 0x4010, "Symbol1"),
        second_context,
        [(0.75, consensus_offset)],
    )
    stub_matches["Symbol2"][second_context] = make_symbol_match(
        focal,
        second_context,
        [(0.85, consensus_offset)],
    )
    stub_matches["Symbol3"][second_context] = make_symbol_match(
        Symbol(bank, 0x4030, "Symbol3"),
        second_context,
        [(0.65, consensus_offset)],
    )
    stub_matches["Symbol4"][second_context] = make_symbol_match(
        Symbol(bank, 0x4040, "Symbol4"),
        second_context,
        [(0.5, 20)],
    )

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)
    windows = {window for _, window in matcher.calls}

    assert match.best is not None, "expected a best match"
    assert match.best.offset == consensus_offset, "group consensus should choose +11"
    assert match.window == second_context, "context should progress to 64 and stop"
    assert 32 in windows, "search should try 32 first"
    assert 64 in windows, "search should try 64 when 32 fails"
    assert 128 not in windows, "search should stop after 64 succeeds"


def test_exact_primary_preserves_original() -> None:
    bank = 1
    addresses = [
        0x4000,
        0x4040,
        0x4080,
        0x40C0,
        0x4100,
        0x4140,
        0x4180,
    ]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }

    source_data = bytearray(ROM_BANK_SIZE * 2)
    target_data = bytearray(ROM_BANK_SIZE * 2)

    for idx, address in enumerate(addresses):
        source_bytes = build_pattern(0x20 * idx + 1, 16)
        source_offset = rom_offset(bank, address)
        source_data[source_offset : source_offset + 16] = source_bytes

        if address == 0x4100:
            exact_target = source_bytes
            target_data[rom_offset(bank, address) : rom_offset(bank, address) + 16] = exact_target
            target_data[rom_offset(bank, address + 0x10) : rom_offset(bank, address + 0x10) + 16] = b"\xFF" * 16
        else:
            wrong_target = bytearray(source_bytes[:12] + b"\xFF" * 4)
            target_data[rom_offset(bank, address) : rom_offset(bank, address) + 16] = wrong_target
            adjusted_target = bytearray(source_bytes[:12])
            adjusted_target += b"\xFE" * 4
            target_data[rom_offset(bank, address + 11) : rom_offset(bank, address + 11) + 16] = adjusted_target

    matcher = SymbolMatcher(
        DummyRom(bytes(source_data)),
        DummyRom(bytes(target_data)),
        FakeSymbolDatabase(symbols, {name: 16 for name in symbols}),
    )

    exact_symbol = Symbol(bank, 0x4100, "Symbol4")
    match = matcher.find(exact_symbol, top=10)

    assert match.best is not None, "expected a best match for exact symbol"
    assert match.best.offset == 0, "exact primary match should preserve the original location"
    assert match.window == 16, "exact primary match should not fall back to a larger window"
    assert match.exact, "primary match should be exact"


def test_strong_consensus_accepts_contextual_result() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4010, "Symbol1")
    natural_window = 16
    context_window = 32
    consensus_offset = 11

    stub_matches = {
        "Symbol0": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4000, "Symbol0"),
                natural_window,
                [(0.5, 0)],
            ),
            context_window: make_symbol_match(
                Symbol(bank, 0x4000, "Symbol0"),
                context_window,
                [(0.7, consensus_offset)],
            ),
        },
        "Symbol1": {
            natural_window: make_symbol_match(
                focal,
                natural_window,
                [(0.5, 0), (0.4, consensus_offset)],
            ),
            context_window: make_symbol_match(
                focal,
                context_window,
                [(0.9, consensus_offset), (0.4, 0)],
            ),
        },
        "Symbol2": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4020, "Symbol2"),
                natural_window,
                [(0.5, 0)],
            ),
            context_window: make_symbol_match(
                Symbol(bank, 0x4020, "Symbol2"),
                context_window,
                [(0.8, consensus_offset)],
            ),
        },
    }

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)

    assert match.best is not None
    assert match.best.offset == consensus_offset
    assert match.window == context_window


def test_weak_focal_no_consensus_preserves_primary() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4010, "Symbol1")
    natural_window = 16
    context_window = 32

    stub_matches = {
        "Symbol0": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4000, "Symbol0"),
                natural_window,
                [(0.5, 0)],
            ),
            context_window: make_symbol_match(
                Symbol(bank, 0x4000, "Symbol0"),
                context_window,
                [(0.7, 11)],
            ),
        },
        "Symbol1": {
            natural_window: make_symbol_match(
                focal,
                natural_window,
                [(0.5, 0), (0.4, 11)],
            ),
            context_window: make_symbol_match(
                focal,
                context_window,
                [(0.8, 11), (0.4, 0)],
            ),
        },
        "Symbol2": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4020, "Symbol2"),
                natural_window,
                [(0.5, 0)],
            ),
            context_window: make_symbol_match(
                Symbol(bank, 0x4020, "Symbol2"),
                context_window,
                [(0.7, 20)],
            ),
        },
    }

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)

    assert match.best is not None
    assert match.best.offset == 0
    assert match.window == natural_window


def test_single_neighbor_does_not_form_consensus() -> None:
    bank = 1
    addresses = [0x4000, 0x4010]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4010, "Symbol1")
    natural_window = 16
    context_window = 32

    stub_matches = {
        "Symbol0": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4000, "Symbol0"),
                natural_window,
                [(0.5, 0)],
            ),
            context_window: make_symbol_match(
                Symbol(bank, 0x4000, "Symbol0"),
                context_window,
                [(0.7, 11)],
            ),
        },
        "Symbol1": {
            natural_window: make_symbol_match(
                focal,
                natural_window,
                [(0.6, 0), (0.5, 11)],
            ),
            context_window: make_symbol_match(
                focal,
                context_window,
                [(0.8, 11)],
            ),
        },
    }

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)

    assert match.best is not None
    assert match.best.offset == 0
    assert match.window == natural_window


def test_two_neighbors_support_accepts_context() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4010, "Symbol1")
    natural_window = 16
    context_window = 32
    consensus_offset = 11

    stub_matches = {
        "Symbol0": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4000, "Symbol0"),
                natural_window,
                [(0.4, 0)],
            ),
            context_window: make_symbol_match(
                Symbol(bank, 0x4000, "Symbol0"),
                context_window,
                [(0.7, consensus_offset)],
            ),
        },
        "Symbol1": {
            natural_window: make_symbol_match(
                focal,
                natural_window,
                [(0.4, 0)],
            ),
            context_window: make_symbol_match(
                focal,
                context_window,
                [(0.8, consensus_offset)],
            ),
        },
        "Symbol2": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4020, "Symbol2"),
                natural_window,
                [(0.4, 0)],
            ),
            context_window: make_symbol_match(
                Symbol(bank, 0x4020, "Symbol2"),
                context_window,
                [(0.7, consensus_offset)],
            ),
        },
    }

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)

    assert match.best is not None
    assert match.best.offset == consensus_offset
    assert match.window == context_window


def test_competing_relocation_is_rejected() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020, 0x4030, 0x4040]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4020, "Symbol2")
    natural_window = 16
    context_window = 32

    stub_matches = {}
    for name, location in symbols.items():
        symbol = Symbol(bank, location[1], name)
        natural_result = make_symbol_match(symbol, natural_window, [(0.4, 0)])
        context_result = make_symbol_match(symbol, context_window, [(0.7, 11)])
        stub_matches[name] = {
            natural_window: natural_result,
            context_window: context_result,
        }

    # override neighbor support to create a tie
    stub_matches["Symbol0"][context_window] = make_symbol_match(
        Symbol(bank, 0x4000, "Symbol0"),
        context_window,
        [(0.7, 11)],
    )
    stub_matches["Symbol1"][context_window] = make_symbol_match(
        Symbol(bank, 0x4010, "Symbol1"),
        context_window,
        [(0.7, 11)],
    )
    stub_matches["Symbol3"][context_window] = make_symbol_match(
        Symbol(bank, 0x4030, "Symbol3"),
        context_window,
        [(0.8, 20)],
    )
    stub_matches["Symbol4"][context_window] = make_symbol_match(
        Symbol(bank, 0x4040, "Symbol4"),
        context_window,
        [(0.8, 20)],
    )

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)

    assert match.best is not None
    assert match.best.offset == 0
    assert match.window == natural_window


def test_clear_majority_is_accepted() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020, 0x4030, 0x4040]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4020, "Symbol2")
    natural_window = 16
    context_window = 32
    consensus_offset = 11

    stub_matches = {}
    for name, location in symbols.items():
        symbol = Symbol(bank, location[1], name)
        natural_result = make_symbol_match(symbol, natural_window, [(0.4, 0)])
        stub_matches[name] = {
            natural_window: natural_result,
            context_window: make_symbol_match(symbol, context_window, [(0.8, 20)]),
        }

    # three neighbors support focal offset, one supports a different offset
    stub_matches["Symbol0"][context_window] = make_symbol_match(
        Symbol(bank, 0x4000, "Symbol0"),
        context_window,
        [(0.7, consensus_offset)],
    )
    stub_matches["Symbol1"][context_window] = make_symbol_match(
        Symbol(bank, 0x4010, "Symbol1"),
        context_window,
        [(0.7, consensus_offset)],
    )
    stub_matches["Symbol2"][context_window] = make_symbol_match(
        focal,
        context_window,
        [(0.9, consensus_offset)],
    )
    stub_matches["Symbol3"][context_window] = make_symbol_match(
        Symbol(bank, 0x4030, "Symbol3"),
        context_window,
        [(0.6, consensus_offset)],
    )
    stub_matches["Symbol4"][context_window] = make_symbol_match(
        Symbol(bank, 0x4040, "Symbol4"),
        context_window,
        [(0.7, 20)],
    )

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)

    assert match.best is not None
    assert match.best.offset == consensus_offset
    assert match.window == context_window


def test_focal_does_not_vote_is_rejected() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020, 0x4030]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4010, "Symbol1")
    natural_window = 16
    context_window = 32

    stub_matches = {
        "Symbol0": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4000, "Symbol0"),
                natural_window,
                [(0.5, 0)],
            ),
            context_window: make_symbol_match(
                Symbol(bank, 0x4000, "Symbol0"),
                context_window,
                [(0.7, 20)],
            ),
        },
        "Symbol1": {
            natural_window: make_symbol_match(
                focal,
                natural_window,
                [(0.5, 0)],
            ),
            context_window: make_symbol_match(
                focal,
                context_window,
                [(0.8, 11)],
            ),
        },
        "Symbol2": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4020, "Symbol2"),
                natural_window,
                [(0.5, 0)],
            ),
            context_window: make_symbol_match(
                Symbol(bank, 0x4020, "Symbol2"),
                context_window,
                [(0.6, 20)],
            ),
        },
        "Symbol3": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4030, "Symbol3"),
                natural_window,
                [(0.5, 0)],
            ),
            context_window: make_symbol_match(
                Symbol(bank, 0x4030, "Symbol3"),
                context_window,
                [(0.6, 21)],
            ),
        },
    }

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)

    assert match.best is not None
    assert match.best.offset == 0
    assert match.window == natural_window


def test_reliable_primary_preserves_original() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4010, "Symbol1")
    natural_window = 16

    stub_matches = {
        "Symbol0": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4000, "Symbol0"),
                natural_window,
                [(0.5, 0)],
            ),
        },
        "Symbol1": {
            natural_window: make_symbol_match(
                focal,
                natural_window,
                [(0.8, 0), (0.4, 11)],
            ),
        },
        "Symbol2": {
            natural_window: make_symbol_match(
                Symbol(bank, 0x4020, "Symbol2"),
                natural_window,
                [(0.5, 0)],
            ),
        },
    }

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)

    assert match.best is not None
    assert match.best.offset == 0
    assert match.window == natural_window
    assert all(window <= natural_window for _, window in matcher.calls)


def test_context_progression_stops_when_64_succeeds() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4010, "Symbol1")
    natural_window = 16
    first_context = 32
    second_context = 64
    consensus_offset = 11

    stub_matches = {
        "Symbol0": {
            natural_window: make_symbol_match(Symbol(bank, 0x4000, "Symbol0"), natural_window, [(0.5, 0)]),
            first_context: make_symbol_match(Symbol(bank, 0x4000, "Symbol0"), first_context, [(0.7, 20)]),
            second_context: make_symbol_match(Symbol(bank, 0x4000, "Symbol0"), second_context, [(0.7, consensus_offset)]),
        },
        "Symbol1": {
            natural_window: make_symbol_match(focal, natural_window, [(0.5, 0)]),
            first_context: make_symbol_match(focal, first_context, [(0.8, 20)]),
            second_context: make_symbol_match(focal, second_context, [(0.9, consensus_offset)]),
        },
        "Symbol2": {
            natural_window: make_symbol_match(Symbol(bank, 0x4020, "Symbol2"), natural_window, [(0.5, 0)]),
            first_context: make_symbol_match(Symbol(bank, 0x4020, "Symbol2"), first_context, [(0.6, 21)]),
            second_context: make_symbol_match(Symbol(bank, 0x4020, "Symbol2"), second_context, [(0.8, consensus_offset)]),
        },
    }

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)
    windows = {window for _, window in matcher.calls}

    assert match.best is not None
    assert match.best.offset == consensus_offset
    assert match.window == second_context
    assert first_context in windows
    assert second_context in windows
    assert 128 not in windows


def test_two_neighbors_split_rejects_context() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4010, "Symbol1")
    natural_window = 16
    context_window = 32

    stub_matches = {
        "Symbol0": {
            natural_window: make_symbol_match(Symbol(bank, 0x4000, "Symbol0"), natural_window, [(0.5, 0)]),
            context_window: make_symbol_match(Symbol(bank, 0x4000, "Symbol0"), context_window, [(0.7, 7)]),
        },
        "Symbol1": {
            natural_window: make_symbol_match(focal, natural_window, [(0.5, 0)]),
            context_window: make_symbol_match(focal, context_window, [(0.8, 7)]),
        },
        "Symbol2": {
            natural_window: make_symbol_match(Symbol(bank, 0x4020, "Symbol2"), natural_window, [(0.5, 0)]),
            context_window: make_symbol_match(Symbol(bank, 0x4020, "Symbol2"), context_window, [(0.6, 8)]),
        },
    }

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)

    assert match.best is not None
    assert match.best.offset == 0
    assert match.window == natural_window


def test_all_contexts_fail_preserves_primary() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4010, "Symbol1")
    natural_window = 16

    stub_matches = {
        "Symbol0": {
            natural_window: make_symbol_match(Symbol(bank, 0x4000, "Symbol0"), natural_window, [(0.5, 0)]),
            32: make_symbol_match(Symbol(bank, 0x4000, "Symbol0"), 32, [(0.7, 11)]),
            64: make_symbol_match(Symbol(bank, 0x4000, "Symbol0"), 64, [(0.7, 20)]),
            128: make_symbol_match(Symbol(bank, 0x4000, "Symbol0"), 128, [(0.7, 21)]),
        },
        "Symbol1": {
            natural_window: make_symbol_match(focal, natural_window, [(0.5, 0)]),
            32: make_symbol_match(focal, 32, [(0.8, 11)]),
            64: make_symbol_match(focal, 64, [(0.8, 20)]),
            128: make_symbol_match(focal, 128, [(0.8, 21)]),
        },
        "Symbol2": {
            natural_window: make_symbol_match(Symbol(bank, 0x4020, "Symbol2"), natural_window, [(0.5, 0)]),
            32: make_symbol_match(Symbol(bank, 0x4020, "Symbol2"), 32, [(0.7, 12)]),
            64: make_symbol_match(Symbol(bank, 0x4020, "Symbol2"), 64, [(0.7, 22)]),
            128: make_symbol_match(Symbol(bank, 0x4020, "Symbol2"), 128, [(0.7, 23)]),
        },
    }

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)

    assert match.best is not None
    assert match.best.offset == 0
    assert match.window == natural_window


def test_context_confirms_primary_is_accepted() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4010, "Symbol1")
    natural_window = 16
    context_window = 32

    stub_matches = {
        "Symbol0": {
            natural_window: make_symbol_match(Symbol(bank, 0x4000, "Symbol0"), natural_window, [(0.5, 0)]),
            context_window: make_symbol_match(Symbol(bank, 0x4000, "Symbol0"), context_window, [(0.7, 0)]),
        },
        "Symbol1": {
            natural_window: make_symbol_match(focal, natural_window, [(0.5, 0)]),
            context_window: make_symbol_match(focal, context_window, [(0.8, 0)]),
        },
        "Symbol2": {
            natural_window: make_symbol_match(Symbol(bank, 0x4020, "Symbol2"), natural_window, [(0.5, 0)]),
            context_window: make_symbol_match(Symbol(bank, 0x4020, "Symbol2"), context_window, [(0.7, 0)]),
        },
    }

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)
    windows = {window for _, window in matcher.calls}

    assert match.best is not None
    assert match.best.offset == 0
    assert match.window == context_window
    assert 64 not in windows
    assert 128 not in windows


def test_consensus_requires_reliable_focal_and_neighbors() -> None:
    bank = 1
    addresses = [0x4000, 0x4010, 0x4020, 0x4030, 0x4040]
    symbols = {
        f"Symbol{i}": [bank, address]
        for i, address in enumerate(addresses)
    }
    focal = Symbol(bank, 0x4020, "Symbol2")
    natural_window = 16
    context_window = 32
    consensus_offset = 11

    stub_matches = {}
    for name, location in symbols.items():
        symbol = Symbol(bank, location[1], name)
        stub_matches[name] = {
            natural_window: make_symbol_match(symbol, natural_window, [(0.5, 0)]),
            context_window: make_symbol_match(
                symbol,
                context_window,
                [(0.4, consensus_offset), (0.0, 0)],
            ),
        }

    stub_matches["Symbol2"][context_window] = make_symbol_match(
        focal,
        context_window,
        [(0.9, consensus_offset), (0.8, 0)],
    )

    matcher = StubSymbolMatcher(
        FakeSymbolDatabase(symbols, {name: natural_window for name in symbols}),
        stub_matches,
    )

    match = matcher.find(focal, top=10)

    assert match.best is not None
    assert match.best.offset == 0
    assert match.window == natural_window


def main() -> int:
    tests = [
        test_group_fallback_selects_consensus,
        test_exact_primary_preserves_original,
        test_strong_consensus_accepts_contextual_result,
        test_weak_focal_no_consensus_preserves_primary,
        test_single_neighbor_does_not_form_consensus,
        test_two_neighbors_support_accepts_context,
        test_competing_relocation_is_rejected,
        test_two_neighbors_split_rejects_context,
        test_clear_majority_is_accepted,
        test_focal_does_not_vote_is_rejected,
        test_reliable_primary_preserves_original,
        test_context_progression_stops_when_64_succeeds,
        test_all_contexts_fail_preserves_primary,
        test_context_confirms_primary_is_accepted,
        test_consensus_requires_reliable_focal_and_neighbors,
    ]
    for test in tests:
        test_name = test.__name__
        try:
            test()
        except AssertionError as exc:
            print(f"FAIL {test_name}: {exc}")
            return 1
    print("PASS: matcher group-context fallback regression tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
