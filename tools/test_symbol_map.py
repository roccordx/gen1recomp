import json

from analyzer import RomAnalyzer
from boundary_detector import BoundaryDetector
from segment_normalizer import SegmentNormalizer
from bank_quality_analyzer import BankQualityAnalyzer
from address_resolver import AddressResolver
from symbol_map_generator import SymbolMapGenerator

from rom_data import RomImage, SymbolTable
from symbol_database import SymbolDatabase


def main():

    with open("tools/rom_manifest.json", encoding="utf8") as f:
        manifest = json.load(f)

    symbols = SymbolTable(manifest["symbols"])

    db = SymbolDatabase(manifest["symbols"])

    usa = RomImage("red-usa.gb", expected_sha1=None)
    ita = RomImage("red-ita.gb", expected_sha1=None)

    analysis = RomAnalyzer(
        usa,
        ita,
        symbols,
        db,
    ).scan_rom()

    boundaries = BoundaryDetector().analyze_rom(
        analysis
    )

    normalized = SegmentNormalizer().normalize_rom(
        boundaries
    )

    quality = BankQualityAnalyzer().analyze_rom(
        normalized
    )

    resolver = AddressResolver(
        analysis,
        normalized,
        quality,
    )

    generated = SymbolMapGenerator(
        symbols,
        resolver,
    ).generate()

    print()
    print(f"Generated symbols: {len(generated.symbols)}")
    print()

    for symbol in generated.symbols[:50]:

        print(
            f"{symbol.bank:02X}:"
            f"{symbol.target_address:04X} "
            f"{symbol.name}"
        )


if __name__ == "__main__":
    main()