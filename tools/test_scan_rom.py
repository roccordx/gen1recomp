import json

from analyzer import RomAnalyzer
from rom_data import RomImage, SymbolTable
from symbol_database import SymbolDatabase

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

analysis = analyzer.scan_rom()

print(f"Banks     : {len(analysis.banks)}")
print(f"Symbols   : {analysis.total_symbols}")
print(f"Reliable  : {analysis.reliable_symbols}")
print(f"Review    : {analysis.review_symbols}")