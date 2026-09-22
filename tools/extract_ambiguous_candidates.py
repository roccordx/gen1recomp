#!/usr/bin/env python3

from pathlib import Path
import re

REPORT = Path("tools/italian_text_manifest_report.txt")
CONTEXT = Path("tools/pass2_neighbor_context.txt")
OUT = Path("tools/ambiguous_candidates.tsv")

if not REPORT.exists():
    raise SystemExit(f"Report non trovato: {REPORT}")

if not CONTEXT.exists():
    raise SystemExit(
        f"\nERRORE: {CONTEXT} non esiste.\n\n"
        "Se hai il file in /tmp, esegui:\n"
        "  cp /tmp/pass2_neighbor_context.txt tools/pass2_neighbor_context.txt\n"
        "e poi rilancia questo script.\n"
    )

# ============================================================
# LETTURA REPORT
# ============================================================

report = REPORT.read_text(encoding="utf-8")

# Trova l'intestazione AMBIGUOUS
m = re.search(r"(?m)^AMBIGUOUS\s*$", report)

if not m:
    raise SystemExit(
        "Sezione AMBIGUOUS non trovata nel report.\n"
        "Controlla con: grep -n '^AMBIGUOUS' tools/italian_text_manifest_report.txt"
    )

start = m.end()

# Cerca la prima vera intestazione successiva.
# Usiamo le righe che sappiamo essere presenti nel report.
next_section = re.search(
    r"(?m)^(?:NO_CORPUS|ENCODING_UNKNOWN|UNRESOLVED|RESOLVED)\s*$",
    report[start:]
)

if next_section:
    end = start + next_section.start()
else:
    end = len(report)

ambiguous_body = report[start:end]

ambiguous_symbols = set()

for line in ambiguous_body.splitlines():
    line = line.strip()

    if not line:
        continue

    # Ignora separatori e righe dei candidati dettagliati
    if line.startswith("-"):
        continue

    parts = line.split()

    if not parts:
        continue

    symbol = parts[0]

    if symbol.startswith("_"):
        ambiguous_symbols.add(symbol)

print(f"Simboli AMBIGUOUS trovati nel report: {len(ambiguous_symbols)}")

# ============================================================
# LETTURA NEIGHBOR CONTEXT
# ============================================================

text = CONTEXT.read_text(encoding="utf-8")

# I blocchi iniziano con il nome del simbolo.
blocks = re.split(
    r"(?m)(?=^_[A-Za-z0-9_]+\s*$)",
    text
)

rows = []

for block in blocks:

    lines = block.splitlines()

    if not lines:
        continue

    symbol = lines[0].strip()

    if symbol not in ambiguous_symbols:
        continue

    usa = ""
    prev = []
    nxt = []
    candidates = []

    section = None

    for line in lines[1:]:

        stripped = line.strip()

        if stripped.startswith("USA:"):
            usa = stripped.split(":", 1)[1].strip()
            section = None

        elif stripped == "PREV:":
            section = "prev"

        elif stripped == "NEXT:":
            section = "next"

        elif stripped == "CANDIDATES:":
            section = "candidates"

        elif section in ("prev", "next"):

            mm = re.match(
                r"^(_\S+)\s+USA=([0-9A-Fa-f]+:[0-9A-Fa-f]+)"
                r"(?:\s+ITA=([0-9A-Fa-f]+:[0-9A-Fa-f]+))?",
                stripped
            )

            if mm:

                item = (
                    mm.group(1),
                    mm.group(2),
                    mm.group(3) or "",
                )

                if section == "prev":
                    prev.append(item)
                else:
                    nxt.append(item)

        elif section == "candidates":

            if stripped:
                candidates.extend(stripped.split())

    rows.append({
        "symbol": symbol,
        "usa": usa,
        "candidates": candidates,
        "prev": prev,
        "next": nxt,
    })

# ============================================================
# OUTPUT TSV
# ============================================================

with OUT.open("w", encoding="utf-8") as f:

    f.write(
        "symbol\tusa\tcandidate_count\tcandidates\tprev\tnext\n"
    )

    for row in rows:

        prev_text = " | ".join(
            f"{s} USA={u} ITA={i}"
            for s, u, i in row["prev"]
        )

        next_text = " | ".join(
            f"{s} USA={u} ITA={i}"
            for s, u, i in row["next"]
        )

        f.write(
            f"{row['symbol']}\t"
            f"{row['usa']}\t"
            f"{len(row['candidates'])}\t"
            f"{' '.join(row['candidates'])}\t"
            f"{prev_text}\t"
            f"{next_text}\n"
        )

# ============================================================
# OUTPUT A VIDEO
# ============================================================

print()
print("=" * 100)
print("RISULTATO")
print("=" * 100)

print(f"Simboli AMBIGUOUS nel report : {len(ambiguous_symbols)}")
print(f"Blocchi trovati nel context  : {len(rows)}")
print(f"Con candidati ROM             : {sum(bool(r['candidates']) for r in rows)}")
print(f"Senza candidati               : {sum(not r['candidates'] for r in rows)}")
print(f"Output TSV                    : {OUT}")

print()
print("PRIMI CANDIDATI")
print("-" * 100)

for row in rows[:30]:

    print(
        f"{row['symbol']:<60} "
        f"{len(row['candidates']):>2} candidati"
    )

    if row["candidates"]:
        print(
            "  " + " ".join(row["candidates"])
        )

print()
print("Analisi completata.")
