#!/usr/bin/env python3

import csv
import re
from pathlib import Path
from collections import defaultdict

ROM = Path("red-ita.gb")
MAPPING = Path("tools/bank20_mapping.tsv")
PASS5 = Path("tools/pass5_sequence_analysis.tsv")

OUT = Path("tools/pass5_pointer_verification.txt")
TSV = Path("tools/pass5_pointer_verification.tsv")

BANK = 0x20
BANK_BASE = 0x4000


def parse_bank_addr(value):
    if not value or ":" not in value:
        return None

    bank, offset = value.strip().split(":", 1)

    try:
        return int(bank, 16), int(offset, 16)
    except ValueError:
        return None


def parse_cpu_addr(value):
    if not value:
        return None

    try:
        return int(value.strip(), 16)
    except ValueError:
        return None


def cpu_to_bank_offset(addr):
    if 0x4000 <= addr <= 0x7FFF:
        return BANK, addr - BANK_BASE

    return None


def bank_offset_to_rom_offset(bank, offset):
    if bank == 0:
        return offset

    return bank * 0x4000 + offset


def read_u16(rom, offset):
    if offset < 0 or offset + 1 >= len(rom):
        return None

    return rom[offset] | (rom[offset + 1] << 8)


def pointer_value_to_bank_offset(value):
    """
    GB pointer in the $4000-$7FFF window.
    """
    if value is None:
        return None

    if not (0x4000 <= value <= 0x7FFF):
        return None

    return BANK, value - BANK_BASE


def load_mapping():
    with MAPPING.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_candidates():
    with PASS5.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    # Only the candidates that actually survived into the
    # Bank 0x20 sequence analysis.
    by_symbol = defaultdict(list)

    for row in rows:

        candidate = parse_bank_addr(row["candidate"])

        if candidate is None:
            continue

        by_symbol[row["symbol"]].append(row)

    return by_symbol


def find_raw_pointers(rom, bank, offset):
    """
    Search the complete ROM for little-endian 16-bit values
    pointing to the candidate address in Bank 0x20.

    This is intentionally broad. It is evidence collection,
    not automatic mapping.
    """

    target = BANK_BASE + offset

    lo = target & 0xFF
    hi = (target >> 8) & 0xFF

    hits = []

    for i in range(len(rom) - 1):

        if rom[i] == lo and rom[i + 1] == hi:

            hits.append({
                "rom_offset": i,
                "bank": i // 0x4000,
                "offset": i % 0x4000,
            })

    return hits


def context_bytes(rom, pos, radius=12):
    start = max(0, pos - radius)
    end = min(len(rom), pos + radius + 2)

    return " ".join(
        f"{b:02X}"
        for b in rom[start:end]
    )


def classify_pointer_location(hit):
    bank = hit["bank"]
    offset = hit["offset"]

    # Bank 0x20 itself is particularly interesting because
    # references may occur in data/text structures.
    if bank == BANK:
        return "BANK20"

    # ROM0 contains common code/data.
    if bank == 0:
        return "ROM0"

    return "OTHER_BANK"


def main():

    rom = ROM.read_bytes()

    mapping = load_mapping()
    candidates = load_candidates()

    mapping_by_symbol = {
        row["usa_symbol"]: row
        for row in mapping
    }

    # ------------------------------------------------------------
    # Only candidates that are actually Bank 0x20 candidates.
    # ------------------------------------------------------------

    target_candidates = []

    for symbol, rows in candidates.items():

        for row in rows:

            addr = parse_bank_addr(row["candidate"])

            if addr is None:
                continue

            if addr[0] != BANK:
                continue

            target_candidates.append({
                "symbol": symbol,
                "candidate": row["candidate"],
                "offset": addr[1],
                "score": row["total_score"],
                "classification": row["classification"],
            })

    # ------------------------------------------------------------
    # Search pointer references.
    # ------------------------------------------------------------

    results = []

    for candidate in target_candidates:

        hits = find_raw_pointers(
            rom,
            BANK,
            candidate["offset"],
        )

        for hit in hits:

            results.append({
                "symbol": candidate["symbol"],
                "candidate": candidate["candidate"],
                "score": candidate["score"],
                "classification": candidate["classification"],
                "pointer_rom_bank": hit["bank"],
                "pointer_rom_offset": f"{hit['offset']:04X}",
                "pointer_rom_location":
                    f"{hit['bank']:02X}:{hit['offset']:04X}",
                "pointer_context":
                    context_bytes(rom, hit["rom_offset"]),
                "location_class":
                    classify_pointer_location(hit),
            })

    # ------------------------------------------------------------
    # TSV
    # ------------------------------------------------------------

    fields = [
        "symbol",
        "candidate",
        "score",
        "classification",
        "pointer_rom_bank",
        "pointer_rom_offset",
        "pointer_rom_location",
        "location_class",
        "pointer_context",
    ]

    with TSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            delimiter="\t",
        )

        writer.writeheader()
        writer.writerows(results)

    # ------------------------------------------------------------
    # Report
    # ------------------------------------------------------------

    grouped = defaultdict(list)

    for row in results:
        grouped[
            (row["symbol"], row["candidate"])
        ].append(row)

    with OUT.open("w", encoding="utf-8") as f:

        f.write(
            "PASS 5.2 — POINTER/CALLSITE VERIFICATION\n"
        )
        f.write("=" * 90 + "\n\n")

        f.write(
            f"ROM size                         : "
            f"{len(rom):,} bytes\n"
        )

        f.write(
            f"Bank 0x20 candidates             : "
            f"{len(target_candidates)}\n"
        )

        f.write(
            f"Candidates with pointer hits     : "
            f"{sum(1 for k, v in grouped.items() if v)}\n"
        )

        f.write(
            f"Total raw pointer hits           : "
            f"{len(results)}\n\n"
        )

        for symbol, candidate in sorted(grouped):

            rows = grouped[(symbol, candidate)]

            f.write("\n")
            f.write("=" * 90 + "\n")
            f.write(f"{symbol}\n")
            f.write("=" * 90 + "\n")

            first = rows[0]

            f.write(
                f"Candidate       : {candidate}\n"
            )

            f.write(
                f"PASS3 score     : {first['score']}\n"
            )

            f.write(
                f"Classification  : {first['classification']}\n"
            )

            f.write(
                f"Pointer hits    : {len(rows)}\n\n"
            )

            for row in rows:

                f.write(
                    f"  {row['pointer_rom_location']} "
                    f"[{row['location_class']}]\n"
                )

                f.write(
                    f"    {row['pointer_context']}\n"
                )

    # ------------------------------------------------------------
    # Console summary.
    # ------------------------------------------------------------

    print()
    print("PASS 5.2 — POINTER/CALLSITE VERIFICATION")
    print("=" * 55)
    print(
        f"Bank 0x20 candidates         : "
        f"{len(target_candidates)}"
    )
    print(
        f"Candidates with pointer hits : "
        f"{sum(1 for k, v in grouped.items() if v)}"
    )
    print(
        f"Total raw pointer hits       : "
        f"{len(results)}"
    )
    print()
    print(f"Report: {OUT}")
    print(f"TSV   : {TSV}")


if __name__ == "__main__":
    main()
