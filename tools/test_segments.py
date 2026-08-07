import json

from analyzer import RomAnalyzer
from boundary_detector import BoundaryDetector
from segment_normalizer import SegmentNormalizer
from bank_quality_analyzer import BankQualityAnalyzer

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

    print()
    print(f"Normalized banks : {len(normalized.banks)}")
    print(f"Quality banks    : {len(quality.banks)}")
    print()

    quality_map = {
        q.bank: q
        for q in quality.banks
    }

    for bank in normalized.banks:

        q = quality_map.get(bank.bank)

        print("=" * 72)

        if q is None:
            print(f"Bank {bank.bank:02X} -> NO QUALITY")
            continue

        print(
            f"Bank {bank.bank:02X} "
            f"| READY={q.ready} "
            f"| Quality={q.quality:.2%}"
        )

        print(
            f"Segments: {len(bank.segments)}"
        )

        structural = 0
        outlier = 0

        for segment in bank.segments:

            if segment.structural:
                structural += 1
            else:
                outlier += 1

        print(
            f"Structural: {structural}"
        )

        print(
            f"Outlier   : {outlier}"
        )

        print()

        for i, segment in enumerate(bank.segments):

            print(
                f"{i:03d} "
                f"${segment.start:04X}-${segment.end:04X} "
                f"off={segment.offset:+6d} "
                f"structural={segment.structural} "
                f"outlier={segment.outlier} "
                f"symbols={len(segment.symbols)}"
            )

        print()


if __name__ == "__main__":
    main()