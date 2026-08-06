import json

from analyzer import RomAnalyzer
from boundary_detector import BoundaryDetector
from bank_quality_analyzer import BankQualityAnalyzer
from rom_data import RomImage, SymbolTable
from segment_normalizer import SegmentNormalizer
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

    quality = BankQualityAnalyzer().analyze_rom(normalized)

    for bank in quality.banks:

        state = "READY" if bank.ready else "REVIEW"

        print(
            f"Bank {bank.bank:02X} | "
            f"Quality {bank.quality * 100:6.2f}% | "
            f"Structural {bank.structural_symbols:4d}/{bank.total_symbols:4d} | "
            f"{state}"
        )

    print()
    print("-" * 80)
    print(
        f"READY BANKS : {quality.ready_banks}/{len(quality.banks)}"
    )


if __name__ == "__main__":
    main()