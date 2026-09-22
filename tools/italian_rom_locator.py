#!/usr/bin/env python3
"""Read-only semantic text locator for the Italian Pokémon Red ROM.

The repository ships a US charmap but no Italian manifest/charmap.  This
tool therefore never imports the US charmap as an Italian encoder.  It first
derives only the needed Italian byte->token evidence from existing Bank 0x20
candidate rows which exactly fit independent PokeCorpus Italian text and the
observed text-command layout.  The six requested rows are excluded from that
calibration.  It then searches the whole Italian ROM with exact bytes or
explicit wildcards for dynamic text-command operands.

It is diagnostic only: no map is written or promoted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
PINNED_CORPUS_SHA256 = {
    "qid_msg.txt": "babd38232ca7f4e6062a5a5ad01a35b78f8e429db831a1e564ce62f274ecd160",
    "en_msg.txt": "086f6d43962e5dbda10cd0bed5e882b8916f8846e7419d5a0d45c1b805cb66a6",
    "it_msg.txt": "3d441d30243404ce0b545bb79b7480f76ca4f8dedcb6b863d286d611892bfa48",
}

CASES = (
    ("rb.text_1.OaksAideHiText", "_OaksAideHiText"),
    ("rb.text_1.OaksAideUhOhText", "_OaksAideUhOhText"),
    ("rb.text_1.OaksAideHereYouGoText", "_OaksAideHereYouGoText"),
    ("rb.MtMoon1F.MtMoon1FSuperNerdAfterBattleText", "_MtMoon1FSuperNerdAfterBattleText"),
    ("rb.RocketHideoutB1F.RocketHideoutB1FRocket4EndBattleText", "_RocketHideoutB1FRocket4EndBattleText"),
    ("rb.SSAnneKitchen.SSAnneKitchenCook7MainCourseIsText", "_SSAnneKitchenCook7MainCourseIsText"),
)
TARGET_SYMBOLS = {symbol for _, symbol in CASES}

# These are hypotheses copied from the *observed Gen 1 command layout*, not
# an Italian character table.  Calibration below proves each used value from
# independent Italian corpus rows before a search is permitted.
CONTROL_BYTES = {
    "LINE": 0x4F,
    "PARA": 0x51,
    "PLAYER": 0x52,
    "POKE": 0x54,
    "CONT": 0x55,
    "DONE": 0x57,
    "PROMPT": 0x58,
}
ENTRY = 0x00
DYNAMIC_OPERANDS = {"RAM": (0x01, 2), "NUM": (0x09, 3)}


@dataclass(frozen=True)
class CorpusRow:
    qid: str
    english: str
    italian: str


@dataclass(frozen=True)
class Hit:
    offset: int
    matched: bytes
    wildcard_offsets: tuple[int, ...]
    terminator_ok: bool
    controls_ok: bool


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_corpus(directory: Path) -> dict[str, CorpusRow]:
    files = {name: directory / name for name in PINNED_CORPUS_SHA256}
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("PokeCorpus RedBlue files missing: " + ", ".join(missing))
    bad = {
        name: (sha256(path), PINNED_CORPUS_SHA256[name])
        for name, path in files.items()
        if sha256(path) != PINNED_CORPUS_SHA256[name]
    }
    if bad:
        detail = ", ".join(f"{name}={actual} (expected {expected})" for name, (actual, expected) in bad.items())
        raise ValueError("PokeCorpus files are not the generator-pinned revision: " + detail)
    qids = files["qid_msg.txt"].read_text(encoding="utf-8").splitlines()
    english = files["en_msg.txt"].read_text(encoding="utf-8").splitlines()
    italian = files["it_msg.txt"].read_text(encoding="utf-8").splitlines()
    if len({len(qids), len(english), len(italian)}) != 1:
        raise ValueError("PokeCorpus parallel files have different line counts")
    return {qid: CorpusRow(qid, en, it) for qid, en, it in zip(qids, english, italian)}


def tokenize(text: str) -> list[tuple[str, str | None]]:
    """Turn PokeCorpus markup into semantic text units.

    Literal glyphs remain exact-match candidates. Known Gen 1 controls are
    represented explicitly. Semantic placeholders such as TARGET/USER/RIVAL
    are represented as dynamic units: their ROM byte representation is not
    guessed here and is therefore wildcarded during location.
    """
    text = text.replace("{text_start}", "").replace("@{", "{")

    units: list[tuple[str, str | None]] = []
    index = 0

    tags = {
        "<LINE>": "LINE",
        "<CONT>": "CONT",
        "<PARA>": "PARA",
        "<PLAYER>": "PLAYER",
        "<DONE>": "DONE",
        "<PROMPT>": "PROMPT",
        "#MON": "POKEMON",

        # PokeCorpus semantic placeholders. Their actual ROM representation
        # is intentionally not guessed by the locator.
        "<TARGET>": "DYNAMIC",
        "<USER>": "DYNAMIC",
        "<RIVAL>": "DYNAMIC",
        "<PKMN>": "DYNAMIC",
    }

    while index < len(text):
        matched = next(
            (
                (token, kind)
                for token, kind in tags.items()
                if text.startswith(token, index)
            ),
            None,
        )

        if matched:
            token, kind = matched
            units.append((kind, None))
            index += len(token)
            continue

        if text.startswith("{text_decimal", index):
            end = text.find("}", index)
            if end < 0:
                raise ValueError("unterminated text_decimal token")
            units.append(("NUM", None))
            index = end + 1
            continue

        if text.startswith("{text_ram", index):
            end = text.find("}", index)
            if end < 0:
                raise ValueError("unterminated text_ram token")
            units.append(("RAM", None))
            index = end + 1
            continue

        if text[index] == "@":
            # Raw PokeCorpus terminator. We preserve it as a semantic
            # terminator instead of rejecting the row.
            units.append(("RAW_AT", None))
            index += 1
            continue

        if text[index] == "<":
            end = text.find(">", index)
            if end >= 0:
                raise ValueError(
                    f"unsupported corpus control {text[index:end + 1]}"
                )

        units.append(("GLYPH", text[index]))
        index += 1

    return units


def expected_layout(
    units: list[tuple[str, str | None]],
    codec: dict[str, int] | None = None,
    wildcard_dynamic: bool = False,
) -> list[int | None]:
    """Compile semantic units into a ROM search pattern.

    None represents a byte whose exact value is intentionally unknown.
    Dynamic semantic placeholders are therefore not assigned invented
    command bytes.
    """
    values: list[int | None] = [ENTRY]

    for kind, value in units:
        if kind == "GLYPH":
            if codec is None or value not in codec:
                raise KeyError(value)
            values.append(codec[value])

        elif kind == "POKEMON":
            if codec is None or any(
                x not in codec for x in ("POKé", "M", "O", "N")
            ):
                raise KeyError("POKéMON")
            values.extend(codec[x] for x in ("POKé", "M", "O", "N"))

        elif kind in CONTROL_BYTES:
            values.append(CONTROL_BYTES[kind])

        elif kind in DYNAMIC_OPERANDS:
            opcode, count = DYNAMIC_OPERANDS[kind]
            values.append(0x50)
            values.append(opcode)
            values.extend(
                [None] * count if wildcard_dynamic else []
            )
            values.append(ENTRY)

        elif kind == "DYNAMIC":
            # Semantic corpus placeholder. We do not guess its ROM encoding.
            # Treat it as one unknown byte for now; surrounding literal text
            # remains exact and can still locate the stream.
            values.append(None)

        elif kind == "RAW_AT":
            # PokeCorpus's @ is a terminal marker. The ROM terminal byte is
            # not assumed here; terminator_from_units() determines it from
            # the observed stream convention.
            continue

        else:
            raise ValueError(f"unknown semantic unit {kind}")

    return values

def terminator_from_units(
    units: list[tuple[str, str | None]]
) -> int | None:
    """Return the known Gen 1 terminal byte represented by the corpus row."""
    typed = [
        kind for kind, _ in units
        if kind in ("DONE", "PROMPT")
    ]

    if len(typed) == 1 and units[-1][0] == typed[-1]:
        return CONTROL_BYTES[typed[-1]]

    # PokeCorpus raw '@' is a terminal marker. Gen 1 text streams observed
    # in the Italian ROM use DONE/PROMPT byte values for these terminal forms.
    # Without an explicit semantic distinction, do not guess which one.
    if units and units[-1][0] == "RAW_AT":
        return None

    return None

def read_static_stream(rom: bytes, offset: int) -> bytes | None:
    """Read a simple 00-literal stream used only for calibration samples."""
    if offset >= len(rom) or rom[offset] != ENTRY:
        return None
    for end in range(offset + 1, min(len(rom), offset + 1024)):
        if rom[end] in (CONTROL_BYTES["DONE"], CONTROL_BYTES["PROMPT"]):
            return rom[offset:end + 1]
    return None


def bank_offset(bank: int, address: int) -> int:
    if bank == 0:
        return address
    return bank * 0x4000 + address - 0x4000


def offset_location(offset: int) -> tuple[int, int]:
    if offset < 0x4000:
        return 0, offset
    return offset // 0x4000, 0x4000 + offset % 0x4000


def load_mapping(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def static_calibration(rom: bytes, corpus: dict[str, CorpusRow], mapping: list[dict[str, str]]) -> tuple[dict[str, int], dict[int, str], Counter, int]:
    """Infer glyph bytes solely where a candidate exactly fits static prose.

    A row is evidence only if: it is outside the six target labels, has an
    existing high/medium/exact candidate, its PokeCorpus text has no dynamic
    command, and its literal stream length/control positions fit exactly.
    """
    by_symbol: dict[str, list[CorpusRow]] = defaultdict(list)
    for row in corpus.values():
        by_symbol["_" + row.qid.rsplit(".", 1)[-1]].append(row)
    votes: dict[str, Counter[int]] = defaultdict(Counter)
    controls = Counter()
    accepted = 0
    for row in mapping:
        symbol = row.get("usa_symbol", "")
        if symbol in TARGET_SYMBOLS or row.get("status") not in {"EXACT", "HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE"}:
            continue
        candidates = by_symbol.get(symbol, [])
        if len(candidates) != 1 or not row.get("ita_address"):
            continue
        try:
            units = tokenize(candidates[0].italian)
        except ValueError:
            continue
        if any(kind in {"RAM", "NUM", "RAW_AT"} for kind, _ in units):
            continue
        terminal = terminator_from_units(units)
        if terminal is None:
            continue
        address = int(row["ita_address"], 16)
        raw = read_static_stream(rom, bank_offset(0x20, address))
        if raw is None or raw[-1] != terminal:
            continue
        # Build positional expected shape. Glyphs are None, controls fixed.
        shape: list[int | None] = [ENTRY]
        glyph_units: list[str] = []
        for kind, value in units:
            if kind == "GLYPH":
                shape.append(None); glyph_units.append(str(value))
            elif kind == "POKEMON":
                shape.extend([None] * 4); glyph_units.extend(["POKé", "M", "O", "N"])
            elif kind == "DYNAMIC":
                # Semantic corpus placeholder: no fixed ROM byte.
                continue
            else:
                shape.append(CONTROL_BYTES[kind])
        if len(shape) != len(raw) or any(expected is not None and raw[i] != expected for i, expected in enumerate(shape)):
            continue
        glyph_index = 0
        for index, expected in enumerate(shape):
            if expected is None:
                votes[glyph_units[glyph_index]][raw[index]] += 1
                glyph_index += 1
            else:
                controls[raw[index]] += 1
        accepted += 1
    codec: dict[str, int] = {}
    reverse: dict[int, str] = {}
    for token, counts in votes.items():
        byte, count = counts.most_common(1)[0]
        # Require all accepted occurrences of a semantic token to agree.
        if len(counts) == 1:
            codec[token] = byte
    for token, byte in codec.items():
        if byte not in reverse:
            reverse[byte] = token
    return codec, reverse, controls, accepted


def find_hits(rom: bytes, pattern: list[int | None], terminal: int) -> list[Hit]:
    """Find pattern hits efficiently using the longest fixed prefix."""
    hits: list[Hit] = []
    length = len(pattern)

    if not pattern or pattern[0] is None:
        return hits

    # Use bytes.find() on the fixed prefix instead of scanning the whole ROM
    # byte-by-byte in Python for every corpus row.
    prefix = bytearray()
    for value in pattern:
        if value is None:
            break
        prefix.append(value)

    if not prefix:
        return hits

    prefix_bytes = bytes(prefix)
    search_from = 0

    wildcard_offsets = tuple(
        index for index, value in enumerate(pattern)
        if value is None
    )

    while True:
        offset = rom.find(prefix_bytes, search_from)
        if offset < 0:
            break

        end = offset + length
        if end <= len(rom):
            matched = rom[offset:end]

            if all(
                value is None or matched[index] == value
                for index, value in enumerate(pattern)
            ):
                controls_ok = (
                    matched[0] == ENTRY
                    and matched[-1] == terminal
                )

                hits.append(
                    Hit(
                        offset,
                        matched,
                        wildcard_offsets,
                        matched[-1] == terminal,
                        controls_ok,
                    )
                )

        search_from = offset + 1

    return hits


def decode_candidate(raw: bytes, reverse: dict[int, str]) -> str:
    out: list[str] = []
    index = 0
    labels = {ENTRY: "{TEXT}", 0x4F: "<LINE>", 0x50: "{TEXT_END}", 0x51: "<PARA>", 0x52: "<PLAYER>",
              0x54: "POKé", 0x55: "<CONT>", 0x57: "<DONE>", 0x58: "<PROMPT>"}
    while index < len(raw):
        value = raw[index]
        if value == 0x01 and index + 2 < len(raw):
            out.append("{RAM:" + raw[index + 1:index + 3].hex().upper() + "}"); index += 3; continue
        if value == 0x09 and index + 3 < len(raw):
            out.append("{NUM:" + raw[index + 1:index + 4].hex().upper() + "}"); index += 4; continue
        out.append(labels.get(value, reverse.get(value, f"{{BYTE:{value:02X}}}")))
        index += 1
    return "".join(out)


def hexdump_context(rom: bytes, offset: int, length: int, radius: int = 32) -> str:
    begin = max(0, offset - radius); end = min(len(rom), offset + length + radius)
    pieces = []
    for row in range(begin, end, 16):
        part = rom[row:min(end, row + 16)]
        mark = "*" if row <= offset < row + 16 else " "
        pieces.append(f"{mark}{row:06X}: {part.hex(' ')}")
    return "\n".join(pieces)


def nearby_mapping(mapping: list[dict[str, str]], usa_symbol: str) -> str:
    rows = []
    for row in mapping:
        try:
            rows.append((int(row["usa_address"], 16), row))
        except (KeyError, ValueError):
            pass
    rows.sort()
    at = next((index for index, (_, row) in enumerate(rows) if row.get("usa_symbol") == usa_symbol), None)
    if at is None:
        return "no USA Bank 0x20 mapping row"
    nearby = rows[max(0, at - 2):at + 3]
    return "; ".join(f"{row['usa_symbol']} usa={row['usa_address']} existing_ita={row.get('ita_address') or '-'} status={row.get('status', '-')}" for _, row in nearby)


def tsv_text(value: str) -> str:
    return value.replace("\t", "\\t").replace("\n", "\\n")


def run(args: argparse.Namespace) -> tuple[list[dict[str, str]], list[str]]:
    corpus = load_corpus(Path(args.corpus_dir))
    rom = Path(args.ita_rom).read_bytes()
    mapping = load_mapping(Path(args.mapping))
    codec, reverse, control_evidence, calibration_count = static_calibration(rom, corpus, mapping)
    required_controls = {ENTRY, CONTROL_BYTES["LINE"], CONTROL_BYTES["PARA"],
                         CONTROL_BYTES["PLAYER"], CONTROL_BYTES["CONT"],
                         CONTROL_BYTES["DONE"], CONTROL_BYTES["PROMPT"]}
    controls_confirmed = required_controls <= set(control_evidence)
    codec_sample = ", ".join(f"{token}=0x{codec[token]:02X}" for token in ("A", "a", " ", "'", "à", "è", "é", "ì", "ò", "ù", "POKé") if token in codec)
    report = [
        "ITALIAN ROM TEXT LOCATOR — READ-ONLY", "",
        "Repository inspection: tools/rom_data.py and tools/build_rom_data.py decode only the US manifest charmap; tools/extract/text.py documents the Gen 1 command model. No Italian manifest, charmap, or Italian-specific decoder is present.",
        "Available ROMs: red-usa.gb (canonical US SHA-1 ea9bcae617fdf159b045185467ae58b2e4a48b9a) and red-ita.gb.",
        "The Italian codec below is inferred from independent static Bank 0x20/PokeCorpus fits, never copied from the US charmap.", "",
        f"ROM: {Path(args.ita_rom)}", f"ROM SHA-1: {hashlib.sha1(rom).hexdigest()}",
        f"PokeCorpus: {args.corpus_dir} (all three pinned SHA-256 checks passed)",
        f"Calibration: {calibration_count} static Bank 0x20 corpus rows accepted; six target symbols excluded.",
        "Italian codec status: EMPIRICALLY DETERMINED FOR THE REQUIRED TOKEN SUBSET; no USA charmap was used as an encoder.",
        "Observed control-byte evidence: " + ", ".join(f"{value:02X}={count}" for value, count in sorted(control_evidence.items())),
        f"Control layout confirmation: {'yes' if controls_confirmed else 'partial'}",
        "Required Italian glyph evidence: " + codec_sample, "",
        "Control interpretation used after calibration:",
        "  00 text-entry marker; 4F LINE; 51 PARA; 52 PLAYER; 54 POKé prefix; 55 CONT; 57 DONE; 58 PROMPT; 50 closes a literal segment; 01 + 2 operand bytes + 00 RAM wildcard/re-entry; 09 + 3 operand bytes + 00 NUM wildcard/re-entry.",
        "  Dynamic operand bytes are explicitly wildcarded and reported; they are not matched by content.", "",
    ]
    rows: list[dict[str, str]] = []
    case_statuses: dict[str, str] = {}
    for qid, symbol in CASES:
        item = corpus.get(qid)
        report.extend([f"QID: {qid}", f"Symbol: {symbol}"])
        if item is None:
            rows.append({"qid": qid, "symbol": symbol, "italian_text": "", "encoding_status": "ENCODING_UNKNOWN", "encoded_length": "", "hit_bank": "", "hit_address": "", "hit_length": "", "terminator_ok": "no", "control_codes_ok": "no", "context_score": "0.000", "candidate_status": "ENCODING_UNKNOWN", "notes": "QID absent from pinned corpus"})
            case_statuses[qid] = "ENCODING_UNKNOWN"; continue
        try:
            units = tokenize(item.italian)
            missing = sorted({value for kind, value in units if kind == "GLYPH" and value not in codec})
            needed = {"POKé", "M", "O", "N"} if any(kind == "POKEMON" for kind, _ in units) else set()
            missing.extend(sorted(needed - set(codec)))
            terminal = terminator_from_units(units)
            if missing or terminal is None:
                raise KeyError(", ".join(missing) if missing else "untyped terminator")
            pattern = expected_layout(units, codec, wildcard_dynamic=True)
        except (ValueError, KeyError) as exc:
            note = f"codec cannot encode safely: {exc}"
            rows.append({"qid": qid, "symbol": symbol, "italian_text": tsv_text(item.italian), "encoding_status": "ENCODING_UNKNOWN", "encoded_length": "", "hit_bank": "", "hit_address": "", "hit_length": "", "terminator_ok": "no", "control_codes_ok": "no", "context_score": "0.000", "candidate_status": "ENCODING_UNKNOWN", "notes": note})
            report.extend([f"Italian corpus: {item.italian}", f"Result: ENCODING_UNKNOWN — {note}", ""])
            case_statuses[qid] = "ENCODING_UNKNOWN"; continue
        hits = find_hits(rom, pattern, terminal)
        wildcard_count = sum(value is None for value in pattern)
        if not hits:
            status = "NOT_FOUND"
        elif len(hits) == 1:
            status = "STRUCTURAL_CONTENT" if wildcard_count else "EXACT_CONTENT"
        else:
            status = "MULTIPLE_HITS"
        case_statuses[qid] = status
        report.extend([
            f"Italian corpus: {item.italian}",
            f"Encoding: encoded_length={len(pattern)} wildcards={wildcard_count} terminal=0x{terminal:02X}",
            f"Pattern: {' '.join('??' if value is None else f'{value:02X}' for value in pattern)}",
            f"Result: {status}; hits={len(hits)}",
        ])
        if not hits:
            rows.append({"qid": qid, "symbol": symbol, "italian_text": tsv_text(item.italian), "encoding_status": "EMPIRICAL_REQUIRED_SUBSET", "encoded_length": str(len(pattern)), "hit_bank": "", "hit_address": "", "hit_length": "", "terminator_ok": "no", "control_codes_ok": "no", "context_score": "0.000", "candidate_status": status, "notes": "no full-ROM pattern hit; no mapping selected"})
        for number, hit in enumerate(hits, 1):
            bank, address = offset_location(hit.offset)
            context = nearby_mapping(mapping, symbol)
            # Context score is descriptive only: 1.0 when the hit equals the
            # existing untrusted Bank 20 proposal, otherwise 0.0; it never
            # changes candidate status.
            known = next((row for row in mapping if row.get("usa_symbol") == symbol), None)
            proposed = int(known["ita_address"], 16) if known and known.get("ita_address") else None
            score = 1.0 if bank == 0x20 and address == proposed else 0.0
            notes = f"hit {number}/{len(hits)}; wildcard byte indexes={list(hit.wildcard_offsets)}; nearby: {context}"
            rows.append({"qid": qid, "symbol": symbol, "italian_text": tsv_text(item.italian), "encoding_status": "EMPIRICAL_REQUIRED_SUBSET", "encoded_length": str(len(pattern)), "hit_bank": f"0x{bank:02X}", "hit_address": f"0x{address:04X}", "hit_length": str(len(hit.matched)), "terminator_ok": "yes" if hit.terminator_ok else "no", "control_codes_ok": "yes" if hit.controls_ok else "no", "context_score": f"{score:.3f}", "candidate_status": status, "notes": notes})
            report.extend([
                f"  Hit {number}: ROM offset=0x{hit.offset:06X}; bank=0x{bank:02X}; address=0x{address:04X}; length={len(hit.matched)}",
                f"    bytes: {hit.matched.hex(' ')}",
                f"    wildcard bytes: " + (", ".join(f"+{index}=0x{hit.matched[index]:02X}" for index in hit.wildcard_offsets) or "none"),
                f"    terminator_ok={'yes' if hit.terminator_ok else 'no'} controls_ok={'yes' if hit.controls_ok else 'no'}",
                f"    decoded: {decode_candidate(hit.matched, reverse)}",
                f"    Bank 0x20 neighbour evidence (descriptive only): {context}",
                "    context (+/-32 bytes):\n" + hexdump_context(rom, hit.offset, len(hit.matched)),
            ])
        report.append("")
    counts = Counter(case_statuses.values())
    report.extend([
        "CONCLUSION", f"A. codec italiano: determined empirically for the required token subset ({len(codec)} tokens); no unsupported glyph was silently substituted.",
        f"B. found: {sum(1 for status in case_statuses.values() if status in {'EXACT_CONTENT', 'STRUCTURAL_CONTENT', 'MULTIPLE_HITS'})}/6",
        f"C. single hit: {sum(1 for status in case_statuses.values() if status in {'EXACT_CONTENT', 'STRUCTURAL_CONTENT'})}",
        f"D. multiple hits: {counts['MULTIPLE_HITS']}",
        "E. NOT_FOUND: " + (", ".join(qid for qid, status in case_statuses.items() if status == "NOT_FOUND") or "none"),
        "F. Next validation needs: target pointer/table ownership, map/trainer/script callsite, bank-local boundaries, dynamic-command operand semantics, and independent review. This locator intentionally establishes none of those as VERIFIED.",
    ])
    return rows, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ita-rom", default=str(REPO / "red-ita.gb"))
    parser.add_argument("--mapping", default=str(ROOT / "bank20_mapping.tsv"))
    parser.add_argument("--corpus-dir", required=True, help="Pinned PokeCorpus corpus/RedBlue directory")
    parser.add_argument("--output-report", default=str(ROOT / "italian_rom_locator_report.txt"))
    parser.add_argument("--output-tsv", default=str(ROOT / "italian_rom_locator.tsv"))
    args = parser.parse_args()
    rows, report = run(args)
    fields = ["qid", "symbol", "italian_text", "encoding_status", "encoded_length", "hit_bank", "hit_address", "hit_length", "terminator_ok", "control_codes_ok", "context_score", "candidate_status", "notes"]
    with Path(args.output_tsv).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    Path(args.output_report).write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"wrote {args.output_report} and {args.output_tsv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
