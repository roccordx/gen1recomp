#!/usr/bin/env python3

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


BANK_SIZE = 0x4000
ROM_SIZE = 0x100000


@dataclass
class HeaderCandidate:
    bank: int
    address: int
    score: int
    block_pointer: int
    raw: bytes

    @property
    def label(self) -> str:
        return f"{self.bank:02X}:{self.address:04X}"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def cpu_to_offset(bank: int, address: int) -> int:
    if bank == 0:
        return address

    if not 0x4000 <= address < 0x8000:
        raise ValueError(
            f"invalid banked address {bank:02X}:{address:04X}"
        )

    return bank * BANK_SIZE + (address - BANK_SIZE)


def offset_to_cpu(offset: int) -> tuple[int, int]:
    bank = offset // BANK_SIZE

    if bank == 0:
        return 0, offset

    address = BANK_SIZE + (offset % BANK_SIZE)
    return bank, address


def read_header(rom: bytes, bank: int, address: int) -> bytes:
    offset = cpu_to_offset(bank, address)
    return rom[offset : offset + 10]


def header_signature(header: bytes) -> tuple[int, int, int]:
    """
    Map header:

        +0 = tileset
        +1 = height
        +2 = width
    """
    return header[0], header[1], header[2]


def valid_dimensions(height: int, width: int) -> bool:
    return (
        1 <= height <= 0x40
        and 1 <= width <= 0x40
    )


def valid_block_pointer(pointer: int) -> bool:
    return 0x4000 <= pointer < 0x8000


def find_candidates(
    rom: bytes,
    tileset: int,
    height: int,
    width: int,
) -> list[HeaderCandidate]:

    candidates: list[HeaderCandidate] = []

    if not valid_dimensions(height, width):
        return candidates

    for bank in range(1, len(rom) // BANK_SIZE):
        bank_offset = bank * BANK_SIZE

        # Header needs at least 5 bytes.
        for rel in range(0, BANK_SIZE - 5):
            offset = bank_offset + rel

            if (
                rom[offset] != tileset
                or rom[offset + 1] != height
                or rom[offset + 2] != width
            ):
                continue

            block_pointer = rom[offset + 3] | (rom[offset + 4] << 8)

            score = 0

            # Strong evidence: valid banked block pointer.
            if valid_block_pointer(block_pointer):
                score += 3

            # Connection/header bytes should be structurally plausible.
            #
            # The extractor reads:
            #   +9 = connection flags
            #
            # We don't require a specific value, but values outside
            # the known low flag range are suspicious.
            connection_flags = rom[offset + 9]

            if connection_flags & ~0x0F == 0:
                score += 2

            candidates.append(
                HeaderCandidate(
                    bank=bank,
                    address=BANK_SIZE + rel,
                    score=score,
                    block_pointer=block_pointer,
                    raw=rom[offset : offset + 10],
                )
            )

    candidates.sort(
        key=lambda c: (
            -c.score,
            c.bank,
            c.address,
        )
    )

    return candidates


def load_map_headers(manifest: dict) -> list[tuple[str, tuple[int, int]]]:
    symbols = manifest["symbols"]

    result = []

    for name, value in symbols.items():
        if not name.endswith("_h"):
            continue

        if not isinstance(value, list) or len(value) != 2:
            continue

        result.append((name, (value[0], value[1])))

    result.sort(
        key=lambda item: (
            item[1][0],
            item[1][1],
            item[0],
        )
    )

    return result


def confidence(score: int, rank: int, total: int) -> str:
    if total == 1 and score >= 5:
        return "HIGH"

    if total <= 3 and rank == 0 and score >= 5:
        return "MEDIUM"

    if rank == 0 and score >= 5:
        return "AMBIGUOUS"

    if total == 1 and score >= 3:
        return "MEDIUM"

    return "AMBIGUOUS"


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    usa_rom_path = root / "red-usa.gb"
    ita_rom_path = root / "red-ita.gb"

    usa_manifest_path = root / "tools" / "rom_manifest.json"
    ita_manifest_path = (
        root / "tools" / "rom_variants" / "red_ita_manifest.json"
    )

    output_path = (
        root / "tools" / "italian_map_header_candidates.tsv"
    )

    all_candidates_path = (
        root / "tools" / "italian_map_header_all_candidates.tsv"
    )

    report_path = (
        root / "tools" / "italian_map_header_report.txt"
    )

    for path in (
        usa_rom_path,
        ita_rom_path,
        usa_manifest_path,
        ita_manifest_path,
    ):
        if not path.exists():
            raise SystemExit(f"Missing required file: {path}")

    usa_rom = usa_rom_path.read_bytes()
    ita_rom = ita_rom_path.read_bytes()

    if len(usa_rom) != ROM_SIZE:
        raise SystemExit(
            f"Unexpected USA ROM size: {len(usa_rom)}"
        )

    if len(ita_rom) != ROM_SIZE:
        raise SystemExit(
            f"Unexpected ITA ROM size: {len(ita_rom)}"
        )

    usa_manifest = load_json(usa_manifest_path)
    ita_manifest = load_json(ita_manifest_path)

    usa_headers = load_map_headers(usa_manifest)
    ita_symbols = ita_manifest["symbols"]

    rows = []
    report = []

    report.append("Italian Map Header Locator")
    report.append("=" * 80)
    report.append("")
    report.append(f"USA map headers: {len(usa_headers)}")
    report.append("")

    for index, (symbol, usa_location) in enumerate(usa_headers, 1):
        usa_bank, usa_address = usa_location

        usa_header = read_header(
            usa_rom,
            usa_bank,
            usa_address,
        )

        tileset, height, width = header_signature(usa_header)

        candidates = find_candidates(
            ita_rom,
            tileset,
            height,
            width,
        )

        # If the Italian manifest already has this symbol,
        # show its current location and evaluate it too.
        manifest_location = ita_symbols.get(symbol)

        manifest_candidate = None

        if (
            isinstance(manifest_location, list)
            and len(manifest_location) == 2
        ):
            mb, ma = manifest_location

            try:
                mh = read_header(
                    ita_rom,
                    mb,
                    ma,
                )

                if header_signature(mh) == (
                    tileset,
                    height,
                    width,
                ):
                    manifest_candidate = (
                        mb,
                        ma,
                        mh,
                    )
            except Exception:
                pass

        # Put the current manifest candidate first if it matches.
        if manifest_candidate:
            mb, ma, mh = manifest_candidate

            candidates = [
                HeaderCandidate(
                    bank=mb,
                    address=ma,
                    score=5,
                    block_pointer=(
                        mh[3] | (mh[4] << 8)
                    ),
                    raw=mh,
                )
            ] + [
                c
                for c in candidates
                if not (
                    c.bank == mb
                    and c.address == ma
                )
            ]

        total = len(candidates)

        if total:
            best = candidates[0]
            conf = confidence(
                best.score,
                0,
                total,
            )

            delta = (
                best.address - usa_address
            )

            if best.bank != usa_bank:
                delta_text = "BANK_CHANGE"
            else:
                delta_text = f"{delta:+d}"

            status = "CANDIDATE"

            if (
                best.bank == usa_bank
                and best.address == usa_address
            ):
                status = "UNCHANGED"

            rows.append(
                [
                    symbol,
                    f"{usa_bank:02X}:{usa_address:04X}",
                    best.label,
                    delta_text,
                    f"{tileset:02X}",
                    f"{height:02X}",
                    f"{width:02X}",
                    str(best.score),
                    str(total),
                    conf,
                    status,
                ]
            )

            report.append(
                f"{symbol}"
            )
            report.append(
                f"  USA       : "
                f"{usa_bank:02X}:{usa_address:04X}"
            )
            report.append(
                f"  Signature : "
                f"tileset={tileset:02X} "
                f"height={height:02X} "
                f"width={width:02X}"
            )
            report.append(
                f"  Best ITA  : "
                f"{best.label}"
            )
            report.append(
                f"  Candidates: {total}"
            )
            report.append(
                f"  Score     : {best.score}"
            )
            report.append(
                f"  Confidence: {conf}"
            )
            report.append("")

        else:
            rows.append(
                [
                    symbol,
                    f"{usa_bank:02X}:{usa_address:04X}",
                    "",
                    "",
                    f"{tileset:02X}",
                    f"{height:02X}",
                    f"{width:02X}",
                    "",
                    "0",
                    "NOT_FOUND",
                    "NOT_FOUND",
                ]
            )

            report.append(
                f"{symbol}"
            )
            report.append(
                f"  USA       : "
                f"{usa_bank:02X}:{usa_address:04X}"
            )
            report.append(
                f"  Signature : "
                f"tileset={tileset:02X} "
                f"height={height:02X} "
                f"width={width:02X}"
            )
            report.append(
                "  ITA       : NOT FOUND"
            )
            report.append("")

    header = [
        "symbol",
        "usa",
        "ita_candidate",
        "delta",
        "tileset",
        "height",
        "width",
        "score",
        "candidate_count",
        "confidence",
        "status",
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        f.write("\t".join(header) + "\n")

        for row in rows:
            f.write(
                "\t".join(row) + "\n"
            )

    # Full candidate list for the global alignment solver.
    all_header = [
        "symbol",
        "usa",
        "ita_candidate",
        "score",
        "block_pointer",
        "source",
    ]

    with all_candidates_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        f.write("\t".join(all_header) + "\n")

        for symbol, usa_location in usa_headers:
            usa_bank, usa_address = usa_location

            usa_header = read_header(
                usa_rom,
                usa_bank,
                usa_address,
            )

            tileset, height, width = header_signature(
                usa_header
            )

            candidates = find_candidates(
                ita_rom,
                tileset,
                height,
                width,
            )

            manifest_location = ita_symbols.get(symbol)

            manifest_candidate = None

            if (
                isinstance(manifest_location, list)
                and len(manifest_location) == 2
            ):
                mb, ma = manifest_location

                try:
                    mh = read_header(
                        ita_rom,
                        mb,
                        ma,
                    )

                    if header_signature(mh) == (
                        tileset,
                        height,
                        width,
                    ):
                        manifest_candidate = (
                            mb,
                            ma,
                            mh,
                        )
                except Exception:
                    pass

            manifest_key = None

            if manifest_candidate:
                mb, ma, mh = manifest_candidate
                manifest_key = (mb, ma)

                candidates = [
                    HeaderCandidate(
                        bank=mb,
                        address=ma,
                        score=5,
                        block_pointer=(
                            mh[3] | (mh[4] << 8)
                        ),
                        raw=mh,
                    )
                ] + [
                    c
                    for c in candidates
                    if not (
                        c.bank == mb
                        and c.address == ma
                    )
                ]

            for candidate in candidates:
                candidate_key = (
                    candidate.bank,
                    candidate.address,
                )

                if manifest_key == candidate_key:
                    source = "MANIFEST+SEARCH"
                else:
                    source = "SEARCH"

                f.write(
                    "\t".join(
                        [
                            symbol,
                            f"{usa_bank:02X}:{usa_address:04X}",
                            candidate.label,
                            str(candidate.score),
                            f"{candidate.block_pointer:04X}",
                            source,
                        ]
                    )
                    + "\n"
                )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        f.write("\n".join(report))
        f.write("\n")

    print()
    print("Italian map header locator")
    print("=" * 60)
    print(f"USA map headers : {len(usa_headers)}")
    print(f"Output TSV      : {output_path}")
    print(f"All candidates  : {all_candidates_path}")
    print(f"Output report   : {report_path}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()