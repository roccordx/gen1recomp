import json
import time

from analyzer import RomAnalyzer
from boundary_detector import BoundaryDetector
from segment_normalizer import SegmentNormalizer
from bank_quality_analyzer import BankQualityAnalyzer
from address_resolver import AddressResolver
from symbol_map_generator import SymbolMapGenerator

from rom_data import RomImage, SymbolTable
from symbol_database import SymbolDatabase


def print_timing(name, elapsed):
    print(f"{name:.<30}{elapsed:.2f} s")


def main():

    total_start = time.perf_counter()

    start = time.perf_counter()
    with open("tools/rom_manifest.json", encoding="utf8") as f:
        manifest = json.load(f)

    symbols = SymbolTable(manifest["symbols"])
    db = SymbolDatabase(manifest["symbols"])
    symbol_table_time = time.perf_counter() - start

    start = time.perf_counter()
    usa = RomImage("red-usa.gb", expected_sha1=None)
    ita = RomImage("red-ita.gb", expected_sha1=None)
    rom_load_time = time.perf_counter() - start

    start = time.perf_counter()
    analysis = RomAnalyzer(
        usa,
        ita,
        symbols,
        db,
    ).scan_rom()
    analyzer_time = time.perf_counter() - start

    start = time.perf_counter()
    boundaries = BoundaryDetector().analyze_rom(analysis)
    boundary_time = time.perf_counter() - start

    start = time.perf_counter()
    normalized = SegmentNormalizer().normalize_rom(boundaries)
    normalizer_time = time.perf_counter() - start

    start = time.perf_counter()
    quality = BankQualityAnalyzer().analyze_rom(normalized)
    quality_time = time.perf_counter() - start

    start = time.perf_counter()
    resolver = AddressResolver(
        analysis,
        normalized,
        quality,
    )
    resolver_time = time.perf_counter() - start

    start = time.perf_counter()
    SymbolMapGenerator(
        symbols,
        resolver,
    ).generate()
    generator_time = time.perf_counter() - start

    total_time = time.perf_counter() - total_start

    print("------------------------------------------------------------")
    print("Pipeline profiling")
    print("------------------------------------------------------------")
    print()
    print_timing("Load ROM", rom_load_time)
    print()
    print_timing("Load SymbolTable", symbol_table_time)
    print()
    print_timing("RomAnalyzer", analyzer_time)
    print()
    print_timing("BoundaryDetector", boundary_time)
    print()
    print_timing("SegmentNormalizer", normalizer_time)
    print()
    print_timing("BankQualityAnalyzer", quality_time)
    print()
    print_timing("AddressResolver", resolver_time)
    print()
    print_timing("SymbolMapGenerator", generator_time)
    print()
    print("Per-bank profiling not available.")
    print()
    print("------------------------------------------------------------")
    print()
    print_timing("TOTAL", total_time)

if __name__ == "__main__":
    main()
