#!/usr/bin/env python3

from __future__ import annotations

import argparse

from rom_data import RomImage

ROM_BANK_SIZE = 0x4000


def identical_regions(usa_data: bytes, ita_data: bytes):
    """
    Restituisce una lista di regioni identiche.

    Ogni elemento:
        (inizio, fine)

    dove 'fine' è esclusivo.
    """

    regions = []

    start = None

    for i, (a, b) in enumerate(zip(usa_data, ita_data)):

        if a == b:

            if start is None:
                start = i

        else:

            if start is not None:
                regions.append((start, i))
                start = None

    if start is not None:
        regions.append((start, len(usa_data)))

    return regions


def compare_bank(usa: RomImage, ita: RomImage, bank: int):
    """
    Restituisce:
        uguali, totale, percentuale, dati USA, dati ITA
    """

    start = 0x0000 if bank == 0 else 0x4000

    usa_data = usa.bytes(bank, start, ROM_BANK_SIZE)
    ita_data = ita.bytes(bank, start, ROM_BANK_SIZE)

    equal = sum(a == b for a, b in zip(usa_data, ita_data))
    total = len(usa_data)

    return (
        equal,
        total,
        equal / total * 100,
        usa_data,
        ita_data,
        start,
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)

    args = parser.parse_args()

    usa = RomImage(args.source, expected_sha1=None)
    ita = RomImage(args.target, expected_sha1=None)

    print()
    print("Bank | Equal | Total | Match")
    print("-------------------------------------------")

    for bank in range(0x20):

        (
            equal,
            total,
            percent,
            usa_data,
            ita_data,
            cpu_base,
        ) = compare_bank(usa, ita, bank)

        print(
            f"{bank:02X}   | "
            f"{equal:5d} | "
            f"{total:5d} | "
            f"{percent:6.2f}%"
        )

        regions = identical_regions(usa_data, ita_data)

        for begin, end in regions:

            size = end - begin

            # ignora coincidenze troppo piccole
            if size < 16:
                continue

            cpu_start = cpu_base + begin
            cpu_end = cpu_base + end - 1

            print(
                f"      ${cpu_start:04X}-${cpu_end:04X} "
                f"({size:5d} byte)"
            )

        print()


if __name__ == "__main__":
    main()