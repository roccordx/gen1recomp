#!/usr/bin/env python3

import csv
import re
from pathlib import Path

AUDIT = Path("tools/pass6_4_manifest_audit.tsv")
REPORT = Path("tools/italian_text_manifest_report.txt")
OUT = Path("tools/pass6_5_manifest_corpus_audit.tsv")

runtime_rows = []
with AUDIT.open(encoding="utf-8") as f:
    runtime_rows = list(csv.DictReader(f, delimiter="\t"))

runtime = {
    row["symbol"]: row
    for row in runtime_rows
}

text = REPORT.read_text(encoding="utf-8")

resolved = {}

pattern = re.compile(
    r"^(_[A-Za-z0-9_]+Text[A-Za-z0-9_]*)\s+"
    r"(rb\.[^\s]+)\s+"
    r"([0-9A-Fa-f]{2}:[0-9A-Fa-f]{4})\s+"
    r"len=(\d+)\s+"
    r"wildcards=(\d+)",
    re.MULTILINE,
)

for m in pattern.finditer(text):
    symbol = m.group(1)
    resolved[symbol] = {
        "qid": m.group(2),
        "address": m.group(3).upper(),
        "length": m.group(4),
        "wildcards": m.group(5),
        "status": "CORPUS_ROM_RESOLVED",
    }

# Symbols explicitly reported as having no full-ROM match.
no_full_rom = set(
    re.findall(
        r"^(_[A-Za-z0-9_]+Text[A-Za-z0-9_]*)\s+"
        r"(rb\.[^\s]+)\s+no full-ROM match",
        text,
        re.MULTILINE,
    )
)

rows = []

for symbol, runtime_row in sorted(runtime.items()):
    manifest_addr = runtime_row.get("ita_manifest_address", "").strip().upper()

    if symbol in resolved:
        r = resolved[symbol]
        resolved_addr = r["address"]

        if manifest_addr == resolved_addr:
            relation = "MANIFEST_EQUALS_RESOLVED"
        else:
            relation = "MANIFEST_DIFFERS_RESOLVED"

        rows.append({
            "symbol": symbol,
            "runtime_status": runtime_row.get("status", ""),
            "manifest_address": manifest_addr,
            "resolved_address": resolved_addr,
            "relation": relation,
            "qid": r["qid"],
            "length": r["length"],
            "wildcards": r["wildcards"],
            "classification": "CORPUS_ROM_RESOLVED",
        })

    elif symbol in no_full_rom:
        rows.append({
            "symbol": symbol,
            "runtime_status": runtime_row.get("status", ""),
            "manifest_address": manifest_addr,
            "resolved_address": "",
            "relation": "",
            "qid": "",
            "length": "",
            "wildcards": "",
            "classification": "NO_FULL_ROM_MATCH",
        })

    else:
        rows.append({
            "symbol": symbol,
            "runtime_status": runtime_row.get("status", ""),
            "manifest_address": manifest_addr,
            "resolved_address": "",
            "relation": "",
            "qid": "",
            "length": "",
            "wildcards": "",
            "classification": "NOT_IN_GENERATOR_REPORT",
        })

fieldnames = [
    "symbol",
    "runtime_status",
    "manifest_address",
    "resolved_address",
    "relation",
    "qid",
    "length",
    "wildcards",
    "classification",
]

with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)

from collections import Counter

counts = Counter(row["classification"] for row in rows)
relations = Counter(
    row["relation"]
    for row in rows
    if row["classification"] == "CORPUS_ROM_RESOLVED"
)

print()
print("PASS 6.5.4 - MANIFEST / CORPUS CROSS-AUDIT")
print("=" * 60)
print(f"Runtime gaps analyzed       : {len(rows)}")
print(f"CORPUS_ROM_RESOLVED         : {counts['CORPUS_ROM_RESOLVED']}")
print(f"  manifest == resolved      : {relations['MANIFEST_EQUALS_RESOLVED']}")
print(f"  manifest != resolved      : {relations['MANIFEST_DIFFERS_RESOLVED']}")
print(f"NO_FULL_ROM_MATCH           : {counts['NO_FULL_ROM_MATCH']}")
print(f"NOT_IN_GENERATOR_REPORT     : {counts['NOT_IN_GENERATOR_REPORT']}")
print()
print(f"Output                      : {OUT}")
print()

print("RESOLVED + ADDRESS DIFFERENCES")
print("-" * 60)

for row in rows:
    if row["relation"] == "MANIFEST_DIFFERS_RESOLVED":
        print(
            f"{row['symbol']}: "
            f"manifest={row['manifest_address']} "
            f"resolved={row['resolved_address']} "
            f"qid={row['qid']}"
        )

print()
print("NO FULL-ROM MATCH")
print("-" * 60)

for row in rows:
    if row["classification"] == "NO_FULL_ROM_MATCH":
        print(row["symbol"])

print()
print("DONE")
