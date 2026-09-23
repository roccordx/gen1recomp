#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
from math import inf


ROOT = Path(__file__).resolve().parents[1]

ALL_CANDIDATES = ROOT / "tools" / "italian_map_header_all_candidates.tsv"
OUTPUT = ROOT / "tools" / "italian_map_header_alignment.tsv"
REPORT = ROOT / "tools" / "italian_map_header_alignment_report.txt"


@dataclass(frozen=True)
class Candidate:
    symbol: str
    usa_bank: int
    usa_address: int
    ita_bank: int
    ita_address: int
    score: int
    block_pointer: int
    source: str

    @property
    def usa_offset(self):
        return self.usa_bank * 0x4000 + (self.usa_address - 0x4000)

    @property
    def ita_offset(self):
        return self.ita_bank * 0x4000 + (self.ita_address - 0x4000)

    @property
    def delta(self):
        return self.ita_offset - self.usa_offset

    @property
    def location(self):
        return f"{self.ita_bank:02X}:{self.ita_address:04X}"


def parse_location(value):
    bank, address = value.split(":")
    return int(bank, 16), int(address, 16)


def load_candidates():
    by_symbol = defaultdict(list)

    with ALL_CANDIDATES.open(encoding="utf-8") as f:
        header = next(f).rstrip("\n").split("\t")

        expected = [
            "symbol",
            "usa",
            "ita_candidate",
            "score",
            "block_pointer",
            "source",
        ]

        if header != expected:
            raise RuntimeError(
                f"Header inatteso: {header}"
            )

        for line in f:
            if not line.strip():
                continue

            symbol, usa, ita, score, block_pointer, source = (
                line.rstrip("\n").split("\t")
            )

            ub, ua = parse_location(usa)
            ib, ia = parse_location(ita)

            by_symbol[symbol].append(
                Candidate(
                    symbol=symbol,
                    usa_bank=ub,
                    usa_address=ua,
                    ita_bank=ib,
                    ita_address=ia,
                    score=int(score),
                    block_pointer=int(block_pointer, 16),
                    source=source,
                )
            )

    return by_symbol


def sort_symbols(by_symbol):
    return sorted(
        by_symbol,
        key=lambda s: (
            min(c.usa_offset for c in by_symbol[s]),
            s,
        ),
    )


def unique_anchor(candidates):
    """
    Unico candidato considerando score + source.
    Non considera la posizione come criterio di spareggio.
    """
    if not candidates:
        return None

    max_score = max(c.score for c in candidates)
    top = [c for c in candidates if c.score == max_score]

    top_manifest = [
        c for c in top
        if c.source == "MANIFEST+SEARCH"
    ]

    if len(top_manifest) == 1:
        return top_manifest[0]

    if len(top) == 1:
        return top[0]

    return None


def build_raw_anchors(symbols, by_symbol):
    anchors = {}

    for symbol in symbols:
        c = unique_anchor(by_symbol[symbol])
        if c is not None:
            anchors[symbol] = c

    return anchors


def build_monotonic_anchors(symbols, raw_anchors):
    """
    Mantiene solo gli anchor compatibili con l'ordine fisico USA/ITA.
    In caso di inversione, l'anchor successivo viene escluso.
    """
    result = {}
    last_usa = None
    last_ita = None
    rejected = []

    for symbol in symbols:
        c = raw_anchors.get(symbol)

        if c is None:
            continue

        if last_usa is not None:
            if c.usa_offset <= last_usa:
                rejected.append(
                    (symbol, "USA_ORDER")
                )
                continue

            if c.ita_offset <= last_ita:
                rejected.append(
                    (symbol, "ITA_ORDER")
                )
                continue

        result[symbol] = c
        last_usa = c.usa_offset
        last_ita = c.ita_offset

    return result, rejected


def candidate_base_cost(c):
    """
    Costo basso = candidato preferibile.
    """
    if c.score >= 5:
        cost = 0
    elif c.score >= 3:
        cost = 8
    elif c.score >= 2:
        cost = 18
    else:
        cost = 35

    if c.source == "MANIFEST+SEARCH":
        cost -= 2

    return cost


def solve_segment(segment_symbols, by_symbol, left_anchor, right_anchor):
    """
    Dynamic programming su una sequenza di header.

    Vincolo fondamentale:
        ita_offset(i) < ita_offset(i+1)

    Funzione obiettivo:
      - qualità del candidato
      - coerenza del delta USA->ITA
      - coerenza con il delta atteso tra gli anchor
    """

    if not segment_symbols:
        return {}, 0, 0

    left_usa = left_anchor.usa_offset if left_anchor else None
    right_usa = right_anchor.usa_offset if right_anchor else None
    left_ita = left_anchor.ita_offset if left_anchor else None
    right_ita = right_anchor.ita_offset if right_anchor else None

    n = len(segment_symbols)

    states = []
    parents = []

    for i, symbol in enumerate(segment_symbols):
        candidates = by_symbol[symbol]

        if left_anchor is not None and i == 0:
            pass

        current = []

        for c in candidates:
            if left_anchor and c.ita_offset <= left_ita:
                continue

            if right_anchor and c.ita_offset >= right_ita:
                continue

            if left_usa is not None and right_usa is not None:
                usa_ratio = (
                    (c.usa_offset - left_usa)
                    / max(1, right_usa - left_usa)
                )

                expected_ita = (
                    left_ita
                    + usa_ratio * (right_ita - left_ita)
                )

                position_cost = abs(
                    c.ita_offset - expected_ita
                ) * 0.20
            else:
                position_cost = 0

            base = candidate_base_cost(c)

            current.append(
                {
                    "candidate": c,
                    "base": base + position_cost,
                    "cost": inf,
                    "parent": None,
                }
            )

        states.append(current)
        parents.append(current)

    if not states[0]:
        return {}, inf, inf

    # First row.
    for state in states[0]:
        state["cost"] = state["base"]

        if left_anchor:
            state["cost"] += abs(
                state["candidate"].delta
                - left_anchor.delta
            ) * 0.05

    # Remaining rows.
    for i in range(1, n):
        current = states[i]
        previous = states[i - 1]

        if not current:
            return {}, inf, inf

        for state in current:
            c = state["candidate"]

            for prev in previous:
                pc = prev["candidate"]

                if c.ita_offset <= pc.ita_offset:
                    continue

                delta_change = abs(c.delta - pc.delta)

                cost = (
                    prev["cost"]
                    + state["base"]
                    + delta_change * 0.08
                )

                if cost < state["cost"]:
                    state["cost"] = cost
                    state["parent"] = prev

        if all(x["parent"] is None for x in current):
            return {}, inf, inf

    # Add right anchor coherence.
    finals = []

    for state in states[-1]:
        if state["cost"] == inf:
            continue

        extra = 0

        if right_anchor:
            extra += abs(
                state["candidate"].delta
                - right_anchor.delta
            ) * 0.05

        finals.append(
            (
                state["cost"] + extra,
                state,
            )
        )

    if not finals:
        return {}, inf, inf

    finals.sort(key=lambda x: x[0])

    best_cost, best_state = finals[0]
    second_cost = (
        finals[1][0]
        if len(finals) > 1
        else inf
    )

    selected = {}

    state = best_state

    for i in range(n - 1, -1, -1):
        selected[
            segment_symbols[i]
        ] = state["candidate"]

        state = state["parent"]

        if i == 0:
            break

    return selected, best_cost, second_cost


def classify_segment_solution(
    best_cost,
    second_cost,
    segment_size,
):
    if best_cost == inf:
        return "UNMATCHED"

    if second_cost == inf:
        return "HIGH"

    margin = second_cost - best_cost

    if margin >= 20:
        return "HIGH"

    if margin >= 8:
        return "MEDIUM"

    if margin >= 2:
        return "AMBIGUOUS"

    return "AMBIGUOUS"


def solve(by_symbol):
    symbols = sort_symbols(by_symbol)

    raw_anchors = build_raw_anchors(
        symbols,
        by_symbol,
    )

    anchors, rejected = build_monotonic_anchors(
        symbols,
        raw_anchors,
    )

    anchor_indices = [
        i
        for i, symbol in enumerate(symbols)
        if symbol in anchors
    ]

    assignments = dict(anchors)
    segment_results = []

    # Segments between anchors.
    boundaries = [-1] + anchor_indices + [len(symbols)]

    for left_index, right_index in zip(
        boundaries,
        boundaries[1:],
    ):
        segment_start = left_index + 1
        segment_end = right_index

        if segment_start >= segment_end:
            continue

        segment_symbols = symbols[
            segment_start:segment_end
        ]

        left_anchor = None
        right_anchor = None

        if left_index >= 0:
            left_anchor = anchors[
                symbols[left_index]
            ]

        if right_index < len(symbols):
            right_anchor = anchors[
                symbols[right_index]
            ]

        selected, best_cost, second_cost = (
            solve_segment(
                segment_symbols,
                by_symbol,
                left_anchor,
                right_anchor,
            )
        )

        status = classify_segment_solution(
            best_cost,
            second_cost,
            len(segment_symbols),
        )

        assignments.update(selected)

        segment_results.append(
            {
                "start": segment_symbols[0],
                "end": segment_symbols[-1],
                "count": len(segment_symbols),
                "status": status,
                "best": best_cost,
                "second": second_cost,
                "margin": (
                    second_cost - best_cost
                    if second_cost != inf
                    else inf
                ),
            }
        )

    return (
        symbols,
        assignments,
        raw_anchors,
        anchors,
        rejected,
        segment_results,
    )


def final_status(
    symbol,
    candidate,
    by_symbol,
    anchors,
    segment_results,
):
    if candidate is None:
        return "UNMATCHED", "no_assignment"

    if symbol in anchors:
        return "CONFIRMED", "anchor"

    candidates = by_symbol[symbol]

    if candidate.source == "MANIFEST+SEARCH":
        return "HIGH", "manifest+search"

    if candidate.score >= 5:
        # Strong candidate selected by sequence alignment.
        return "HIGH", "sequence_alignment"

    if candidate.score >= 3:
        return "MEDIUM", "sequence_alignment"

    return "AMBIGUOUS", "weak_candidate"


def main():
    by_symbol = load_candidates()

    (
        symbols,
        assignments,
        raw_anchors,
        anchors,
        rejected,
        segment_results,
    ) = solve(by_symbol)

    status_counts = defaultdict(int)

    with OUTPUT.open("w", encoding="utf-8") as f:
        f.write(
            "\t".join(
                [
                    "symbol",
                    "usa",
                    "ita",
                    "status",
                    "score",
                    "source",
                    "delta",
                    "reason",
                ]
            )
            + "\n"
        )

        for symbol in symbols:
            first = by_symbol[symbol][0]
            candidate = assignments.get(symbol)

            if candidate is None:
                status = "UNMATCHED"
                reason = "no_assignment"

                row = [
                    symbol,
                    f"{first.usa_bank:02X}:{first.usa_address:04X}",
                    "",
                    status,
                    "",
                    "",
                    "",
                    reason,
                ]
            else:
                status, reason = final_status(
                    symbol,
                    candidate,
                    by_symbol,
                    anchors,
                    segment_results,
                )

                delta = candidate.delta

                row = [
                    symbol,
                    f"{first.usa_bank:02X}:{first.usa_address:04X}",
                    candidate.location,
                    status,
                    str(candidate.score),
                    candidate.source,
                    str(delta),
                    reason,
                ]

            status_counts[status] += 1
            f.write("\t".join(row) + "\n")

    collisions = defaultdict(list)

    for symbol, candidate in assignments.items():
        collisions[candidate.location].append(symbol)

    collisions = {
        location: syms
        for location, syms in collisions.items()
        if len(syms) > 1
    }

    with REPORT.open("w", encoding="utf-8") as f:
        f.write("Italian map header segment alignment\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"USA headers             : {len(symbols)}\n")
        f.write(f"Raw unique anchors      : {len(raw_anchors)}\n")
        f.write(f"Monotonic anchors       : {len(anchors)}\n")
        f.write(f"Rejected anchors        : {len(rejected)}\n")
        f.write(f"Assigned                : {len(assignments)}\n")
        f.write("\n")

        f.write("STATUS\n")
        f.write("-" * 70 + "\n")

        for status in [
            "CONFIRMED",
            "HIGH",
            "MEDIUM",
            "AMBIGUOUS",
            "UNMATCHED",
        ]:
            f.write(
                f"{status:12} : "
                f"{status_counts[status]}\n"
            )

        f.write("\n")

        f.write("SEGMENTS\n")
        f.write("-" * 70 + "\n")

        for i, segment in enumerate(segment_results, 1):
            best = (
                "INF"
                if segment["best"] == inf
                else f"{segment['best']:.2f}"
            )

            second = (
                "INF"
                if segment["second"] == inf
                else f"{segment['second']:.2f}"
            )

            margin = (
                "INF"
                if segment["margin"] == inf
                else f"{segment['margin']:.2f}"
            )

            f.write(
                f"{i:03d} "
                f"{segment['start']} -> "
                f"{segment['end']} "
                f"count={segment['count']} "
                f"status={segment['status']} "
                f"best={best} "
                f"second={second} "
                f"margin={margin}\n"
            )

        f.write("\n")

        f.write("REJECTED ANCHORS\n")
        f.write("-" * 70 + "\n")

        for symbol, reason in rejected:
            f.write(
                f"{symbol}\t{reason}\n"
            )

        f.write("\n")

        f.write(
            f"ADDRESS COLLISIONS : {len(collisions)}\n"
        )

        for location, syms in sorted(collisions.items()):
            f.write(
                f"{location}\t"
                f"{', '.join(sorted(syms))}\n"
            )

    print()
    print("Italian map header segment alignment")
    print("=" * 70)
    print(f"USA headers        : {len(symbols)}")
    print(f"Raw anchors        : {len(raw_anchors)}")
    print(f"Monotonic anchors  : {len(anchors)}")
    print(f"Rejected anchors   : {len(rejected)}")
    print(f"Assigned           : {len(assignments)}")
    print()

    for status in [
        "CONFIRMED",
        "HIGH",
        "MEDIUM",
        "AMBIGUOUS",
        "UNMATCHED",
    ]:
        print(
            f"{status:12} : "
            f"{status_counts[status]}"
        )

    print()
    print(f"Segments          : {len(segment_results)}")
    print(f"Collisions        : {len(collisions)}")
    print()
    print(f"Output : {OUTPUT}")
    print(f"Report : {REPORT}")


if __name__ == "__main__":
    main()
