import json

from analyzer import RomAnalyzer
from boundary_detector import BoundaryDetector
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

    for bank in boundaries.banks:

        if not bank.segments:
            continue

        print()
        print("=" * 80)
        print(f"BANK {bank.bank:02X}")
        print("=" * 80)

        for i, segment in enumerate(bank.segments, start=1):

            print()

            print(f"Segment {i}")

            print(
                f"${segment.start:04X} - ${segment.end:04X}"
            )

            print(
                f"Offset {segment.offset:+}"
            )

            print(
                f"Symbols {len(segment.symbols)}"
            )


if __name__ == "__main__":
    main()