#!/usr/bin/env python3
"""Read-only structural validator for the existing Bank 0x20 mapping TSV."""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from pathlib import Path

from bank20_sequence_alignment import ANCHORS, _candidate_addresses, _chunk, _raw_similarity, _similarity, _structural_bytes
from rom_data import RomImage, SymbolTable, decode_text, load_manifest

ROOT = Path(__file__).resolve().parent
SUSPICIOUS = {
    "_OaksAideUhOhText",
    "_OaksAideHereYouGoText",
    "_MtMoon1FSuperNerdAfterBattleText",
    "_RocketHideoutB1FRocket4EndBattleText",
}


def length_score(left: int, right: int) -> float:
    if not left or not right:
        return float(left == right)
    return math.exp(-abs(math.log(right / left)))


def codes(data: bytes) -> bytes:
    return bytes(value for value in data if value <= 0x05 or value == 0x09)


def markers(data: bytes) -> bytes:
    return bytes(value for value in data if value == 0 or 0x50 <= value <= 0x5F)


def terminators(data: bytes) -> tuple[int, ...]:
    return tuple(value for value in data if value in (0x50, 0x57, 0x58, 0x5F))


def segment_for(address: int):
    for start_name, end_name in (
        ("_TrainerNameText", "_MtMoonB1FUnusedText"),
        ("_MtMoonB1FUnusedText", "_SilphCo5FRocket1EndBattleText"),
    ):
        if ANCHORS[start_name][0] <= address <= ANCHORS[end_name][0]:
            return start_name, end_name
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", default=str(ROOT / "bank20_mapping.tsv"))
    parser.add_argument("--usa-rom", default=str(ROOT.parent / "red-usa.gb"))
    parser.add_argument("--ita-rom", default=str(ROOT.parent / "red-ita.gb"))
    parser.add_argument("--manifest", default=str(ROOT / "rom_manifest.json"))
    parser.add_argument("--output-tsv", default=str(ROOT / "bank20_mapping_validation.tsv"))
    parser.add_argument("--output-report", default=str(ROOT / "bank20_mapping_validation.txt"))
    args = parser.parse_args()

    manifest = load_manifest(Path(args.manifest))
    symbols = sorted(
        (symbol for symbol in SymbolTable(manifest["symbols"]).by_name.values()
         if symbol.bank == 0x20),
        key=lambda symbol: (symbol.address, symbol.name),
    )
    by_name = {symbol.name: symbol for symbol in symbols}
    usa = RomImage(args.usa_rom, expected_sha1=None)
    ita = RomImage(args.ita_rom, expected_sha1=None)
    with Path(args.mapping).open(encoding="utf-8") as handle:
        mapping = list(csv.DictReader(handle, delimiter="\t"))

    rows = []
    for row in mapping:
        name = row["usa_symbol"]
        usa_address = int(row["usa_address"], 16)
        ita_address = int(row["ita_address"], 16) if row["ita_address"] else None
        segment = segment_for(usa_address)
        if not segment or ita_address is None:
            rows.append({**row, "classification": "UNMATCHED", "boundary_score": 0.0,
                         "terminator_score": 0.0, "control_code_score": 0.0,
                         "length_score": 0.0, "neighbor_score": 0.0,
                         "displacement_score": 0.0, "reference_score": "N/A",
                         "raw_similarity": 0.0, "evidence_summary": "no accepted address"})
            continue
        start_name, end_name = segment
        source_start, target_start = ANCHORS[start_name]
        source_end, target_end = ANCHORS[end_name]
        source_symbols = [s for s in symbols if source_start < s.address < source_end]
        candidates = [a for a in _candidate_addresses(ita, target_start, target_end)
                      if a > target_start]
        candidate_index = candidates.index(ita_address) if ita_address in candidates else None
        source_symbol = by_name[name]
        source_index = source_symbols.index(source_symbol) if source_symbol in source_symbols else None
        usa_end = (source_symbols[source_index + 1].address
                   if source_index is not None and source_index + 1 < len(source_symbols)
                   else source_end)
        ita_end = (candidates[candidate_index + 1]
                   if candidate_index is not None and candidate_index + 1 < len(candidates)
                   else target_end)
        usa_block = _chunk(usa, usa_address, usa_end)
        ita_block = _chunk(ita, ita_address, ita_end)
        usa_terms, ita_terms = terminators(usa_block), terminators(ita_block)
        boundary = float(candidate_index is not None and usa_end > usa_address and ita_end > ita_address)
        term_score = float(bool(usa_terms) == bool(ita_terms) and
                           (not usa_terms or usa_terms[-1] == ita_terms[-1]))
        control_score = _similarity(codes(usa_block), codes(ita_block))
        length = length_score(len(usa_block), len(ita_block))
        raw = _raw_similarity(usa_block[:32], ita_block[:32])
        previous = (target_start if candidate_index in (None, 0)
                    else candidates[candidate_index - 1])
        expected = target_start + (usa_address - source_start) * (target_end - target_start) / max(1, source_end - source_start)
        displacement = max(0.0, 1.0 - abs(ita_address - expected) / max(16.0, (target_end - target_start) / max(1, len(source_symbols))))
        neighbor = displacement
        if name in ANCHORS:
            classification = "VERIFIED"
        elif name in SUSPICIOUS:
            classification = "SUSPICIOUS"
        elif name in ("_OaksAideHiText", "_SSAnneKitchenCook7MainCourseIsText"):
            classification = "UNMATCHED"
        elif boundary and term_score and control_score >= 0.75 and length >= 0.75:
            classification = "VERIFIED"
        else:
            classification = "PLAUSIBLE"
        summary = (f"boundary={boundary:.0f}; terminator={term_score:.0f}; "
                   f"control={control_score:.3f}; length={length:.3f}; "
                   f"neighbor={neighbor:.3f}; displacement={displacement:.3f}; "
                   "reference=N/A; raw=secondary")
        rows.append({**row, "classification": classification,
                     "boundary_score": f"{boundary:.3f}",
                     "terminator_score": f"{term_score:.3f}",
                     "control_code_score": f"{control_score:.3f}",
                     "length_score": f"{length:.3f}",
                     "neighbor_score": f"{neighbor:.3f}",
                     "displacement_score": f"{displacement:.3f}",
                     "reference_score": "N/A", "raw_similarity": f"{raw:.3f}",
                     "evidence_summary": summary})

    fields = ["symbol", "usa_address", "ita_address", "classification",
              "boundary_score", "terminator_score", "control_code_score",
              "length_score", "neighbor_score", "displacement_score",
              "reference_score", "raw_similarity", "evidence_summary"]
    with Path(args.output_tsv).open("w", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({"symbol": row["usa_symbol"], **{field: row.get(field, "") for field in fields[1:]}})
    counts = Counter(row["classification"] for row in rows)
    report = [
        "BANK 0x20 DETERMINISTIC MAPPING VALIDATION", "",
        "Input mapping was read-only; no mapping or matching algorithm was modified.",
        "Reference consistency: N/A; no usable reference graph was found in the repository.",
        "Raw similarity is reported only as secondary evidence and is not a classification gate.", "",
        "Criteria:",
        "  boundary: assigned address is a discovered candidate with a valid block interval.",
        "  terminator: final terminator class agrees (50/57/58/5F).",
        "  control: SequenceMatcher similarity of control-code streams.",
        "  length: symmetric log-ratio plausibility of USA/ITA block lengths.",
        "  neighbor/displacement: position relative to segment span; descriptive only.",
        "  VERIFIED requires anchor exactness or valid boundary + terminator + control >= 0.75 + length >= 0.75.",
        "  The six previously identified problematic cases are never promoted by this validator.", "",
        f"COUNTS: {dict(counts)}", "",
        "GLOBAL ANALYSIS:",
        "  PLAUSIBLE rows lack a complete conjunction of independent structural criteria, most often control-stream or length evidence.",
        "  The four known suspicious rows are retained as SUSPICIOUS regardless of local score.",
        "  The two unaccepted rows are retained as UNMATCHED; provisional TSV addresses are not treated as accepted evidence.",
        "  The validator is reproducible and conservative, but it does not establish semantic translation equivalence.",
        "  Result: mapping is not ready for runtime integration based on this validation alone.", "",
        "Problematic rows:",
    ]
    for row in rows:
        if row["classification"] in ("SUSPICIOUS", "UNMATCHED"):
            report.append(f"  {row['usa_symbol']}: {row['classification']} ({row['evidence_summary']})")
    Path(args.output_report).write_text("\n".join(report) + "\n", encoding="utf-8")
    print("counts", dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())