import json

from analyzer import RomAnalyzer
from boundary_detector import BoundaryDetector
from segment_normalizer import SegmentNormalizer
from rom_data import RomImage, SymbolTable
from symbol_database import SymbolDatabase


def main():

    with open("tools/rom_manifest.json", encoding="utf8") as f:
        manifest = json.load(f)

    symbols = SymbolTable(manifest["symbols"])

    db = SymbolDatabase(manifest["symbols"])

    usa = RomImage("red-usa.gb", expected_sha1=None)
    ita = RomImage("red-ita.gb", expected_sha1=None)

    rom = RomAnalyzer(
        usa,
        ita,
        symbols,
        db,
    ).scan_rom()

    boundaries = BoundaryDetector().analyze_rom(rom)

    normalized = SegmentNormalizer().normalize_rom(boundaries)

    for bank in normalized.banks:

        if not bank.segments:
            continue

        print()
        print("=" * 80)
        print(f"BANK {bank.bank:02X}")
        print("=" * 80)

        for segment in bank.segments:

            state = (
                "STRUCTURAL"
                if segment.structural
                else "OUTLIER"
            )

            print(
                f"${segment.start:04X}-${segment.end:04X}  "
                f"{segment.offset:+5d}  "
                f"{len(segment.symbols):3d} symbols  "
                f"{state}"
            )


if __name__ == "__main__":
    main()