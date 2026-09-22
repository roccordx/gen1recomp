#!/usr/bin/env python3

import csv
from collections import defaultdict

AUDIT = "tools/pass6_5_manifest_corpus_audit.tsv"
GLOBAL = "tools/italian_global_mapping.tsv"
OUT = "tools/pass6_5_5_mapping_collision_audit.tsv"

# ------------------------------------------------------------
# Load existing global mapping
# ------------------------------------------------------------

existing_by_symbol = {}
existing_by_address = defaultdict(list)

with open(GLOBAL, encoding="utf-8") as f:
    for row in csv.DictReader(f, delimiter="\t"):
        symbol = row["usa_symbol"].strip()
        address = row["ita_address"].strip().upper()

        existing_by_symbol[symbol] = address
        existing_by_address[address].append(symbol)

# ------------------------------------------------------------
# Load 181 corpus-resolved runtime gaps
# ------------------------------------------------------------

candidates = []

with open(AUDIT, encoding="utf-8") as f:
    for row in csv.DictReader(f, delimiter="\t"):
        if row["classification"] != "CORPUS_ROM_RESOLVED":
            continue

        candidates.append(row)

# ------------------------------------------------------------
# Analyze
# ------------------------------------------------------------

new_symbols = []
already_present = []
address_collisions = []
internal_collisions = []

candidate_by_address = defaultdict(list)

for row in candidates:
    symbol = row["symbol"]
    address = row["resolved_address"].strip().upper()

    candidate_by_address[address].append(symbol)

    if symbol in existing_by_symbol:
        already_present.append(
            (symbol, address, existing_by_symbol[symbol])
        )
        continue

    occupants = existing_by_address.get(address, [])

    if occupants:
        address_collisions.append(
            (symbol, address, occupants)
        )
    else:
        new_symbols.append((symbol, address))

for address, symbols in candidate_by_address.items():
    if len(symbols) > 1:
        internal_collisions.append((address, symbols))

# ------------------------------------------------------------
# Write detailed report
# ------------------------------------------------------------

fieldnames = [
    "symbol",
    "address",
    "status",
    "existing_symbol",
]

rows = []

for symbol, address in new_symbols:
    rows.append({
        "symbol": symbol,
        "address": address,
        "status": "NEW_SAFE",
        "existing_symbol": "",
    })

for symbol, address, existing in already_present:
    rows.append({
        "symbol": symbol,
        "address": address,
        "status": "ALREADY_PRESENT",
        "existing_symbol": existing,
    })

for symbol, address, occupants in address_collisions:
    rows.append({
        "symbol": symbol,
        "address": address,
        "status": "ADDRESS_COLLISION",
        "existing_symbol": ",".join(occupants),
    })

for address, symbols in internal_collisions:
    for symbol in symbols:
        rows.append({
            "symbol": symbol,
            "address": address,
            "status": "INTERNAL_COLLISION",
            "existing_symbol": ",".join(
                s for s in symbols if s != symbol
            ),
        })

with open(OUT, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
        delimiter="\t",
    )
    writer.writeheader()
    writer.writerows(rows)

# ------------------------------------------------------------
# Console output
# ------------------------------------------------------------

print()
print("PASS 6.5.5 - GLOBAL MAPPING COLLISION AUDIT")
print("=" * 60)

print(f"Corpus-resolved candidates : {len(candidates)}")
print(f"New safe mappings          : {len(new_symbols)}")
print(f"Already present            : {len(already_present)}")
print(f"Address collisions         : {len(address_collisions)}")
print(f"Internal collisions        : {len(internal_collisions)}")

print()
print("NEW SAFE MAPPINGS")
print("-" * 60)

for symbol, address in new_symbols:
    print(f"{symbol}\t{address}")

print()
print("ALREADY PRESENT")
print("-" * 60)

for symbol, address, existing in already_present:
    print(
        f"{symbol}: candidate={address} "
        f"existing={existing}"
    )

print()
print("ADDRESS COLLISIONS")
print("-" * 60)

for symbol, address, occupants in address_collisions:
    print(
        f"{symbol}: {address} already occupied by "
        f"{', '.join(occupants)}"
    )

print()
print("INTERNAL COLLISIONS")
print("-" * 60)

for address, symbols in internal_collisions:
    print(
        f"{address}: {', '.join(symbols)}"
    )

print()
print(f"Output: {OUT}")
print("DONE")
