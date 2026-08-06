import json

from analyzer import RomAnalyzer
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

    for bank in analysis.banks:

        if not bank.matches:
            continue

        print()
        print("=" * 80)
        print(f"BANK {bank.bank:02X}")
        print("=" * 80)
        print()

        ordered = sorted(
            bank.matches,
            key=lambda m: m.match.symbol.address,
        )

        last_offset = None

        for symbol in ordered:

            best = symbol.match.best

            if best is None:
                continue

            offset = best.offset

            if last_offset is not None and offset != last_offset:
                print("-" * 80)

            print(
                f"${symbol.match.symbol.address:04X}  "
                f"{symbol.name:40} "
                f"{offset:+5d}   "
                f"{best.score * 100:6.2f}%"
            )

            last_offset = offset


if __name__ == "__main__":
    main()