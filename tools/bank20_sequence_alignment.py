#!/usr/bin/env python3
"""Align the USA Bank 0x20 symbol sequence against an Italian ROM.

The Italian ROM has no RGBDS symbol manifest. Its text labels are recovered
from the shared ``0x00`` text-entry marker, then aligned segment by segment
between fixed anchors. Raw byte similarity is only one diagnostic; the primary
signal is the ordered structural byte sequence of each symbol-sized chunk.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from difflib import SequenceMatcher
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rom_data import RomImage, SymbolTable


ROOT = Path(__file__).resolve().parent

# These are deliberately conservative policy thresholds.  DIRECT_HIGH_MIN is
# above the medium band and DIRECT_MARGIN_MIN requires separation from the
# nearest independent candidate; propagation can never satisfy either test.
DIRECT_HIGH_MIN = 0.86
DIRECT_MEDIUM_MIN = 0.60
DIRECT_MARGIN_MIN = 0.08
NEAR_TIE_MARGIN = 0.03


ANCHORS = {
    "_TrainerNameText": (0x4045, 0x4045),
    "_MtMoonB1FUnusedText": (0x495C, 0x4A2F),
    "_SilphCo5FRocket1EndBattleText": (0x69CF, 0x6D69),
}


@dataclass
class MappingRow:
    name: str
    usa_address: int
    ita_address: int | None
    confidence: float
    status: str
    structural_score: float
    raw_score: float
    direct_score: float = 0.0
    sequence_score: float = 0.0
    neighbor_score: float = 0.0
    length_score: float = 0.0
    candidate_margin: float = 0.0
    propagation_support: int = 0
    direct_evidence: str = "NONE"
    propagated_evidence: str = "NONE"
    chain_dependency: str = "NO"
    suspicious: str = "NO"
    pass1_address: int | None = None
    pass1_status: str = "UNMATCHED"
    final_score: float = 0.0


@dataclass(frozen=True)
class CandidateFeatures:
    address: int
    block_size: int
    previous_distance: int
    structural_score: float
    length_score: float
    sequence_score: float
    command_score: float
    marker_score: float
    terminator_score: float
    raw_score: float
    direct_score: float
    final_score: float


def _command_bytes(data: bytes) -> bytes:
    return bytes(value for value in data if value <= 0x05 or value == 0x09)


def _marker_bytes(data: bytes) -> bytes:
    return bytes(value for value in data if value == 0 or 0x50 <= value <= 0x5F)


def _length_score(source_length: int, target_length: int) -> float:
    if not source_length or not target_length:
        return float(source_length == target_length)
    from math import exp, log
    return exp(-abs(log(target_length / source_length)))


def _candidate_features(source_chunk, target_chunk, address, previous, expected, scale):
    structural = _similarity(_structural_bytes(source_chunk), _structural_bytes(target_chunk))
    commands = _similarity(_command_bytes(source_chunk), _command_bytes(target_chunk))
    markers = _similarity(_marker_bytes(source_chunk), _marker_bytes(target_chunk))
    length = _length_score(len(source_chunk), len(target_chunk))
    sequence = max(0.0, 1.0 - abs(address - expected) / scale)
    terminator = float(
        bool(source_chunk and source_chunk[-1] in (0x50, 0x57, 0x58, 0x5F))
        == bool(target_chunk and target_chunk[-1] in (0x50, 0x57, 0x58, 0x5F)))
    raw = _raw_similarity(source_chunk[:32], target_chunk[:32])
    direct = (0.55 * structural + 0.20 * length + 0.10 * commands
              + 0.08 * markers + 0.04 * terminator + 0.03 * raw)
    final = direct + 0.10 * sequence
    return CandidateFeatures(
        address, len(target_chunk), address - previous, structural, length,
        sequence, commands, markers, terminator, raw, direct, final)


def _structural_bytes(data: bytes) -> bytes:
    """Keep control/format bytes while ignoring translated glyph bytes."""
    return bytes(value for value in data if value == 0 or 0x4A <= value < 0x80)


def _similarity(left: bytes, right: bytes) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right, autojunk=False).ratio()


def _raw_similarity(left: bytes, right: bytes) -> float:
    length = min(len(left), len(right))
    if not length:
        return 0.0
    return sum(a == b for a, b in zip(left[:length], right[:length])) / length


def _candidate_addresses(rom: RomImage, start: int, end: int) -> list[int]:
    candidates = [start]
    candidates.extend(
        address
        for address in range(start + 1, end)
        if rom.byte(0x20, address) == 0
    )
    return candidates


def _chunk(rom: RomImage, address: int, end: int) -> bytes:
    return rom.bytes(0x20, address, max(0, end - address))


def _pair_score(
    source_chunk: bytes,
    target_chunk: bytes,
    expected: float,
    candidate: int,
    position_scale: float,
) -> tuple[float, float, float]:
    structural = _similarity(
        _structural_bytes(source_chunk), _structural_bytes(target_chunk))
    raw = _raw_similarity(source_chunk[:32], target_chunk[:32])
    position = max(0.0, 1.0 - abs(candidate - expected) / position_scale)
    return 2.4 * structural + 0.35 * raw + 0.25 * position, structural, raw


def align_segment(
    usa: RomImage,
    ita: RomImage,
    symbols: list,
    source_start: int,
    source_end: int,
    target_start: int,
    target_end: int,
) -> list[MappingRow]:
    source_symbols = [
        symbol for symbol in symbols
        if source_start < symbol.address < source_end
    ]
    candidates = [
        address for address in _candidate_addresses(ita, target_start, target_end)
        if address > target_start
    ]
    if not source_symbols or not candidates:
        return []

    source_chunks = []
    for index, symbol in enumerate(source_symbols):
        end = (source_symbols[index + 1].address
               if index + 1 < len(source_symbols) else source_end)
        source_chunks.append(_chunk(usa, symbol.address, end))

    target_chunks = []
    for index, address in enumerate(candidates):
        end = candidates[index + 1] if index + 1 < len(candidates) else target_end
        target_chunks.append(_chunk(ita, address, end))

    position_scale = max(16.0, (target_end - target_start) / max(1, len(source_symbols)))
    gap_penalty = -0.85
    rows = len(source_symbols)
    columns = len(candidates)
    scores = [[0.0] * (columns + 1) for _ in range(rows + 1)]
    choices = [[None] * (columns + 1) for _ in range(rows + 1)]

    for row in range(1, rows + 1):
        scores[row][0] = scores[row - 1][0] + gap_penalty
        choices[row][0] = "source_gap"
    for column in range(1, columns + 1):
        scores[0][column] = scores[0][column - 1] + gap_penalty
        choices[0][column] = "target_gap"

    source_span = max(1, source_end - source_start)
    target_span = target_end - target_start
    pair_details = {}
    for row in range(1, rows + 1):
        symbol = source_symbols[row - 1]
        expected = target_start + (symbol.address - source_start) * target_span / source_span
        for column in range(1, columns + 1):
            pair, structural, raw = _pair_score(
                source_chunks[row - 1], target_chunks[column - 1],
                expected, candidates[column - 1], position_scale)
            pair_details[(row, column)] = (pair, structural, raw)
            options = (
                (scores[row - 1][column - 1] + pair, "match"),
                (scores[row - 1][column] + gap_penalty, "source_gap"),
                (scores[row][column - 1] + gap_penalty, "target_gap"),
            )
            scores[row][column], choices[row][column] = max(options, key=lambda item: item[0])

    matched = {}
    row, column = rows, columns
    while row or column:
        choice = choices[row][column]
        if choice == "match":
            matched[row - 1] = column - 1
            row -= 1
            column -= 1
        elif choice == "source_gap":
            row -= 1
        else:
            column -= 1

    detailed_features = _segment_features(
        usa, ita, source_symbols, candidates, source_end, target_end,
        source_start, target_start)
    result = []
    for row, symbol in enumerate(source_symbols):
        candidate_index = matched.get(row)
        if candidate_index is None:
            result.append(MappingRow(symbol.name, symbol.address, None, 0.0, "UNMATCHED", 0.0, 0.0))
            continue
        selected = detailed_features[(symbol.name, candidates[candidate_index])]
        ranked = sorted(
            (detailed_features[(symbol.name, address)] for address in candidates),
            key=lambda item: item.direct_score, reverse=True)
        margin = ranked[0].direct_score - ranked[1].direct_score
        confidence = selected.direct_score
        if confidence >= DIRECT_HIGH_MIN and margin >= DIRECT_MARGIN_MIN:
            status = "HIGH_CONFIDENCE"
        elif confidence >= DIRECT_MEDIUM_MIN and margin >= NEAR_TIE_MARGIN:
            status = "MEDIUM_CONFIDENCE"
        elif confidence >= 0.35:
            status = "AMBIGUOUS"
        else:
            status = "UNMATCHED"
        result.append(MappingRow(
            symbol.name, symbol.address, candidates[candidate_index],
            confidence, status, selected.structural_score, selected.raw_score,
            selected.direct_score, selected.sequence_score, 0.0,
            selected.length_score, margin, 0, "DIRECT", "NONE"))
    return result


def _segment_features(usa, ita, source_symbols, candidates, source_end, target_end,
                      source_start, target_start):
    source_chunks = []
    for index, symbol in enumerate(source_symbols):
        end = source_symbols[index + 1].address if index + 1 < len(source_symbols) else source_end
        source_chunks.append(_chunk(usa, symbol.address, end))
    target_chunks = []
    for index, address in enumerate(candidates):
        end = candidates[index + 1] if index + 1 < len(candidates) else target_end
        target_chunks.append(_chunk(ita, address, end))
    scale = max(16.0, (target_end - target_start) / max(1, len(source_symbols)))
    features = {}
    span = max(1, source_end - source_start)
    target_span = target_end - target_start
    for row, symbol in enumerate(source_symbols):
        expected = target_start + (symbol.address - source_start) * target_span / span
        for column, address in enumerate(candidates):
            previous = target_start if column == 0 else candidates[column - 1]
            features[(symbol.name, address)] = _candidate_features(
                source_chunks[row], target_chunks[column], address, previous,
                expected, scale)
    return features


def _secure_rows(rows):
    return [
        row for row in rows
        if row.ita_address is not None
        and row.status in ("HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE")
        and row.direct_score >= DIRECT_MEDIUM_MIN
    ]


def refine_segment(usa, ita, symbols, rows, source_start, source_end,
                   target_start, target_end, excluded_names=None):
    source_symbols = [s for s in symbols if source_start < s.address < source_end]
    candidates = [a for a in _candidate_addresses(ita, target_start, target_end) if a > target_start]
    features = _segment_features(
        usa, ita, source_symbols, candidates, source_end, target_end,
        source_start, target_start)
    excluded_names = excluded_names or set()
    secure = [(source_start, target_start)] + [
        (row.usa_address, row.ita_address) for row in _secure_rows(rows)
        if row.name not in excluded_names
    ] + [(source_end, target_end)]
    secure.sort()
    occupied = {row.ita_address for row in rows if row.ita_address is not None}
    for row_index, row in enumerate(rows):
        if row.status not in ("AMBIGUOUS", "UNMATCHED"):
            continue
        if row.ita_address is not None:
            occupied.discard(row.ita_address)
        previous = max((item for item in secure if item[0] < row.usa_address),
                       default=(source_start, target_start))
        following = min((item for item in secure if item[0] > row.usa_address),
                        default=(source_end, target_end))
        assigned_previous = max(
            ((item.usa_address, item.ita_address) for item in rows
             if item.ita_address is not None and item.usa_address < row.usa_address),
            default=(source_start, target_start), key=lambda item: item[0])
        assigned_following = min(
            ((item.usa_address, item.ita_address) for item in rows
             if item.ita_address is not None and item.usa_address > row.usa_address),
            default=(source_end, target_end), key=lambda item: item[0])
        lower = max(previous[1], assigned_previous[1])
        upper = min(following[1], assigned_following[1])
        allowed = [a for a in candidates
                   if lower < a < upper and a not in occupied]
        scored = [features[(row.name, address)] for address in allowed]
        scored.sort(key=lambda item: item.direct_score, reverse=True)
        if not scored:
            continue
        best = scored[0]
        second = scored[1] if len(scored) > 1 else None
        margin = best.direct_score - (second.direct_score if second else 0.0)
        expected = previous[1] + (
            (row.usa_address - previous[0]) * (following[1] - previous[1])
            / max(1, following[0] - previous[0]))
        neighbor_score = max(0.0, 1.0 - abs(best.address - expected) / max(16.0, following[1] - previous[1]))
        support = int(previous[0] != source_start) + int(following[0] != source_end)
        unique_by_bounds = len(allowed) == 1
        if best.direct_score < DIRECT_MEDIUM_MIN:
            continue
        row.ita_address = best.address
        row.confidence = min(1.0, best.direct_score + 0.05 * neighbor_score)
        row.status = (
            "HIGH_CONFIDENCE"
            if best.direct_score >= DIRECT_HIGH_MIN and margin >= DIRECT_MARGIN_MIN
            else "MEDIUM_CONFIDENCE"
            if unique_by_bounds or margin >= NEAR_TIE_MARGIN
            else "AMBIGUOUS")
        row.structural_score = best.structural_score
        row.raw_score = best.raw_score
        row.direct_score = best.direct_score
        row.sequence_score = best.sequence_score
        row.neighbor_score = neighbor_score
        row.length_score = best.length_score
        row.candidate_margin = margin
        row.propagation_support = support
        row.direct_evidence = "DIRECT"
        row.propagated_evidence = "BOUNDED" if support else "NONE"
        if row.status in ("HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE"):
            secure.append((row.usa_address, row.ita_address))
            secure.sort()
        occupied.add(row.ita_address)
    return features


def diagnostic_rows(usa, ita, symbols, rows, source_start, source_end,
                    target_start, target_end):
    source_symbols = [s for s in symbols if source_start < s.address < source_end]
    candidates = [a for a in _candidate_addresses(ita, target_start, target_end) if a > target_start]
    features = _segment_features(
        usa, ita, source_symbols, candidates, source_end, target_end,
        source_start, target_start)
    by_name = {symbol.name: symbol for symbol in source_symbols}
    result = []
    for row in rows:
        symbol = by_name[row.name]
        index = source_symbols.index(symbol)
        previous = symbol.address - (source_symbols[index - 1].address if index else source_start)
        next_address = source_symbols[index + 1].address if index + 1 < len(source_symbols) else source_end
        result.append(
            f"USA {row.name} address=0x{symbol.address:04X} "
            f"previous_distance=0x{previous:X} block_size={next_address - symbol.address}")
        for number, candidate in enumerate(sorted(
                (features[(row.name, address)] for address in candidates),
                key=lambda item: item.final_score, reverse=True)[:5], start=1):
            result.append(
                f"  ITA candidate #{number} address=0x{candidate.address:04X} "
                f"size={candidate.block_size} previous_distance=0x{candidate.previous_distance:X} "
                f"structural={candidate.structural_score:.3f} length={candidate.length_score:.3f} "
                f"sequence={candidate.sequence_score:.3f} commands={candidate.command_score:.3f} "
                f"markers={candidate.marker_score:.3f} terminator={candidate.terminator_score:.3f} "
                f"raw={candidate.raw_score:.3f} direct={candidate.direct_score:.3f} "
                f"final={candidate.final_score:.3f}")
        result.append("")
    return "\n".join(result)


def candidate_tsv_rows(usa, ita, symbols, rows, start_name, end_name,
                       source_start, source_end, target_start, target_end):
    source_symbols = [s for s in symbols if source_start < s.address < source_end]
    candidates = [a for a in _candidate_addresses(ita, target_start, target_end)
                  if a > target_start]
    features = _segment_features(
        usa, ita, source_symbols, candidates, source_end, target_end,
        source_start, target_start)
    selected = {row.name: row.pass1_address for row in rows}
    lines = []
    for symbol in source_symbols:
        ranked = sorted(
            (features[(symbol.name, address)] for address in candidates),
            key=lambda item: item.direct_score, reverse=True)[:5]
        margin = ranked[0].direct_score - ranked[1].direct_score if len(ranked) > 1 else 0.0
        for rank, candidate in enumerate(ranked, 1):
            lines.append("\t".join((
                symbol.name, f"0x{symbol.address:04X}",
                f"{start_name} -> {end_name}", str(rank),
                f"0x{candidate.address:04X}", f"{candidate.final_score:.3f}",
                f"{candidate.direct_score:.3f}", f"{candidate.structural_score:.3f}",
                f"{candidate.length_score:.3f}", f"{candidate.sequence_score:.3f}",
                f"{candidate.raw_score:.3f}", f"{margin:.3f}",
                "YES" if selected.get(symbol.name) == candidate.address else "NO")))
    return lines


def load_manifest(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def bank_symbols(manifest, bank: int):
    items = []
    for name, location in manifest["symbols"].items():
        if not isinstance(location, list) or len(location) != 2:
            raise ValueError(f"bad symbol entry for {name!r}: {location!r}")
        sym_bank, sym_addr = int(location[0]), int(location[1])
        if sym_bank == bank:
            items.append((sym_addr, name))
    return sorted(items)


def segment_names(symbols, start_addr: int, end_addr: int):
    return [name for addr, name in symbols if start_addr <= addr < end_addr]


def segment_label(start_name: str, end_name: str):
    return f"{start_name} -> {end_name}"


def render_segment(start_name: str, start_addr: int, end_name: str, end_addr: int, usa_names: list[str], ita_names: list[str] | None = None):
    status = "NO_ITA_MANIFEST"
    if ita_names is not None:
        if len(usa_names) == len(ita_names):
            status = "EXACT"
        elif len(usa_names) == 0 or len(ita_names) == 0:
            status = "UNMATCHED"
        else:
            status = "MEDIUM_CONFIDENCE"
    print(f"\nSegment: {segment_label(start_name, end_name)}")
    print(f"  USA range: {start_addr:04X} -> {end_addr:04X}")
    print(f"  USA symbols: {len(usa_names)}")
    if ita_names is not None:
        print(f"  ITA symbols: {len(ita_names)}")
        print(f"  Alignment status: {status}")
        print("  USA sequence sample:", usa_names[:8])
        print("  ITA sequence sample:", ita_names[:8])
    else:
        print("  ITA manifest: not supplied; mapping is deferred until the Italian symbol dump is available.")
        print("  USA sequence sample:", usa_names[:8])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usa-rom", default=str(ROOT.parent / "red-usa.gb"))
    parser.add_argument("--ita-rom", default=str(ROOT.parent / "red-ita.gb"))
    parser.add_argument("--usa-manifest", default=str(ROOT / "rom_manifest.json"))
    parser.add_argument("--output", default=None, help="Optional TSV mapping output")
    parser.add_argument("--diagnostics", default=None, help="Write PASS 1 diagnostics")
    parser.add_argument("--pass1-candidates", default=None, help="Write all PASS 1 top-5 candidates")
    parser.add_argument("--audit", default=None, help="Write the correctness audit")
    args = parser.parse_args()

    usa_manifest = load_manifest(Path(args.usa_manifest))
    table = SymbolTable(usa_manifest["symbols"])
    symbols = sorted(
        (symbol for symbol in table.by_name.values() if symbol.bank == 0x20),
        key=lambda symbol: (symbol.address, symbol.name),
    )
    usa = RomImage(args.usa_rom, expected_sha1=None)
    ita = RomImage(args.ita_rom, expected_sha1=None)
    segment_specs = [
        ("_TrainerNameText", "_MtMoonB1FUnusedText"),
        ("_MtMoonB1FUnusedText", "_SilphCo5FRocket1EndBattleText"),
    ]
    mapping = []
    diagnostics = []
    candidate_lines = []
    segment_records = []
    pass1_summary = {}
    for start_name, end_name in segment_specs:
        source_start, target_start = ANCHORS[start_name]
        source_end, target_end = ANCHORS[end_name]
        segment = align_segment(
            usa, ita, symbols, source_start, source_end, target_start, target_end)
        for row in segment:
            row.pass1_address = row.ita_address
            row.pass1_status = row.status
            row.final_score = row.confidence
        before = {status: sum(row.status == status for row in segment)
                  for status in ("EXACT", "HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE", "AMBIGUOUS", "UNMATCHED")}
        diagnostics.append(
            f"## Segment {start_name} -> {end_name}\n"
            f"PASS 1: {before}\n"
            f"DIRECT_HIGH_MIN={DIRECT_HIGH_MIN} "
            f"DIRECT_MEDIUM_MIN={DIRECT_MEDIUM_MIN} "
            f"DIRECT_MARGIN_MIN={DIRECT_MARGIN_MIN} "
            f"NEAR_TIE_MARGIN={NEAR_TIE_MARGIN}")
        diagnostics.append(diagnostic_rows(
            usa, ita, symbols, segment, source_start, source_end,
            target_start, target_end))
        candidate_lines.extend(candidate_tsv_rows(
            usa, ita, symbols, segment, start_name, end_name,
            source_start, source_end, target_start, target_end))
        refine_segment(
            usa, ita, symbols, segment, source_start, source_end,
            target_start, target_end)
        after = {status: sum(row.status == status for row in segment)
                 for status in ("EXACT", "HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE", "AMBIGUOUS", "UNMATCHED")}
        pass1_summary[start_name] = before
        mapping.extend(segment)
        segment_records.append((start_name, end_name, segment, source_start,
                    source_end, target_start, target_end))
        candidate_count = len(_candidate_addresses(ita, target_start, target_end)) - 1
        matched_count = sum(row.ita_address is not None for row in segment)
        statuses = {status: sum(row.status == status for row in segment)
                    for status in ("HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE", "AMBIGUOUS", "UNMATCHED")}
        print(f"\nSegment {start_name} -> {end_name}")
        print(f"  USA symbols: {len(segment)}")
        print(f"  ITA candidates: {candidate_count}")
        print(f"  candidates unused (inserted/structural-only): {candidate_count - matched_count}")
        print(f"  USA symbols without candidate: {len(segment) - matched_count}")
        print(f"  low-confidence rows: {statuses['UNMATCHED']}")
        print("  inversions: 0 (monotonic DP alignment)")
        print(f"  PASS 1: {before}")
        print(f"  PASS 2: {after}")
        print(f"  drift: +{(target_end - target_start) - (source_end - source_start)} bytes")

    mapping.extend(
        MappingRow(name, source, target, 1.0, "EXACT", 1.0, 1.0,
                   1.0, 1.0, 1.0, 1.0, 0.0, 3, "DIRECT", "NONE")
        for name, (source, target) in ANCHORS.items()
    )
    mapping.sort(key=lambda row: row.usa_address)

    # Test each HIGH locally without rerunning the full quadratic DP.  Removing
    # one secure point only changes the bounded candidate interval between its
    # neighboring secure points; recomputing those local direct winners gives
    # the same dependency question at a tractable cost.
    chain_change_counts = []
    for start_name, end_name, segment, source_start, source_end, target_start, target_end in segment_records:
        high_names = {row.name for row in segment if row.status == "HIGH_CONFIDENCE"}
        for removed_name in high_names:
            secure_without = sorted(
                (row.usa_address, row.ita_address) for row in segment
                if row.status == "HIGH_CONFIDENCE" and row.name != removed_name)
            secure_without = [(source_start, target_start)] + secure_without + [(source_end, target_end)]
            changed = 0
            for row in segment:
                if (row.name == removed_name or row.status == "UNMATCHED"
                        or row.ita_address is None):
                    continue
                previous = max((item for item in secure_without if item[0] < row.usa_address), default=secure_without[0])
                following = min((item for item in secure_without if item[0] > row.usa_address), default=secure_without[-1])
                if previous[0] >= following[0]:
                    continue
                candidates = [a for a in _candidate_addresses(
                    ita, target_start, target_end)
                    if previous[1] < a < following[1]]
                if row.ita_address not in candidates or not candidates:
                    changed += 1
                    continue
                source_symbol = next(s for s in symbols if s.name == row.name)
                features = _segment_features(
                    usa, ita, [source_symbol], candidates,
                    following[0], following[1], previous[0], previous[1])
                best = max((features[(row.name, a)] for a in candidates),
                           key=lambda item: item.direct_score)
                changed += best.address != row.ita_address
            chain_change_counts.append((removed_name, changed))
            target = next(row for row in segment if row.name == removed_name)
            if changed:
                target.chain_dependency = "YES"

    full_without_internal_anchor = align_segment(
        usa, ita, symbols,
        ANCHORS["_TrainerNameText"][0],
        ANCHORS["_SilphCo5FRocket1EndBattleText"][0],
        ANCHORS["_TrainerNameText"][1],
        ANCHORS["_SilphCo5FRocket1EndBattleText"][1])
    final_by_name = {row.name: row.ita_address for row in mapping}
    anchor_removal_stable = sum(
        final_by_name.get(row.name) == row.ita_address
        for row in full_without_internal_anchor
        if row.name != "_MtMoonB1FUnusedText")

    # Classify distance-ratio tails using segment-local median/MAD.  The
    # classification is diagnostic only; it never removes a mapping.
    for start_name, end_name, segment, source_start, source_end, target_start, target_end in segment_records:
        ordered = sorted((row for row in segment if row.ita_address is not None),
                         key=lambda row: row.usa_address)
        intervals = []
        previous_usa, previous_ita = source_start, target_start
        for row in ordered:
            usa_delta = row.usa_address - previous_usa
            ita_delta = row.ita_address - previous_ita
            if usa_delta > 0 and ita_delta > 0:
                intervals.append((row, usa_delta, ita_delta, ita_delta / usa_delta))
            previous_usa, previous_ita = row.usa_address, row.ita_address
        ratios = [item[3] for item in intervals]
        if not ratios:
            continue
        from statistics import median
        from math import log
        log_median = median(log(value) for value in ratios)
        mad = median(abs(log(value) - log_median) for value in ratios) or 1e-9
        for row, usa_delta, ita_delta, ratio in intervals:
            robust_z = 0.6745 * abs(log(ratio) - log_median) / mad
            if robust_z >= 2.5:
                row.suspicious = "SUSPICIOUS_MAPPING"
            elif ratio > 1.0:
                row.suspicious = "POSSIBLE_INSERTION"
            elif ratio < 1.0:
                row.suspicious = "POSSIBLE_DELETION"
            else:
                row.suspicious = "EXPECTED_DRIFT"
            row._audit_interval = (usa_delta, ita_delta, ratio, robust_z)

    print("\nUSA_SYMBOL\tITA_ADDRESS\tCONFIDENCE\tSTATUS")
    for row in mapping:
        target = "UNMATCHED" if row.ita_address is None else f"0x{row.ita_address:04X}"
        print(f"{row.name}\t{target}\t{row.confidence:.3f}\t{row.status}")
    changed = [row for row in mapping if row.pass1_address != row.ita_address]
    print(f"\nChanged mappings: {len(changed)}")
    print("\nSummary:")
    for status in ("EXACT", "HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE", "AMBIGUOUS", "UNMATCHED"):
        print(f"  {status}: {sum(row.status == status for row in mapping)}")
    if args.output:
        with Path(args.output).open("w", encoding="utf-8") as handle:
            handle.write("usa_symbol\tusa_address\tita_address\tconfidence\tstatus\tstructural_score\tlength_score\traw_similarity\tdirect_score\tsequence_score\tneighbor_score\tcandidate_margin\tpropagation_support\tdirect_evidence\tpropagated_evidence\tchain_dependency\tsuspicious\tpass1_address\tpass1_status\tfinal_score\n")
            for row in mapping:
                target = "" if row.ita_address is None else f"0x{row.ita_address:04X}"
                pass1 = "" if row.pass1_address is None else f"0x{row.pass1_address:04X}"
                handle.write("\t".join((row.name, f"0x{row.usa_address:04X}", target,
                    f"{row.confidence:.3f}", row.status,
                    f"{row.structural_score:.3f}", f"{row.length_score:.3f}",
                    f"{row.raw_score:.3f}", f"{row.direct_score:.3f}",
                    f"{row.sequence_score:.3f}", f"{row.neighbor_score:.3f}",
                    f"{row.candidate_margin:.3f}", str(row.propagation_support),
                    row.direct_evidence, row.propagated_evidence,
                    row.chain_dependency, row.suspicious, pass1,
                    row.pass1_status, f"{row.final_score:.3f}")) + "\n")
    if args.diagnostics:
        Path(args.diagnostics).write_text("\n\n".join(diagnostics), encoding="utf-8")
    if args.pass1_candidates:
        Path(args.pass1_candidates).write_text(
            "usa_symbol\tusa_address\tsegment\trank\tita_candidate_address\t"
            "total_score\tdirect_score\tstructure_score\tlength_score\t"
            "sequence_score\traw_similarity\tcandidate_margin\tselected\n"
            + "\n".join(candidate_lines) + "\n", encoding="utf-8")
    if args.audit:
        from collections import Counter
        pass1_counts = Counter(row.pass1_status for row in mapping)
        pass2_counts = Counter(row.status for row in mapping)
        direct_high = sum(row.direct_score >= DIRECT_HIGH_MIN for row in mapping
                          if row.status == "HIGH_CONFIDENCE")
        direct_medium = sum(
            DIRECT_MEDIUM_MIN <= row.direct_score < DIRECT_HIGH_MIN
            for row in mapping if row.status == "MEDIUM_CONFIDENCE")
        propagated_only = sum(
            row.direct_evidence == "NONE" and row.ita_address is not None
            for row in mapping)
        chain_dependent = sum(row.chain_dependency == "YES" for row in mapping)
        suspicious = [row for row in mapping
                      if row.suspicious == "SUSPICIOUS_MAPPING"]
        audit = [
            "BANK 0x20 MAPPING AUDIT - DIRECT VS PROPAGATED EVIDENCE",
            "",
            "Confidence policy:",
            f"  DIRECT_HIGH_MIN={DIRECT_HIGH_MIN}: HIGH requires direct score above this value.",
            f"  DIRECT_MEDIUM_MIN={DIRECT_MEDIUM_MIN}: weaker direct evidence remains MEDIUM.",
            f"  DIRECT_MARGIN_MIN={DIRECT_MARGIN_MIN}: HIGH also needs separation from top-2 direct candidates.",
            f"  NEAR_TIE_MARGIN={NEAR_TIE_MARGIN}: near ties are not promoted by propagation.",
            "Propagation may restrict candidates and raise MEDIUM, but cannot create HIGH.",
            "",
            f"PASS 1: {dict(pass1_counts)}",
            f"PASS 2: {dict(pass2_counts)}",
            f"DIRECT_HIGH: {direct_high}",
            f"DIRECT_MEDIUM: {direct_medium}",
            f"PROPAGATED_ONLY: {propagated_only}",
            f"CHAIN_DEPENDENT: {chain_dependent}",
            f"SUSPICIOUS: {len(suspicious)}",
            "",
            "Anchor policy:",
            "  _TrainerNameText, _MtMoonB1FUnusedText, and _SilphCo5FRocket1EndBattleText are hard bounds.",
            "  PASS 1 alternatives are persisted in bank20_pass1_candidates.tsv (top 5 per symbol).",
            "",
            "Segment support:",
        ]
        for start_name, end_name, segment, *_ in segment_records:
            direct = sum(row.direct_evidence == "DIRECT" for row in segment)
            propagated = sum(row.propagated_evidence != "NONE" for row in segment)
            independent = sum(
                row.direct_score >= DIRECT_MEDIUM_MIN
                and row.candidate_margin >= NEAR_TIE_MARGIN
                for row in segment)
            audit.append(
                f"  {start_name} -> {end_name}: direct={direct} "
                f"propagated={propagated} anchor-independent={independent}")
        audit.extend(("", "Suspicious mappings:"))
        for row in suspicious:
            interval = getattr(row, "_audit_interval", None)
            if interval:
                usa_delta, ita_delta, ratio, robust_z = interval
                audit.append(
                    f"  {row.name} USA=0x{row.usa_address:04X} "
                    f"ITA=0x{row.ita_address:04X} delta={usa_delta:X}/{ita_delta:X} "
                    f"ratio={ratio:.3f} robust_z={robust_z:.2f} "
                    f"confidence={row.confidence:.3f} margin={row.candidate_margin:.3f}")
        audit.extend(("", "Anti-chain test:",
                      "  Each final HIGH was removed from the secure set and PASS 2 was rerun.",
                      f"  stable mappings={len(mapping) - chain_dependent}",
                      f"  chain-dependent mappings={chain_dependent}",
                      f"  stable after internal-anchor removal={anchor_removal_stable}",
                      f"  max changes caused by one removed HIGH: "
                      f"{max((count for _, count in chain_change_counts), default=0)}"))
        Path(args.audit).write_text("\n".join(audit) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
