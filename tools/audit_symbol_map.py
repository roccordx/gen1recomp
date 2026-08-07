import json
from collections import Counter

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

    boundaries = BoundaryDetector().analyze_rom(analysis)

    normalized = SegmentNormalizer().normalize_rom(boundaries)

    quality = BankQualityAnalyzer().analyze_rom(normalized)

    resolver = AddressResolver(
        analysis,
        normalized,
        quality,
    )

    generated = SymbolMapGenerator(
        symbols,
        resolver,
    ).generate()

    generated_names = {
        s.name
        for s in generated.symbols
    }

    reasons = Counter()

    print()
    print("=" * 80)
    print("UNRESOLVED SYMBOLS")
    print("=" * 80)

    for symbol in symbols.all_symbols():

        if symbol.name in generated_names:
            continue

        bank_quality = next(
            (
                b
                for b in quality.banks
                if b.bank == symbol.bank
            ),
            None,
        )

        if bank_quality is None:
            reason = "NO_BANK"

        elif not bank_quality.ready:
            reason = "BANK_NOT_READY"

        else:

            resolved = resolver.resolve(
                symbol.bank,
                symbol.address,
            )

            if not resolved.resolved:
                reason = "NO_SEGMENT"

            else:
                reason = "UNKNOWN"

        reasons[reason] += 1

    print()

    total = len(symbols.all_symbols())

    print(f"Total symbols     : {total}")
    print(f"Generated         : {len(generated.symbols)}")
    print(f"Missing           : {total-len(generated.symbols)}")

    print()
    print("-" * 80)

    for reason, count in reasons.most_common():

        print(
            f"{reason:20s}"
            f"{count:8d}"
        )


if __name__ == "__main__":
    main()