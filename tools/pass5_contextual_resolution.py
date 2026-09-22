#!/usr/bin/env python3

from pathlib import Path
from collections import defaultdict
import csv


MAPPING = Path("tools/bank20_mapping.tsv")
PASS3 = Path("tools/pass3_ambiguous_analysis.tsv")

OUT_TSV = Path("tools/pass5_contextual_resolution.tsv")
OUT_TXT = Path("tools/pass5_contextual_resolution.txt")


RESOLVED_STATUSES = {
    "EXACT",
    "HIGH_CONFIDENCE",
    "MEDIUM_CONFIDENCE",
}


def parse_addr(value):
    if not value:
        return None

    # PASS 5 works on Bank 0x20.
    # bank20_mapping.tsv stores CPU addresses as 0x4000-0x7FFF,
    # while PASS 3 stores addresses as BANK:OFFSET (e.g. 20:69FD).
    if ":" not in value:
        try:
            address = int(value, 16)
        except ValueError:
            return None

        if 0x4000 <= address <= 0x7FFF:
            return 0x20, address

        return None

    bank, address = value.split(":", 1)

    try:
        return int(bank, 16), int(address, 16)
    except ValueError:
        return None


def rom_offset(value):
    parsed = parse_addr(value)

    if parsed is None:
        return None

    bank, address = parsed

    if bank == 0:
        return address

    return bank * 0x4000 + address - 0x4000


def load_tsv(path):
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def distance(a, b):
    if a is None or b is None:
        return None

    return abs(a - b)


# ============================================================
# LOAD
# ============================================================

mapping = load_tsv(MAPPING)
pass3 = load_tsv(PASS3)


# ============================================================
# COMPLETE USA SEQUENCE
# ============================================================

usa_sequence = []

for row in mapping:
    usa = row.get("usa_address", "")
    offset = rom_offset(usa)

    if offset is None:
        continue

    usa_sequence.append(
        (
            offset,
            row,
        )
    )

usa_sequence.sort(key=lambda x: x[0])


# ============================================================
# ITA RESOLVED SEQUENCE
# ============================================================

def resolved_ita(row):
    status = row.get("status", "")
    ita = row.get("ita_address", "")

    if status not in RESOLVED_STATUSES:
        return None

    return rom_offset(ita)


# ============================================================
# FIND USA NEIGHBOURS
# ============================================================

def usa_neighbours(usa_value):
    target = rom_offset(usa_value)

    if target is None:
        return None, None

    previous = None
    following = None

    for offset, row in usa_sequence:

        if offset >= target:
            break

        if resolved_ita(row) is not None:
            previous = row

    for offset, row in usa_sequence:

        if offset <= target:
            continue

        if resolved_ita(row) is not None:
            following = row
            break

    return previous, following


# ============================================================
# SCORE ONE CANDIDATE
# ============================================================

def score_candidate(usa_value, candidate):

    usa_target = rom_offset(usa_value)
    ita_candidate = rom_offset(candidate)

    if usa_target is None or ita_candidate is None:
        return 0, ["invalid-address"]

    previous, following = usa_neighbours(usa_value)

    score = 0
    reasons = []

    # --------------------------------------------------------
    # Previous resolved USA symbol
    # --------------------------------------------------------

    prev_usa = None
    prev_ita = None

    if previous is not None:

        prev_usa = rom_offset(previous["usa_address"])
        prev_ita = resolved_ita(previous)

        if prev_ita is not None:

            if ita_candidate > prev_ita:
                score += 30
                reasons.append("after-prev")
            else:
                score -= 100
                reasons.append("before-prev")

    # --------------------------------------------------------
    # Following resolved USA symbol
    # --------------------------------------------------------

    next_usa = None
    next_ita = None

    if following is not None:

        next_usa = rom_offset(following["usa_address"])
        next_ita = resolved_ita(following)

        if next_ita is not None:

            if ita_candidate < next_ita:
                score += 30
                reasons.append("before-next")
            else:
                score -= 100
                reasons.append("after-next")

    # --------------------------------------------------------
    # Same bank as contextual neighbours
    # --------------------------------------------------------

    candidate_bank, _ = parse_addr(candidate)

    neighbour_banks = set()

    for row in (previous, following):

        if row is None:
            continue

        ita = row.get("ita_address", "")
        parsed = parse_addr(ita)

        if parsed:
            neighbour_banks.add(parsed[0])

    if candidate_bank in neighbour_banks:
        score += 10
        reasons.append("same-neighbour-bank")

    # --------------------------------------------------------
    # Relative-distance consistency
    #
    # Compare USA distance with ITA distance.
    # This is only a soft heuristic.
    # --------------------------------------------------------

    if previous is not None and prev_usa is not None and prev_ita is not None:

        usa_gap = usa_target - prev_usa
        ita_gap = ita_candidate - prev_ita

        if usa_gap > 0 and ita_gap > 0:

            ratio = ita_gap / usa_gap

            if 0.50 <= ratio <= 2.00:
                score += 15
                reasons.append("reasonable-prev-ratio")

            elif ratio <= 4.00:
                score += 5
                reasons.append("wide-prev-ratio")

    if following is not None and next_usa is not None and next_ita is not None:

        usa_gap = next_usa - usa_target
        ita_gap = next_ita - ita_candidate

        if usa_gap > 0 and ita_gap > 0:

            ratio = ita_gap / usa_gap

            if 0.50 <= ratio <= 2.00:
                score += 15
                reasons.append("reasonable-next-ratio")

            elif ratio <= 4.00:
                score += 5
                reasons.append("wide-next-ratio")

    # --------------------------------------------------------
    # Exact interval
    # --------------------------------------------------------

    if prev_ita is not None and next_ita is not None:

        if prev_ita < ita_candidate < next_ita:
            score += 20
            reasons.append("inside-resolved-interval")

    return score, reasons


# ============================================================
# PASS 5
# ============================================================

pass3_by_symbol = defaultdict(list)

for row in pass3:

    if row.get("classification") == "REJECTED":
        continue

    pass3_by_symbol[row["symbol"]].append(row)


results = []
best_by_class = defaultdict(list)


for symbol, candidates in sorted(pass3_by_symbol.items()):

    if not candidates:
        continue

    usa_value = candidates[0]["usa"]

    scored = []

    for row in candidates:

        candidate = row["candidate"]

        score, reasons = score_candidate(
            usa_value,
            candidate,
        )

        scored.append(
            {
                "symbol": symbol,
                "usa": usa_value,
                "candidate": candidate,
                "score": score,
                "reasons": ";".join(reasons),
                "pass3_classification": row.get(
                    "classification",
                    "",
                ),
                "structural_score": row.get(
                    "structural_score",
                    "",
                ),
                "rom_score": row.get(
                    "rom_score",
                    "",
                ),
                "total_score": row.get(
                    "total_score",
                    "",
                ),
            }
        )

    if not scored:
        continue

    best_score = max(
        row["score"]
        for row in scored
    )

    best = [
        row
        for row in scored
        if row["score"] == best_score
    ]

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    if len(best) != 1:
        classification = "STILL_AMBIGUOUS"

    else:

        winner = best[0]

        # Strong contextual evidence.
        if (
            best_score >= 90
            and winner["pass3_classification"]
            in {"HIGH_CONFIDENCE", "PLAUSIBLE"}
        ):
            classification = "CONFIRMED"

        elif best_score >= 60:
            classification = "PLAUSIBLE"

        else:
            classification = "STILL_AMBIGUOUS"

    for row in scored:

        row["best_score"] = best_score
        row["best"] = (
            "YES"
            if row in best
            else ""
        )
        row["classification"] = classification

        results.append(row)

    if len(best) == 1:
        best_by_class[classification].append(
            best[0]
        )


# ============================================================
# TSV
# ============================================================

fields = [
    "symbol",
    "usa",
    "candidate",
    "score",
    "best_score",
    "best",
    "classification",
    "pass3_classification",
    "structural_score",
    "rom_score",
    "total_score",
    "reasons",
]


with OUT_TSV.open(
    "w",
    encoding="utf-8",
    newline="",
) as handle:

    writer = csv.DictWriter(
        handle,
        fieldnames=fields,
        delimiter="\t",
    )

    writer.writeheader()

    for row in results:
        writer.writerow(row)


# ============================================================
# REPORT
# ============================================================

with OUT_TXT.open(
    "w",
    encoding="utf-8",
) as handle:

    handle.write(
        "PASS 5 - CONTEXTUAL RESOLUTION\n"
    )

    handle.write(
        "=" * 100 + "\n\n"
    )

    handle.write(
        f"Candidate analizzati : {len(results)}\n"
    )

    handle.write(
        f"Simboli analizzati   : {len(pass3_by_symbol)}\n\n"
    )

    for classification in (
        "CONFIRMED",
        "PLAUSIBLE",
        "STILL_AMBIGUOUS",
    ):

        handle.write(
            f"{classification:20s}: "
            f"{len(best_by_class[classification])}\n"
        )

    for classification in (
        "CONFIRMED",
        "PLAUSIBLE",
        "STILL_AMBIGUOUS",
    ):

        handle.write(
            "\n\n"
            + classification
            + "\n"
            + "-" * 100
            + "\n"
        )

        for row in best_by_class[classification]:

            handle.write(
                f"{row['symbol']}\t"
                f"USA={row['usa']}\t"
                f"ITA={row['candidate']}\t"
                f"score={row['score']}\t"
                f"pass3={row['pass3_classification']}\t"
                f"reasons={row['reasons']}\n"
            )


# ============================================================
# CONSOLE
# ============================================================

print()
print("=" * 100)
print("PASS 5 - CONTEXTUAL RESOLUTION")
print("=" * 100)

print(
    f"Candidate analizzati : {len(results)}"
)

print(
    f"Simboli analizzati   : {len(pass3_by_symbol)}"
)

print()

for classification in (
    "CONFIRMED",
    "PLAUSIBLE",
    "STILL_AMBIGUOUS",
):

    print(
        f"{classification:20s}: "
        f"{len(best_by_class[classification])}"
    )

print()
print(f"Output TSV: {OUT_TSV}")
print(f"Output TXT: {OUT_TXT}")
