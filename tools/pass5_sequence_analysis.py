#!/usr/bin/env python3

import csv
from pathlib import Path
from collections import defaultdict

MAPPING = Path("tools/bank20_mapping.tsv")
PASS3 = Path("tools/pass3_ambiguous_analysis.tsv")
OUT = Path("tools/pass5_sequence_analysis.txt")
TSV = Path("tools/pass5_sequence_analysis.tsv")


def parse_candidate_addr(value):
    """
    PASS 3 format:
        21:69EA
    """
    if not value:
        return None

    value = value.strip()

    if ":" not in value:
        return None

    bank, offset = value.split(":", 1)

    try:
        return int(bank, 16), int(offset, 16)
    except ValueError:
        return None


def parse_cpu_addr(value):
    """
    Mapping USA format:
        0x4045
    """
    if not value:
        return None

    value = value.strip()

    try:
        return int(value, 16)
    except ValueError:
        return None


def parse_mapping_ita(value):
    """
    Mapping ITA format:
        0x4045

    Bank 0x20 is represented in the mapping as a CPU address.
    Convert it to bank 0x20 + bank offset.
    """
    addr = parse_cpu_addr(value)

    if addr is None:
        return None

    # Bank 0x20 starts at CPU address 0x4000.
    if 0x4000 <= addr <= 0x7FFF:
        return (0x20, addr - 0x4000)

    return None


def format_bank_addr(bank, offset):
    return f"{bank:02X}:{offset:04X}"


def format_cpu_addr(addr):
    return f"0x{addr:04X}"


def load_mapping():
    with MAPPING.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_pass3():
    with PASS3.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    by_symbol = defaultdict(list)

    for row in rows:
        symbol = row["symbol"].strip()
        candidate = row["candidate"].strip()

        parsed = parse_candidate_addr(candidate)

        if parsed is None:
            continue

        by_symbol[symbol].append({
            "candidate": candidate,
            "bank": parsed[0],
            "offset": parsed[1],
            "structural_score": int(row["structural_score"]),
            "rom_score": int(row["rom_score"]),
            "total_score": int(row["total_score"]),
            "classification": row["classification"],
        })

    return by_symbol


def main():

    mapping_rows = load_mapping()
    pass3 = load_pass3()

    # ------------------------------------------------------------
    # Build the complete 254-symbol sequence from the mapping.
    # ------------------------------------------------------------

    sequence = []

    for row in mapping_rows:

        symbol = row["usa_symbol"].strip()

        usa_cpu = parse_cpu_addr(row.get("usa_address"))

        if usa_cpu is None:
            continue

        ita = parse_mapping_ita(row.get("ita_address"))

        sequence.append({
            "symbol": symbol,
            "usa_cpu": usa_cpu,
            "usa_bank": 0x20 if 0x4000 <= usa_cpu <= 0x7FFF else None,
            "usa_offset": (
                usa_cpu - 0x4000
                if 0x4000 <= usa_cpu <= 0x7FFF
                else None
            ),
            "mapping_ita": ita,
            "mapping_status": row.get("status", ""),
            "mapping_confidence": row.get("confidence", ""),
        })

    # Only Bank 0x20.
    sequence = [
        row for row in sequence
        if row["usa_bank"] == 0x20
    ]

    sequence.sort(key=lambda x: x["usa_offset"])

    ambiguous_symbols = set(pass3.keys())

    resolved = []
    ambiguous = []

    for item in sequence:

        if item["symbol"] in ambiguous_symbols:
            ambiguous.append(item)

        elif item["mapping_ita"] is not None:
            resolved.append(item)

    # ------------------------------------------------------------
    # Candidate collision index.
    # ------------------------------------------------------------

    candidate_index = defaultdict(list)

    for symbol, candidates in pass3.items():

        for c in candidates:

            key = (c["bank"], c["offset"])

            candidate_index[key].append(symbol)

    # ------------------------------------------------------------
    # Analyze ambiguous symbols.
    # ------------------------------------------------------------

    results = []

    for idx, item in enumerate(sequence):

        symbol = item["symbol"]

        if symbol not in ambiguous_symbols:
            continue

        # Previous resolved symbol.
        prev_resolved = None

        for j in range(idx - 1, -1, -1):

            candidate = sequence[j]

            if candidate["symbol"] in ambiguous_symbols:
                continue

            if candidate["mapping_ita"] is None:
                continue

            prev_resolved = candidate
            break

        # Next resolved symbol.
        next_resolved = None

        for j in range(idx + 1, len(sequence)):

            candidate = sequence[j]

            if candidate["symbol"] in ambiguous_symbols:
                continue

            if candidate["mapping_ita"] is None:
                continue

            next_resolved = candidate
            break

        for c in pass3[symbol]:

            candidate_bank = c["bank"]
            candidate_offset = c["offset"]

            prev_distance = None
            next_distance = None

            # Only meaningful when previous mapping is also Bank 0x20.
            if prev_resolved:

                prev_bank, prev_offset = prev_resolved["mapping_ita"]

                if prev_bank == candidate_bank:
                    prev_distance = (
                        candidate_offset - prev_offset
                    )

            if next_resolved:

                next_bank, next_offset = next_resolved["mapping_ita"]

                if next_bank == candidate_bank:
                    next_distance = (
                        next_offset - candidate_offset
                    )

            # Candidate collision.
            occupied_by = [
                s
                for s in candidate_index.get(
                    (candidate_bank, candidate_offset),
                    []
                )
                if s != symbol
            ]

            collision = bool(occupied_by)

            # Hard sequence compatibility.
            compatible = True

            if prev_distance is not None and prev_distance <= 0:
                compatible = False

            if next_distance is not None and next_distance <= 0:
                compatible = False

            results.append({
                "symbol": symbol,
                "usa": format_cpu_addr(item["usa_cpu"]),
                "candidate": format_bank_addr(
                    candidate_bank,
                    candidate_offset,
                ),
                "classification": c["classification"],
                "total_score": c["total_score"],
                "prev_symbol": (
                    prev_resolved["symbol"]
                    if prev_resolved else ""
                ),
                "prev_ita": (
                    format_bank_addr(*prev_resolved["mapping_ita"])
                    if prev_resolved else ""
                ),
                "prev_distance": (
                    prev_distance
                    if prev_distance is not None else ""
                ),
                "next_symbol": (
                    next_resolved["symbol"]
                    if next_resolved else ""
                ),
                "next_ita": (
                    format_bank_addr(*next_resolved["mapping_ita"])
                    if next_resolved else ""
                ),
                "next_distance": (
                    next_distance
                    if next_distance is not None else ""
                ),
                "compatible": "YES" if compatible else "NO",
                "collision": "YES" if collision else "NO",
                "occupied_by": ";".join(occupied_by),
            })

    # ------------------------------------------------------------
    # TSV
    # ------------------------------------------------------------

    fields = [
        "symbol",
        "usa",
        "candidate",
        "classification",
        "total_score",
        "prev_symbol",
        "prev_ita",
        "prev_distance",
        "next_symbol",
        "next_ita",
        "next_distance",
        "compatible",
        "collision",
        "occupied_by",
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
    # Per-symbol analysis.
    # ------------------------------------------------------------

    by_symbol = defaultdict(list)

    for row in results:
        by_symbol[row["symbol"]].append(row)

    confirmed = []
    reduced = []
    unchanged = []

    for symbol, rows in by_symbol.items():

        compatible = [
            row
            for row in rows
            if row["compatible"] == "YES"
            and row["collision"] == "NO"
        ]

        if len(compatible) == 1:

            confirmed.append(
                (symbol, compatible[0])
            )

        elif len(compatible) < len(rows):

            reduced.append(
                (symbol, len(rows), len(compatible))
            )

        else:

            unchanged.append(
                (symbol, len(rows))
            )

    # ------------------------------------------------------------
    # Report.
    # ------------------------------------------------------------

    with OUT.open("w", encoding="utf-8") as f:

        f.write(
            "PASS 5 — GLOBAL SEQUENCE ANALYSIS\n"
        )
        f.write("=" * 80 + "\n\n")

        f.write(
            f"Bank 0x20 mapping symbols       : {len(sequence)}\n"
        )

        f.write(
            f"PASS 3 ambiguous symbols        : "
            f"{len(ambiguous_symbols)}\n"
        )

        f.write(
            f"Resolved mapping symbols        : "
            f"{len(resolved)}\n"
        )

        f.write(
            f"Ambiguous symbols in sequence   : "
            f"{len(ambiguous)}\n"
        )

        f.write(
            f"Candidate rows analysed          : "
            f"{len(results)}\n"
        )

        f.write(
            f"Confirmed by hard sequence       : "
            f"{len(confirmed)}\n"
        )

        f.write(
            f"Reduced candidate set            : "
            f"{len(reduced)}\n"
        )

        f.write(
            f"Unchanged candidate sets         : "
            f"{len(unchanged)}\n"
        )

        f.write("\n")

        f.write(
            "IMPORTANT:\n"
            "No mapping was modified by PASS 5.\n"
            "Sequence compatibility is evidence only.\n\n"
        )

        if confirmed:

            f.write(
                "CONFIRMED BY SEQUENCE\n"
            )
            f.write("-" * 80 + "\n")

            for symbol, row in confirmed:

                f.write(
                    f"{symbol}\n"
                )

                f.write(
                    f"  USA       : {row['usa']}\n"
                )

                f.write(
                    f"  Candidate : {row['candidate']}\n"
                )

                f.write(
                    f"  Previous  : "
                    f"{row['prev_symbol']} "
                    f"{row['prev_ita']}\n"
                )

                f.write(
                    f"  Next      : "
                    f"{row['next_symbol']} "
                    f"{row['next_ita']}\n"
                )

                f.write(
                    f"  Distances : "
                    f"prev={row['prev_distance']} "
                    f"next={row['next_distance']}\n\n"
                )

        f.write(
            "\nREDUCED CANDIDATE SETS\n"
        )
        f.write("-" * 80 + "\n")

        for symbol, before, after in reduced:

            f.write(
                f"{symbol}: "
                f"{before} -> {after}\n"
            )

        f.write(
            "\nUNCHANGED\n"
        )
        f.write("-" * 80 + "\n")

        for symbol, count in unchanged:

            f.write(
                f"{symbol}: {count} candidates\n"
            )

    # ------------------------------------------------------------
    # Console.
    # ------------------------------------------------------------

    print()
    print("PASS 5 — GLOBAL SEQUENCE ANALYSIS")
    print("=" * 50)

    print(
        f"Bank 0x20 mapping symbols       : "
        f"{len(sequence)}"
    )

    print(
        f"PASS 3 ambiguous symbols        : "
        f"{len(ambiguous_symbols)}"
    )

    print(
        f"Resolved mapping symbols        : "
        f"{len(resolved)}"
    )

    print(
        f"Ambiguous symbols in sequence   : "
        f"{len(ambiguous)}"
    )

    print(
        f"Candidate rows analysed          : "
        f"{len(results)}"
    )

    print(
        f"Confirmed by hard sequence       : "
        f"{len(confirmed)}"
    )

    print(
        f"Reduced candidate set            : "
        f"{len(reduced)}"
    )

    print(
        f"Unchanged candidate sets         : "
        f"{len(unchanged)}"
    )

    print()
    print(f"Report: {OUT}")
    print(f"TSV   : {TSV}")


if __name__ == "__main__":
    main()
