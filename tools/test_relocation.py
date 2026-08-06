import json

from analyzer import RomAnalyzer
from relocation_analyzer import RelocationAnalyzer
from rom_data import RomImage, SymbolTable
from symbol_database import SymbolDatabase


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

relocations = RelocationAnalyzer().analyze_rom(analysis)

for bank in relocations.banks:

    print(f"\nBank {bank.bank:02X}")
    print("-" * 40)

    if bank.dominant_offset is None:
        print("No relocation")
        continue

    print(f"Dominant offset : {bank.dominant_offset:+}")
    print(f"Confidence      : {bank.confidence * 100:6.2f}%")
    print()

    for offset, count in bank.offsets.items():
        print(f"{offset:+5d} -> {count}")