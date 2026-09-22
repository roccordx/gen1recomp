#!/usr/bin/env python3

from pathlib import Path
import re

SCORING = Path("tools/ambiguous_candidate_scoring.tsv")
ROM = Path("red-ita.gb")
MAPPING = Path("tools/bank20_mapping.tsv")

OUT_TSV = Path("tools/pass3_ambiguous_analysis.tsv")
OUT_TXT = Path("tools/pass3_ambiguous_analysis.txt")

BANK_SIZE = 0x4000
ROM_BASE = 0x4000

# ----------------------------------------------------------------------
# Codec / control bytes già calibrati nel progetto
# ----------------------------------------------------------------------

ENTRY = 0x00
DONE = 0x57
PROMPT = 0x58
END_LITERAL = 0x50

CONTROL_BYTES = {
    0x00,
    0x01,
    0x09,
    0x4F,
    0x50,
    0x51,
    0x52,
    0x54,
    0x55,
    0x57,
    0x58,
}


def parse_addr(value):
    if not value or ":" not in value:
        return None

    bank, addr = value.split(":", 1)

    try:
        return int(bank, 16), int(addr, 16)
    except ValueError:
        return None


def bank_offset(bank, addr):
    """
    Bank 0x20 address 0x4000 -> physical ROM offset.
    """
    if bank == 0:
        return addr

    return bank * BANK_SIZE + (addr - ROM_BASE)


def read_byte(data, bank, addr):
    off = bank_offset(bank, addr)

    if off < 0 or off >= len(data):
        return None

    return data[off]


def inspect_candidate(data, candidate):
    parsed = parse_addr(candidate)

    if not parsed:
        return {
            "valid": False,
            "terminal": False,
            "entry": False,
            "length": 0,
            "bytes": "",
        }

    bank, addr = parsed
    offset = bank_offset(bank, addr)

    if offset < 0 or offset >= len(data):
        return {
            "valid": False,
            "terminal": False,
            "entry": False,
            "length": 0,
            "bytes": "",
        }

    raw = data[offset:offset + 512]

    if not raw:
        return {
            "valid": False,
            "terminal": False,
            "entry": False,
            "length": 0,
            "bytes": "",
        }

    # --------------------------------------------------------------
    # Entry marker
    # --------------------------------------------------------------

    entry = raw[0] == ENTRY

    # --------------------------------------------------------------
    # Cerca terminatore.
    #
    # DONE / PROMPT sono i terminali più affidabili.
    # --------------------------------------------------------------

    terminal_pos = None
    terminal_byte = None

    for i, b in enumerate(raw[1:], start=1):

        if b in (DONE, PROMPT):
            terminal_pos = i
            terminal_byte = b
            break

        # Protezione da falsi stream enormi.
        if i >= 255:
            break

    terminal = terminal_pos is not None

    # --------------------------------------------------------------
    # Conteggio bytes "controllo"
    # --------------------------------------------------------------

    controls = []

    scan_end = terminal_pos if terminal_pos is not None else min(len(raw), 64)

    for i in range(scan_end):
        if raw[i] in CONTROL_BYTES:
            controls.append((i, raw[i]))

    return {
        "valid": True,
        "terminal": terminal,
        "terminal_byte": terminal_byte,
        "terminal_pos": terminal_pos,
        "entry": entry,
        "length": terminal_pos + 1 if terminal_pos is not None else 0,
        "controls": len(controls),
        "bytes": raw[:min(terminal_pos + 1 if terminal_pos else 32, 32)].hex(" "),
    }


# ----------------------------------------------------------------------
# Mapping già accettati
# ----------------------------------------------------------------------

def load_accepted_mapping():
    """
    Legge Bank 0x20 dalla mapping table.
    Restituisce:
      indirizzo ITA -> simbolo
    """

    occupied = {}

    if not MAPPING.exists():
        return occupied

    with MAPPING.open(encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split("\t")

            if len(parts) < 3:
                continue

            symbol = parts[0]

            # Cerca indirizzi tipo 20:4XXX nella riga.
            addresses = re.findall(
                r"\b20:[0-9A-Fa-f]{4}\b",
                line
            )

            for addr in addresses:
                occupied[addr.upper()] = symbol

    return occupied


# ----------------------------------------------------------------------
# Lettura scoring
# ----------------------------------------------------------------------

if not SCORING.exists():
    raise SystemExit(f"File non trovato: {SCORING}")

if not ROM.exists():
    raise SystemExit(f"ROM italiana non trovata: {ROM}")

data = ROM.read_bytes()

occupied = load_accepted_mapping()

rows = []

with SCORING.open(encoding="utf-8") as f:

    header = f.readline()

    for line in f:

        parts = line.rstrip("\n").split("\t")

        if len(parts) < 8:
            continue

        symbol = parts[0]
        usa = parts[1]
        candidate = parts[2]
        bank = parts[3]
        address = parts[4]
        score = int(parts[5])
        best = parts[6]
        reasons = parts[7]

        rows.append({
            "symbol": symbol,
            "usa": usa,
            "candidate": candidate,
            "bank": bank,
            "address": address,
            "score": score,
            "best": best,
            "reasons": reasons,
        })


# ----------------------------------------------------------------------
# Analisi ROM
# ----------------------------------------------------------------------

results = []

for row in rows:

    info = inspect_candidate(
        data,
        row["candidate"]
    )

    occupied_by = occupied.get(
        row["candidate"].upper()
    )

    rom_score = 0
    rom_reasons = []

    if info["valid"]:
        rom_score += 10
        rom_reasons.append("valid-address")

    if info["entry"]:
        rom_score += 30
        rom_reasons.append("entry-00")
    else:
        rom_reasons.append("no-entry-00")

    if info["terminal"]:
        rom_score += 30
        rom_reasons.append(
            f"terminal-{info['terminal_byte']:02X}"
        )
    else:
        rom_reasons.append("no-terminal")

    if info["terminal_pos"] is not None:

        if info["terminal_pos"] <= 160:
            rom_score += 10
            rom_reasons.append("reasonable-length")

    if occupied_by and occupied_by != row["symbol"]:
        rom_score -= 100
        rom_reasons.append(
            f"occupied-by:{occupied_by}"
        )

    results.append({
        **row,
        "rom_score": rom_score,
        "rom_reasons": rom_reasons,
        "terminal": (
            f"{info['terminal_byte']:02X}"
            if info.get("terminal_byte") is not None
            else ""
        ),
        "length": info.get("length", 0),
        "entry": "YES" if info.get("entry") else "NO",
        "occupied_by": occupied_by or "",
        "bytes": info.get("bytes", ""),
    })


# ----------------------------------------------------------------------
# Raggruppa per simbolo e determina best combinato
# ----------------------------------------------------------------------

groups = {}

for row in results:
    groups.setdefault(row["symbol"], []).append(row)

final_rows = []

for symbol, candidates in groups.items():

    for row in candidates:

        # Structural score massimo osservato: 180.
        # ROM score massimo teorico: 80.
        total = row["score"] + row["rom_score"]

        row["total_score"] = total

    candidates.sort(
        key=lambda x: (
            -x["total_score"],
            -x["score"],
            x["candidate"],
        )
    )

    best_total = candidates[0]["total_score"]

    bests = [
        x for x in candidates
        if x["total_score"] == best_total
    ]

    for row in candidates:

        if len(bests) == 1 and row is bests[0]:

            if row["rom_score"] >= 60 and row["score"] >= 160:
                classification = "HIGH_CONFIDENCE"

            elif row["rom_score"] >= 40 and row["score"] >= 140:
                classification = "PLAUSIBLE"

            else:
                classification = "STRUCTURAL_ONLY"

        elif row["total_score"] >= best_total - 20:
            classification = "STILL_AMBIGUOUS"

        else:
            classification = "REJECTED"

        row["classification"] = classification
        final_rows.append(row)


# ----------------------------------------------------------------------
# TSV
# ----------------------------------------------------------------------

with OUT_TSV.open("w", encoding="utf-8") as f:

    f.write(
        "symbol\tusa\tcandidate\tstructural_score\t"
        "rom_score\ttotal_score\tclassification\t"
        "entry\tterminal\tlength\toccupied_by\t"
        "structural_reasons\trom_reasons\tbytes\n"
    )

    for row in final_rows:

        f.write(
            f"{row['symbol']}\t"
            f"{row['usa']}\t"
            f"{row['candidate']}\t"
            f"{row['score']}\t"
            f"{row['rom_score']}\t"
            f"{row['total_score']}\t"
            f"{row['classification']}\t"
            f"{row['entry']}\t"
            f"{row['terminal']}\t"
            f"{row['length']}\t"
            f"{row['occupied_by']}\t"
            f"{row['reasons']}\t"
            f"{';'.join(row['rom_reasons'])}\t"
            f"{row['bytes']}\n"
        )


# ----------------------------------------------------------------------
# TXT report
# ----------------------------------------------------------------------

with OUT_TXT.open("w", encoding="utf-8") as f:

    f.write("PASS 3 - AMBIGUOUS CANDIDATE ANALYSIS\n")
    f.write("=" * 100 + "\n\n")

    for symbol, candidates in groups.items():

        f.write(f"{symbol}\n")
        f.write("-" * 100 + "\n")

        for row in candidates:

            f.write(
                f"  {row['candidate']} "
                f"struct={row['score']} "
                f"rom={row['rom_score']} "
                f"total={row['total_score']} "
                f"=> {row['classification']}\n"
            )

            f.write(
                f"      entry={row['entry']} "
                f"terminal={row['terminal']} "
                f"length={row['length']}\n"
            )

            if row["occupied_by"]:
                f.write(
                    f"      OCCUPIED BY: {row['occupied_by']}\n"
                )

            f.write(
                f"      structural: {row['reasons']}\n"
            )

            f.write(
                f"      ROM: {'; '.join(row['rom_reasons'])}\n"
            )

            f.write(
                f"      bytes: {row['bytes']}\n"
            )

        f.write("\n")


# ----------------------------------------------------------------------
# STATISTICHE
# ----------------------------------------------------------------------

counts = {}

for row in final_rows:
    counts[row["classification"]] = (
        counts.get(row["classification"], 0) + 1
    )

symbols = len(groups)

high_symbols = {
    row["symbol"]
    for row in final_rows
    if row["classification"] == "HIGH_CONFIDENCE"
}

plausible_symbols = {
    row["symbol"]
    for row in final_rows
    if row["classification"] == "PLAUSIBLE"
}

ambiguous_symbols = {
    row["symbol"]
    for row in final_rows
    if row["classification"] == "STILL_AMBIGUOUS"
}


print()
print("=" * 110)
print("PASS 3 - ROM + STRUCTURAL ANALYSIS")
print("=" * 110)

print(f"Casi/simboli analizzati       : {symbols}")
print(f"Candidati analizzati          : {len(final_rows)}")
print()
print(f"HIGH_CONFIDENCE               : {len(high_symbols)} simboli")
print(f"PLAUSIBLE                     : {len(plausible_symbols)} simboli")
print(f"STILL_AMBIGUOUS               : {len(ambiguous_symbols)} simboli")
print()
print(f"Output TSV                    : {OUT_TSV}")
print(f"Output report                 : {OUT_TXT}")

print()
print("HIGH CONFIDENCE")
print("-" * 110)

for symbol in sorted(high_symbols):

    best = [
        r for r in final_rows
        if r["symbol"] == symbol
        and r["classification"] == "HIGH_CONFIDENCE"
    ]

    for row in best:

        print(
            f"{symbol:<60} "
            f"-> {row['candidate']} "
            f"total={row['total_score']}"
        )

print()
print("STILL AMBIGUOUS")
print("-" * 110)

for symbol in sorted(ambiguous_symbols):

    best = [
        r for r in final_rows
        if r["symbol"] == symbol
        and r["classification"] == "STILL_AMBIGUOUS"
    ]

    print(
        f"{symbol:<60} "
        + ", ".join(
            f"{r['candidate']}({r['total_score']})"
            for r in best
        )
    )

print()
print("PASS 3 completato.")
print("Nessun file di mapping è stato modificato.")
