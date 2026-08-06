import json

from analyzer import RomAnalyzer
from boundary_detector import BoundaryDetector
from segment_normalizer import SegmentNormalizer
from bank_quality_analyzer import BankQualityAnalyzer
from address_resolver import AddressResolver
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

    boundaries = BoundaryDetector().analyze_rom(analysis)

    normalized = SegmentNormalizer().normalize_rom(boundaries)

    quality = BankQualityAnalyzer().analyze_rom(normalized)

    resolver = AddressResolver(
        analysis,
        normalized,
        quality,
    )

    tests = [

        (0x06, 0x4000),
        (0x06, 0x42A1),
        (0x06, 0x5B2F),
        (0x06, 0x5C06),
        (0x06, 0x6708),

    ]

    for bank, address in tests:

        result = resolver.resolve(bank, address)

        if result.resolved:

            print(
                f"Bank {bank:02X}  "
                f"${address:04X} -> ${result.target_address:04X} "
                f"(offset {result.offset:+d})"
            )

        else:

            print(
                f"Bank {bank:02X}  "
                f"${address:04X} -> NOT RESOLVED"
            )


if __name__ == "__main__":
    main()