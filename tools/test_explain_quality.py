import json

from analyzer import RomAnalyzer
from boundary_detector import BoundaryDetector
from segment_normalizer import SegmentNormalizer
from bank_quality_analyzer import BankQualityAnalyzer
from explain_quality import QualityExplainer

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

    explanation = QualityExplainer().explain(
        quality
    )

    ready = 0

    print()

    for bank in explanation.banks:

        if bank.ready:
            ready += 1

        print("=" * 70)

        print(f"Bank {bank.bank:02X}")

        print(f"READY                : {'YES' if bank.ready else 'NO'}")
        print(f"Quality              : {bank.quality:6.2%}")

        print(
            f"Segments             : "
            f"{bank.structural_segments}/{bank.total_segments}"
        )

        print(
            f"Symbols              : "
            f"{bank.structural_symbols}/{bank.total_symbols}"
        )

        if bank.reasons:

            print()

            print("Reasons")

            for reason in bank.reasons:

                print(f"  • {reason}")

        print()

    print("=" * 70)

    print(f"READY BANKS : {ready}")
    print(f"TOTAL BANKS : {len(explanation.banks)}")

    print()


if __name__ == "__main__":
    main()