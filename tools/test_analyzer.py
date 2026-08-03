from analyzer import RomAnalyzer
from rom_data import RomImage, SymbolTable
from symbol_database import SymbolDatabase

import json

with open("tools/rom_manifest.json", encoding="utf8") as f:
    manifest = json.load(f)

symbols = SymbolTable(manifest["symbols"])
db = SymbolDatabase(manifest["symbols"])

usa = RomImage("red-usa.gb", expected_sha1=None)
ita = RomImage("red-ita.gb", expected_sha1=None)

analyzer = RomAnalyzer(
    usa,
    ita,
    symbols,
    db,
)

analysis = analyzer.scan_bank(6)

print(f"Bank {analysis.bank:02X}")
print()

print(f"Total      : {analysis.total}")
print(f"Reliable   : {analysis.reliable}")
print(f"Review     : {analysis.review}")
print(f"Avg score  : {analysis.average_score * 100:.2f}%")
print(f"Avg conf   : {analysis.average_confidence * 100:.2f}%")

print()
print("Relocations")
print("-----------")

for reloc, names in sorted(analysis.relocations.items()):
    print(f"{reloc:+4d} : {len(names):2d}")

print()
print("First symbols")
print("-------------")

for symbol in analysis.matches[:10]:

    print(
        f"{symbol.name:35}"
        f"{symbol.relocation:+6d}"
        f"{symbol.score * 100:9.2f}%"
    )