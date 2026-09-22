#!/usr/bin/env python3
"""Generate Italian text-symbol overrides for a ROM manifest.

Uses the pinned PokeCorpus and the empirically calibrated Italian codec from
italian_rom_locator.py. Only text labels with a unique full-ROM match are
promoted to the generated Italian manifest.

The base manifest is never modified.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from italian_rom_locator import (
    CONTROL_BYTES,
    ENTRY,
    expected_layout,
    load_corpus,
    load_mapping,
    static_calibration,
    tokenize,
    terminator_from_units,
    find_hits,
    bank_offset,
    offset_location,
)


def symbol_from_qid(qid: str) -> str:
    return "_" + qid.rsplit(".", 1)[-1]


def build_corpus_index(corpus):
    index = {}
    collisions = {}
    for row in corpus.values():
        symbol = symbol_from_qid(row.qid)
        if symbol in index:
            collisions.setdefault(symbol, []).append(row.qid)
        else:
            index[symbol] = row
    return index, collisions


def build_italian_charmap(codec):
    """Build the manifest charmap expected by build_rom_data.py.

    Control bytes are deliberately represented with angle-bracket tokens,
    matching the convention already used by the US manifest.
    """
    reverse = {}

    for token, byte in codec.items():
        # POKé is represented by the game's dedicated byte.
        if byte not in reverse:
            reverse[byte] = token

    # These are commands, not ordinary glyphs.
    reverse[CONTROL_BYTES["LINE"]] = "<LINE>"
    reverse[CONTROL_BYTES["PARA"]] = "<PARA>"
    reverse[CONTROL_BYTES["PLAYER"]] = "<PLAYER>"
    reverse[CONTROL_BYTES["POKE"]] = "<POKE>"
    reverse[CONTROL_BYTES["CONT"]] = "<CONT>"
    reverse[CONTROL_BYTES["DONE"]] = "<DONE>"
    reverse[CONTROL_BYTES["PROMPT"]] = "<PROMPT>"
    reverse[0x50] = "<TEXT_END>"
    reverse[ENTRY] = "<TEXT>"

    return {str(byte): value for byte, value in sorted(reverse.items())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-manifest", required=True)
    parser.add_argument("--ita-rom", required=True)
    parser.add_argument("--corpus-dir", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--output-report", required=True)
    args = parser.parse_args()

    base_path = Path(args.base_manifest)
    output_path = Path(args.output_manifest)
    report_path = Path(args.output_report)

    manifest = json.loads(base_path.read_text(encoding="utf-8"))
    corpus = load_corpus(Path(args.corpus_dir))
    rom = Path(args.ita_rom).read_bytes()
    mapping = load_mapping(Path(args.mapping))

    codec, reverse, control_evidence, calibration_count = static_calibration(
        rom, corpus, mapping
    )

    corpus_index, collisions = build_corpus_index(corpus)

    labels = manifest["text"]["labels"]

    overrides = {}
    resolved = []
    unresolved = []
    ambiguous = []
    ambiguous_corpus = []
    ambiguous_rom = []
    no_corpus = []
    encoding_unknown = []

    for symbol in labels:
        row = corpus_index.get(symbol)

        if row is None:
            no_corpus.append(symbol)
            continue

        if symbol in collisions:
            ambiguous_corpus.append((symbol, collisions[symbol]))
            continue

        try:
            units = tokenize(row.italian)
            terminal = terminator_from_units(units)

            missing = sorted(
                {
                    value
                    for kind, value in units
                    if kind == "GLYPH" and value not in codec
                }
            )

            if any(kind == "POKEMON" for kind, _ in units):
                missing.extend(
                    token for token in ("POKé", "M", "O", "N")
                    if token not in codec
                )

            if missing:
                raise KeyError(", ".join(sorted(set(missing))))

            if terminal is None:
                raise ValueError("missing typed DONE/PROMPT terminator")

            pattern = expected_layout(
                units,
                codec,
                wildcard_dynamic=True,
            )

        except (ValueError, KeyError) as exc:
            encoding_unknown.append((symbol, str(exc)))
            continue

        hits = find_hits(rom, pattern, terminal)

        if len(hits) == 1:
            hit = hits[0]
            bank, address = offset_location(hit.offset)

            overrides[symbol] = [bank, address]

            resolved.append(
                (
                    symbol,
                    row.qid,
                    bank,
                    address,
                    len(pattern),
                    sum(v is None for v in pattern),
                )
            )

        elif len(hits) == 0:
            unresolved.append((symbol, row.qid, "no full-ROM match"))

        else:
            ambiguous_rom.append(
                (
                    symbol,
                    row.qid,
                    hits,
                    len(pattern),
                    sum(v is None for v in pattern),
                )
            )

    ambiguous = [
        (symbol, "multiple PokeCorpus QIDs: " + ", ".join(qids))
        for symbol, qids in ambiguous_corpus
    ]
    ambiguous.extend(
        (symbol, f"{len(hits)} full-ROM matches")
        for symbol, qid, hits, pattern_len, wildcard_count in ambiguous_rom
    )

    # Create a copy of the manifest; never modify the source manifest.
    out_manifest = json.loads(json.dumps(manifest))

    # Keep all existing symbols as fallback, replacing only uniquely resolved
    # Italian text labels.
    symbols = out_manifest["symbols"]
    for symbol, location in overrides.items():
        symbols[symbol] = location

    # ROM identity must describe the target ROM.
    import hashlib

    out_manifest["romSha1"] = hashlib.sha1(rom).hexdigest()

    # Replace the character map with the empirically derived Italian subset,
    # while retaining the base map for bytes for which no Italian evidence was
    # available.
    italian_charmap = build_italian_charmap(codec)
    base_charmap = out_manifest.get("charmap", {})
    merged_charmap = dict(base_charmap)
    merged_charmap.update(italian_charmap)
    out_manifest["charmap"] = merged_charmap

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(out_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report = []
    report.append("ITALIAN TEXT MANIFEST GENERATION")
    report.append("=" * 80)
    report.append("")
    report.append(f"Base manifest: {base_path}")
    report.append(f"Italian ROM: {args.ita_rom}")
    report.append(f"Corpus: {args.corpus_dir}")
    report.append(f"Text labels in manifest: {len(labels)}")
    report.append(f"Calibration rows accepted: {calibration_count}")
    report.append(f"Calibrated codec tokens: {len(codec)}")
    report.append("")
    report.append(f"RESOLVED: {len(resolved)}")
    report.append(f"UNRESOLVED: {len(unresolved)}")
    report.append(f"AMBIGUOUS: {len(ambiguous)}")
    report.append(f"NO_CORPUS: {len(no_corpus)}")
    report.append(f"ENCODING_UNKNOWN: {len(encoding_unknown)}")
    report.append("")

    report.append("RESOLVED")
    report.append("-" * 80)
    for symbol, qid, bank, address, length, wildcards in resolved:
        report.append(
            f"{symbol}\t{qid}\t"
            f"{bank:02X}:{address:04X}\t"
            f"len={length}\twildcards={wildcards}"
        )

    report.append("")
    report.append("UNRESOLVED")
    report.append("-" * 80)
    for symbol, qid, reason in unresolved:
        report.append(f"{symbol}\t{qid}\t{reason}")

    report.append("")
    report.append("AMBIGUOUS")
    report.append("-" * 80)

    for symbol, qids in ambiguous_corpus:
        report.append(
            f"{symbol}\tmultiple PokeCorpus QIDs: {', '.join(qids)}"
        )

    for symbol, qid, hits, pattern_len, wildcard_count in ambiguous_rom:
        report.append(
            f"{symbol}\t{len(hits)} full-ROM matches\t{qid}\t"
            f"len={pattern_len}\twildcards={wildcard_count}"
        )
        for hit in hits:
            bank, address = offset_location(hit.offset)
            report.append(
                f"  - {bank:02X}:{address:04X}\toffset=0x{hit.offset:06X}"
            )

    report.append("")
    report.append("NO CORPUS")
    report.append("-" * 80)
    for symbol in no_corpus:
        report.append(symbol)

    report.append("")
    report.append("ENCODING UNKNOWN")
    report.append("-" * 80)
    for symbol, reason in encoding_unknown:
        report.append(f"{symbol}\t{reason}")

    report.append("")
    report.append("IMPORTANT")
    report.append("-" * 80)
    report.append(
        "Only uniquely matched Italian text streams were promoted. "
        "Unresolved symbols retain their base-manifest addresses."
    )
    report.append(
        "The generated manifest is therefore a build-time diagnostic artifact "
        "until all runtime-required text symbols are resolved."
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"Generated manifest: {output_path}")
    print(f"Generated report:   {report_path}")
    print(f"Text labels:        {len(labels)}")
    print(f"RESOLVED:           {len(resolved)}")
    print(f"UNRESOLVED:         {len(unresolved)}")
    print(f"AMBIGUOUS:          {len(ambiguous)}")
    print(f"NO_CORPUS:          {len(no_corpus)}")
    print(f"ENCODING_UNKNOWN:   {len(encoding_unknown)}")


if __name__ == "__main__":
    main()
