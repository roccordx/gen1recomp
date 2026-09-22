#!/usr/bin/env python3

from pathlib import Path
import sys
import re

# Usa direttamente il locator esistente
sys.path.insert(0, str(Path("tools").resolve()))

from italian_rom_locator import (
    load_corpus,
    load_mapping,
    tokenize,
    expected_layout,
    static_calibration,
    bank_offset,
    decode_candidate,
)

SCORING = Path("tools/pass3_ambiguous_analysis.tsv")
ROM_PATH = Path("red-ita.gb")
CORPUS_DIR = Path("/tmp/pokecorpus-pinned/corpus/RedBlue")

OUT_TSV = Path("tools/pass4_content_verification.tsv")
OUT_TXT = Path("tools/pass4_content_verification.txt")

BANK_SIZE = 0x4000
ROM_BASE = 0x4000


def parse_addr(value):
    if ":" not in value:
        return None

    b, a = value.split(":", 1)

    try:
        return int(b, 16), int(a, 16)
    except ValueError:
        return None


def parse_candidate(candidate):
    parsed = parse_addr(candidate)

    if parsed is None:
        return None

    bank, address = parsed

    return bank, address, bank_offset(bank, address)


def exact_match_at(rom, offset, pattern):
    """
    Verifica il pattern generato dal locator esattamente
    all'indirizzo candidato.

    None = wildcard.
    """

    if offset < 0:
        return False

    if offset + len(pattern) > len(rom):
        return False

    for i, expected in enumerate(pattern):

        if expected is None:
            continue

        if rom[offset + i] != expected:
            return False

    return True


def describe_pattern(pattern):
    fixed = sum(x is not None for x in pattern)
    wildcards = len(pattern) - fixed

    return len(pattern), fixed, wildcards


def find_qid_for_symbol(corpus, symbol):
    """
    Cerca il QID usando il tail del QID, come già fa
    la calibrazione del locator.
    """

    matches = []

    for qid, row in corpus.items():

        tail = qid.split(".")[-1]

        if tail == symbol.lstrip("_"):
            matches.append((qid, row))

    if len(matches) == 1:
        return matches[0]

    return None


# ============================================================
# INPUT
# ============================================================

if not SCORING.exists():
    raise SystemExit(
        f"File non trovato: {SCORING}"
    )

if not ROM_PATH.exists():
    raise SystemExit(
        f"ROM non trovata: {ROM_PATH}"
    )

if not CORPUS_DIR.exists():
    raise SystemExit(
        f"Corpus non trovato: {CORPUS_DIR}"
    )


rom = ROM_PATH.read_bytes()

print("Caricamento PokéCorpus...")
corpus = load_corpus(CORPUS_DIR)

print(f"Righe corpus: {len(corpus)}")

# La stessa mapping usata dal locator.
mapping = load_mapping(Path("tools/bank20_mapping.tsv"))

print(f"Righe mapping: {len(mapping)}")

codec, reverse, control_evidence, calibration_count = static_calibration(
    rom,
    corpus,
    mapping,
)

print(f"Codec calibrato: {len(codec)} token")
print(f"Righe calibrazione accettate: {calibration_count}")


# ============================================================
# CARICA CANDIDATI
# ============================================================

rows = []

with SCORING.open(encoding="utf-8") as f:

    header = f.readline().rstrip("\n").split("\t")
    columns = {name: i for i, name in enumerate(header)}

    required = {
        "symbol",
        "usa",
        "candidate",
        "structural_score",
        "rom_score",
        "total_score",
    }

    missing = required - columns.keys()

    if missing:
        raise RuntimeError(
            f"Formato SCORING inatteso; colonne mancanti: {sorted(missing)}"
        )

    for line in f:

        parts = line.rstrip("\n").split("\t")

        if len(parts) < len(header):
            continue

        rows.append({
            "symbol": parts[columns["symbol"]],
            "usa": parts[columns["usa"]],
            "candidate": parts[columns["candidate"]],
            "structural_score": int(parts[columns["structural_score"]]),
            "rom_score": int(parts[columns["rom_score"]]),
            "total_score": int(parts[columns["total_score"]]),
            "structural_best": parts[columns["classification"]]
                if "classification" in columns
                else "",
            "reasons": parts[columns["structural_reasons"]]
                if "structural_reasons" in columns
                else "",
        })


# ============================================================
# VERIFICA CONTENUTO
# ============================================================

results = []

for row in rows:

    symbol = row["symbol"]

    corpus_match = find_qid_for_symbol(
        corpus,
        symbol,
    )

    if corpus_match is None:

        row.update({
            "qid": "",
            "italian_text": "",
            "pattern_len": 0,
            "fixed_bytes": 0,
            "wildcards": 0,
            "content_match": "NO_CORPUS",
            "content_score": 0,
            "classification": "NO_CORPUS",
        })

        results.append(row)
        continue


    qid, corpus_row = corpus_match

    italian_text = corpus_row.italian

    # --------------------------------------------------------
    # Usa ESATTAMENTE il tokenizer del locator.
    # --------------------------------------------------------

    try:
        units = tokenize(italian_text)

        pattern = expected_layout(units, codec)

    except Exception as exc:

        row.update({
            "qid": qid,
            "italian_text": italian_text,
            "pattern_len": 0,
            "fixed_bytes": 0,
            "wildcards": 0,
            "content_match": f"ENCODING_ERROR:{exc}",
            "content_score": 0,
            "classification": "ENCODING_ERROR",
        })

        results.append(row)
        continue


    pattern_len, fixed_bytes, wildcards = describe_pattern(pattern)

    candidate = parse_candidate(row["candidate"])

    if candidate is None:

        row.update({
            "qid": qid,
            "italian_text": italian_text,
            "pattern_len": pattern_len,
            "fixed_bytes": fixed_bytes,
            "wildcards": wildcards,
            "content_match": "INVALID_ADDRESS",
            "content_score": 0,
            "classification": "REJECTED",
        })

        results.append(row)
        continue


    bank, address, offset = candidate

    # --------------------------------------------------------
    # Verifica esatta del contenuto.
    # --------------------------------------------------------

    match = exact_match_at(
        rom,
        offset,
        pattern,
    )

    # --------------------------------------------------------
    # Se il match è negativo, controlliamo anche cosa c'è
    # realmente all'indirizzo.
    # --------------------------------------------------------

    actual = rom[
        offset:
        min(offset + max(pattern_len, 32), len(rom))
    ]

    actual_hex = actual[:32].hex(" ")

    if match:

        content_score = 100

        classification = "CONTENT_CONFIRMED"

    else:

        content_score = 0

        classification = "CONTENT_REJECTED"


    row.update({
        "qid": qid,
        "italian_text": italian_text,
        "pattern_len": pattern_len,
        "fixed_bytes": fixed_bytes,
        "wildcards": wildcards,
        "content_match": "YES" if match else "NO",
        "content_score": content_score,
        "classification": classification,
        "actual_hex": actual_hex,
    })

    results.append(row)


# ============================================================
# TSV
# ============================================================

with OUT_TSV.open("w", encoding="utf-8") as f:

    f.write(
        "symbol\tusa\tcandidate\tstructural_score\t"
        "rom_score\ttotal_score\tqid\t"
        "pattern_len\tfixed_bytes\twildcards\t"
        "content_match\tcontent_score\tclassification\t"
        "italian_text\tactual_hex\n"
    )

    for row in results:

        f.write(
            f"{row['symbol']}\t"
            f"{row['usa']}\t"
            f"{row['candidate']}\t"
            f"{row['structural_score']}\t"
            f"{row['rom_score']}\t"
            f"{row['total_score']}\t"
            f"{row.get('qid','')}\t"
            f"{row.get('pattern_len',0)}\t"
            f"{row.get('fixed_bytes',0)}\t"
            f"{row.get('wildcards',0)}\t"
            f"{row.get('content_match','')}\t"
            f"{row.get('content_score',0)}\t"
            f"{row.get('classification','')}\t"
            f"{row.get('italian_text','')}\t"
            f"{row.get('actual_hex','')}\n"
        )


# ============================================================
# REPORT
# ============================================================

with OUT_TXT.open("w", encoding="utf-8") as f:

    f.write(
        "PASS 4 - CONTENT VERIFICATION\n"
    )
    f.write(
        "=" * 110 + "\n\n"
    )

    grouped = {}

    for row in results:
        grouped.setdefault(
            row["symbol"],
            []
        ).append(row)

    for symbol, candidates in grouped.items():

        f.write(
            f"{symbol}\n"
        )
        f.write(
            "-" * 110 + "\n"
        )

        for row in candidates:

            f.write(
                f"  {row['candidate']} "
                f"struct={row['structural_score']} "
                f"rom={row['rom_score']} "
                f"content={row.get('content_score',0)} "
                f"=> {row.get('classification','')}\n"
            )

            if row.get("qid"):
                f.write(
                    f"      QID: {row['qid']}\n"
                )

            if row.get("italian_text"):
                f.write(
                    f"      IT: {row['italian_text']}\n"
                )

            f.write(
                f"      pattern: "
                f"{row.get('pattern_len',0)} bytes, "
                f"{row.get('fixed_bytes',0)} fixed, "
                f"{row.get('wildcards',0)} wildcards\n"
            )

            if row.get("actual_hex"):
                f.write(
                    f"      ROM: {row['actual_hex']}\n"
                )

        f.write("\n")


# ============================================================
# STATISTICHE
# ============================================================

confirmed = [
    r for r in results
    if r.get("classification") == "CONTENT_CONFIRMED"
]

rejected = [
    r for r in results
    if r.get("classification") == "CONTENT_REJECTED"
]

no_corpus = [
    r for r in results
    if r.get("classification") == "NO_CORPUS"
]

errors = [
    r for r in results
    if r.get("classification") == "ENCODING_ERROR"
]


# Per simbolo: quanti candidati hanno match del contenuto?
by_symbol = {}

for row in results:
    by_symbol.setdefault(
        row["symbol"],
        []
    ).append(row)

unique_content = {}
multiple_content = {}

for symbol, candidates in by_symbol.items():

    matches = [
        r for r in candidates
        if r.get("classification") == "CONTENT_CONFIRMED"
    ]

    if len(matches) == 1:
        unique_content[symbol] = matches[0]

    elif len(matches) > 1:
        multiple_content[symbol] = matches


print()
print("=" * 110)
print("PASS 4 - CONTENT VERIFICATION")
print("=" * 110)

print(
    f"Candidati analizzati              : {len(results)}"
)

print(
    f"Match contenuto                   : {len(confirmed)}"
)

print(
    f"Match contenuto unico per simbolo : {len(unique_content)}"
)

print(
    f"Più match per simbolo             : {len(multiple_content)}"
)

print(
    f"Rifiutati                         : {len(rejected)}"
)

print(
    f"Senza corpus                      : {len(no_corpus)}"
)

print(
    f"Errori encoding                   : {len(errors)}"
)

print()
print(
    f"Output TSV: {OUT_TSV}"
)

print(
    f"Output TXT: {OUT_TXT}"
)

print()
print("CONTENT CONFIRMED - MATCH UNICO")
print("-" * 110)

for symbol in sorted(unique_content):

    row = unique_content[symbol]

    print(
        f"{symbol:<60} "
        f"-> {row['candidate']} "
        f"QID={row['qid']}"
    )

print()
print("MULTIPLE CONTENT MATCHES")
print("-" * 110)

for symbol in sorted(multiple_content):

    candidates = multiple_content[symbol]

    print(
        f"{symbol:<60} "
        + ", ".join(
            r["candidate"]
            for r in candidates
        )
    )

print()
print("PASS 4 completato.")
print("NESSUN mapping è stato modificato.")
