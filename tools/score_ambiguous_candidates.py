#!/usr/bin/env python3

from pathlib import Path
import re

INPUT = Path("tools/ambiguous_candidates.tsv")
OUTPUT = Path("tools/ambiguous_candidate_scoring.tsv")


def parse_addr(value):
    """
    26:4F4D -> (0x26, 0x4F4D)
    """
    if not value or ":" not in value:
        return None

    bank, addr = value.split(":", 1)

    try:
        return int(bank, 16), int(addr, 16)
    except ValueError:
        return None


def parse_neighbors(value):
    """
    _Symbol USA=26:4EFC ITA=26:4F8C | ...
    """
    result = []

    if not value:
        return result

    for item in value.split(" | "):

        m = re.match(
            r"^(\S+)\s+USA=([0-9A-Fa-f]+:[0-9A-Fa-f]+)"
            r"\s+ITA=([0-9A-Fa-f]+:[0-9A-Fa-f]+)$",
            item.strip()
        )

        if not m:
            continue

        symbol = m.group(1)
        usa = parse_addr(m.group(2))
        ita = parse_addr(m.group(3))

        if usa and ita:
            result.append((symbol, usa, ita))

    return result


def score_candidate(candidate, prev, nxt):
    """
    Score strutturale.

    +100 stesso bank di entrambi i vicini
    +80 candidato tra PREV e NEXT
    +30 stesso bank del PREV
    +30 stesso bank del NEXT
    +20 vicino al PREV
    +20 vicino al NEXT

    NON decide ancora il mapping.
    """

    parsed = parse_addr(candidate)

    if not parsed:
        return 0, []

    bank, addr = parsed

    score = 0
    reasons = []

    prev_same_bank = [
        item for item in prev
        if item[2][0] == bank
    ]

    next_same_bank = [
        item for item in nxt
        if item[2][0] == bank
    ]

    if prev_same_bank:
        score += 30
        reasons.append("same-bank-PREV")

    if next_same_bank:
        score += 30
        reasons.append("same-bank-NEXT")

    # ------------------------------------------------------------
    # Cerca coppie PREV/NEXT nella stessa banca
    # ------------------------------------------------------------

    intervals = []

    for p in prev_same_bank:
        for n in next_same_bank:

            pa = p[2][1]
            na = n[2][1]

            if pa <= na:
                intervals.append((pa, na))

            elif na <= pa:
                intervals.append((na, pa))

    inside = False

    for low, high in intervals:

        if low <= addr <= high:

            inside = True
            score += 80
            reasons.append(
                f"between-neighbors:{low:04X}-{high:04X}"
            )
            break

    # ------------------------------------------------------------
    # Distanza dal vicino più vicino
    # ------------------------------------------------------------

    distances_prev = [
        abs(addr - item[2][1])
        for item in prev_same_bank
    ]

    distances_next = [
        abs(addr - item[2][1])
        for item in next_same_bank
    ]

    if distances_prev:
        d = min(distances_prev)

        if d <= 0x20:
            score += 20
            reasons.append(f"near-PREV:{d:04X}")

    if distances_next:
        d = min(distances_next)

        if d <= 0x20:
            score += 20
            reasons.append(f"near-NEXT:{d:04X}")

    return score, reasons


# ============================================================
# READ INPUT
# ============================================================

if not INPUT.exists():
    raise SystemExit(f"Input non trovato: {INPUT}")

rows = []

with INPUT.open(encoding="utf-8") as f:

    header = f.readline().rstrip("\n").split("\t")

    for line in f:

        parts = line.rstrip("\n").split("\t")

        if len(parts) < 6:
            continue

        symbol = parts[0]
        usa = parts[1]
        candidate_count = int(parts[2])
        candidates = parts[3].split()
        prev = parse_neighbors(parts[4])
        nxt = parse_neighbors(parts[5])

        rows.append({
            "symbol": symbol,
            "usa": usa,
            "candidate_count": candidate_count,
            "candidates": candidates,
            "prev": prev,
            "next": nxt,
        })


# ============================================================
# SCORE
# ============================================================

results = []

for row in rows:

    scored = []

    for candidate in row["candidates"]:

        score, reasons = score_candidate(
            candidate,
            row["prev"],
            row["next"],
        )

        scored.append({
            "candidate": candidate,
            "score": score,
            "reasons": reasons,
        })

    scored.sort(
        key=lambda x: (
            -x["score"],
            parse_addr(x["candidate"]) or (999, 999),
        )
    )

    if scored:

        best_score = scored[0]["score"]

        best = [
            x for x in scored
            if x["score"] == best_score
        ]

    else:

        best_score = 0
        best = []

    results.append({
        **row,
        "scored": scored,
        "best_score": best_score,
        "best": best,
    })


# ============================================================
# OUTPUT TSV
# ============================================================

with OUTPUT.open("w", encoding="utf-8") as f:

    f.write(
        "symbol\tusa\tcandidate\tbank\taddress\t"
        "score\tbest\t"
        "reasons\n"
    )

    for row in results:

        best_candidates = {
            x["candidate"]
            for x in row["best"]
        }

        for item in row["scored"]:

            parsed = parse_addr(item["candidate"])

            if parsed:
                bank, address = parsed
                bank_text = f"{bank:02X}"
                address_text = f"{address:04X}"
            else:
                bank_text = ""
                address_text = ""

            f.write(
                f"{row['symbol']}\t"
                f"{row['usa']}\t"
                f"{item['candidate']}\t"
                f"{bank_text}\t"
                f"{address_text}\t"
                f"{item['score']}\t"
                f"{'YES' if item['candidate'] in best_candidates else 'NO'}\t"
                f"{';'.join(item['reasons'])}\n"
            )


# ============================================================
# STATISTICS
# ============================================================

unique_best = []
ties = []
no_score = []

for row in results:

    if not row["best"]:
        no_score.append(row)
        continue

    if len(row["best"]) == 1:
        unique_best.append(row)
    else:
        ties.append(row)


print()
print("=" * 110)
print("AMBIGUOUS CANDIDATE STRUCTURAL SCORING")
print("=" * 110)

print(f"Casi analizzati              : {len(results)}")
print(f"Casi con un best candidato   : {len(unique_best)}")
print(f"Casi con parità               : {len(ties)}")
print(f"Casi senza candidato valido   : {len(no_score)}")
print(f"Output                        : {OUTPUT}")

print()
print("BEST CANDIDATES")
print("-" * 110)

for row in unique_best:

    best = row["best"][0]

    print(
        f"{row['symbol']:<60} "
        f"USA {row['usa']} -> "
        f"{best['candidate']} "
        f"score={best['score']:>3} "
        f"[{'; '.join(best['reasons'])}]"
    )

print()
print("PARITÀ")
print("-" * 110)

for row in ties:

    candidates = ", ".join(
        f"{x['candidate']}({x['score']})"
        for x in row["best"]
    )

    print(
        f"{row['symbol']:<60} "
        f"{candidates}"
    )

print()
print("Fine.")
