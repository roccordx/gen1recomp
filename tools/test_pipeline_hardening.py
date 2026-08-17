#!/usr/bin/env python3

"""Synthetic regression tests for the Italian ROM analysis hardening."""

from __future__ import annotations

import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from address_resolver import AddressResolver
from analysis import (
    BankAnalysis,
    BankBoundaryAnalysis,
    BankQualityAnalysis,
    BoundarySegment,
    RomAnalysis,
    RomNormalizedAnalysis,
    RomQualityAnalysis,
    SymbolAnalysis,
)
from bank_quality_analyzer import BankQualityAnalyzer
from boundary_detector import BoundaryDetector
from compare_roms import compare_bank, main as compare_roms_main
from matcher import MatchResult, SymbolMatch
from rom_data import ROM_BANK_SIZE, RomImage, Symbol
from segment_normalizer import SegmentNormalizer


def make_match(name: str, address: int, results: list[tuple[float, int]]) -> SymbolMatch:
    symbol = Symbol(1, address, name)
    return SymbolMatch(
        symbol=symbol,
        window=16,
        results=[
            MatchResult(score=score, address=address + offset, offset=offset)
            for score, offset in results
        ],
    )


def test_match_validation_requires_absolute_score_and_confidence() -> None:
    perfect = make_match("Perfect", 0x4000, [(1.0, 0), (0.20, 8)])
    ambiguous = make_match("Ambiguous", 0x4010, [(0.92, 4), (0.80, 8)])
    weak = make_match("Weak", 0x4020, [(0.40, 4), (0.05, 12)])
    single = make_match("Single", 0x4030, [(1.0, 0)])

    assert perfect.reliable
    assert perfect.exact
    assert not ambiguous.reliable
    assert not weak.reliable
    assert not single.reliable


def test_boundary_uses_only_reliable_matches_and_preserves_duplicate_offsets() -> None:
    bank = BankAnalysis(bank=1)
    for index, address in enumerate((0x4000, 0x4010, 0x4020)):
        name = f"Strong{index}"
        bank.matches.append(
            SymbolAnalysis(name, make_match(name, address, [(0.95, 7), (0.10, 99)]))
        )
    bank.matches.append(
        SymbolAnalysis("Weak", make_match("Weak", 0x4030, [(0.40, 7), (0.05, 99)]))
    )
    bank.matches.append(
        SymbolAnalysis("Other", make_match("Other", 0x4040, [(0.95, 11), (0.10, 99)]))
    )

    detected = BoundaryDetector().analyze_bank(bank)

    assert [segment.symbols for segment in detected.segments] == [
        ["Strong0", "Strong1", "Strong2"],
        ["Other"],
    ]


def test_normalizer_quality_and_resolver_gate_on_structural_ready_segments() -> None:
    normalized = SegmentNormalizer().normalize_bank(
        BankBoundaryAnalysis(
            bank=1,
            segments=[
                BoundarySegment(
                    0x4000,
                    0x4080,
                    7,
                    ["A", "B", "C", "D", "E", "F", "G", "H", "I"],
                ),
                BoundarySegment(0x4100, 0x4100, 99, ["Outlier"]),
            ],
        )
    )
    assert normalized.segments[0].structural and not normalized.segments[0].outlier
    assert normalized.segments[1].outlier and not normalized.segments[1].structural

    ready_quality = BankQualityAnalyzer().analyze_bank(normalized)
    assert ready_quality.ready

    resolver = AddressResolver(
        RomAnalysis(),
        RomNormalizedAnalysis([normalized]),
        RomQualityAnalysis([ready_quality]),
    )
    assert resolver.resolve(1, 0x4010).resolved
    assert not resolver.resolve(1, 0x4100).resolved
    assert not resolver.resolve(1, 0x4200).resolved

    non_ready_quality = BankQualityAnalysis(1, 1, 0, 1, 1, 0, 1, 0.0, False)
    non_ready_resolver = AddressResolver(
        RomAnalysis(),
        RomNormalizedAnalysis([normalized]),
        RomQualityAnalysis([non_ready_quality]),
    )
    assert not non_ready_resolver.resolve(1, 0x4010).resolved


def test_non_reliable_matches_cannot_make_bank_ready() -> None:
    bank = BankAnalysis(bank=1)
    for index, address in enumerate((0x4000, 0x4010, 0x4020, 0x4030)):
        name = f"Weak{index}"
        bank.matches.append(
            SymbolAnalysis(name, make_match(name, address, [(0.40, 5), (0.05, 12)]))
        )

    boundaries = BoundaryDetector().analyze_bank(bank)
    normalized = SegmentNormalizer().normalize_bank(boundaries)
    quality = BankQualityAnalyzer().analyze_bank(normalized)

    assert boundaries.segments == []
    assert not quality.ready
    assert quality.total_symbols == 0


def test_rom_bytes_clamps_matching_window_at_bank_boundary() -> None:
    data = bytes([0xAA]) * ROM_BANK_SIZE + bytes([0xBB]) * ROM_BANK_SIZE
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        rom = RomImage(path, expected_sha1=None)
        window = rom.bytes(0, 0x3FF0, 128)
        assert len(window) == 16
        assert set(window) == {0xAA}
    finally:
        Path(path).unlink()


def test_compare_roms_uses_all_available_banks() -> None:
    data = bytes([0x11]) * (ROM_BANK_SIZE * 33)
    with (
        tempfile.NamedTemporaryFile(delete=False) as usa_tmp,
        tempfile.NamedTemporaryFile(delete=False) as ita_tmp,
    ):
        usa_tmp.write(data)
        ita_tmp.write(data)
        usa_path = usa_tmp.name
        ita_path = ita_tmp.name
    try:
        usa = RomImage(usa_path, expected_sha1=None)
        ita = RomImage(ita_path, expected_sha1=None)
        assert usa.bank_count == 33
        equal, total, percent, *_ = compare_bank(usa, ita, 32)
        assert equal == ROM_BANK_SIZE
        assert total == ROM_BANK_SIZE
        assert percent == 100.0
    finally:
        Path(usa_path).unlink()
        Path(ita_path).unlink()


def test_compare_roms_reports_different_bank_counts() -> None:
    with (
        tempfile.NamedTemporaryFile(delete=False) as usa_tmp,
        tempfile.NamedTemporaryFile(delete=False) as ita_tmp,
    ):
        usa_tmp.write(bytes([0x11]) * (ROM_BANK_SIZE * 2))
        ita_tmp.write(bytes([0x11]) * ROM_BANK_SIZE)
        usa_path = usa_tmp.name
        ita_path = ita_tmp.name
    try:
        import sys

        original_argv = sys.argv
        sys.argv = [
            "compare_roms.py",
            "--source",
            usa_path,
            "--target",
            ita_path,
        ]
        output = StringIO()
        try:
            with redirect_stdout(output):
                compare_roms_main()
        finally:
            sys.argv = original_argv

        text = output.getvalue()
        assert "[WARN] ROM bank count differs" in text
        assert "source=2 target=1" in text
    finally:
        Path(usa_path).unlink()
        Path(ita_path).unlink()


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_"):
            func()
    print("ok")
