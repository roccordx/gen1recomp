from pathlib import Path
import struct
from collections import defaultdict

USA_ROM = Path("red-usa.gb")
ITA_ROM = Path("red-ita.gb")

CASES = {
    "_ExclamationText": {
        "usa": 0x4093,
        "ita": [0x40A4, 0x4364],
    },
    "_MtMoon1FCooltrainerF1EndBattleText": {
        "usa": 0x4778,
        "ita": [0x4835, 0x5E05],
    },
    "_MtMoonB1FUnusedText": {
        "usa": 0x495C,
        "ita": [0x4A2F],
    },
    "_SSAnneBowSailor3EndBattleText": {
        "usa": 0x508E,
        "ita": [0x51DC],
    },
    "_SSAnneCaptainsRoomCaptainHM01NoRoomText": {
        "usa": 0x545D,
        "ita": [0x5606],
    },
    "_SilphCo3FRocketEndBattleText": {
        "usa": 0x671A,
        "ita": [0x6A4B],
    },
    "_SilphCo3FScientistEndBattleText": {
        "usa": 0x6785,
        "ita": [0x6AD4],
    },
    "_SilphCo4FRocket1EndBattleText": {
        "usa": 0x684B,
        "ita": [0x6BBC],
    },
}


def find_ptrs(data, addr):
    raw = struct.pack("<H", addr)
    hits = []
    start = 0

    while True:
        p = data.find(raw, start)
        if p < 0:
            break

        hits.append(p)
        start = p + 1

    return hits


def loc(p):
    if p < 0x4000:
        return (0, p)

    bank = p // 0x4000
    off = 0x4000 + (p % 0x4000)
    return (bank, off)


def locstr(p):
    bank, off = loc(p)
    return f"{bank:02X}:{off:04X}"


def dump(data, p, radius=12):
    a = max(0, p - radius)
    b = min(len(data), p + radius + 2)
    return data[a:b]


def is_pointer_table_context(data, p):
    """
    Heuristic:
    look around the pointer for other little-endian addresses in ROM space.
    Stronger when the surrounding bytes contain repeated:
        20 50 17 <ptr>
    which is the known RBY text-pointer table pattern.
    """
    a = max(0, p - 8)
    b = min(len(data), p + 10)
    chunk = data[a:b]

    score = 0
    reasons = []

    # Exact known pointer-table marker around the pointer.
    if p >= 3 and data[p - 3:p] == bytes([0x20, 0x50, 0x17]):
        score += 100
        reasons.append("preceded_by_20_50_17")

    if p + 5 <= len(data) and data[p + 2:p + 5] == bytes([0x20, 0x50, 0x17]):
        score += 100
        reasons.append("followed_by_20_50_17")

    # Search neighboring words that look like ROM addresses.
    nearby_words = 0

    for q in range(a, b - 1):
        value = data[q] | (data[q + 1] << 8)

        # Bank-20 pointer range.
        if 0x4000 <= value < 0x8000:
            nearby_words += 1

    if nearby_words >= 3:
        score += 30
        reasons.append(f"{nearby_words}_nearby_rom_words")
    elif nearby_words >= 1:
        score += 10
        reasons.append(f"{nearby_words}_nearby_rom_word")

    return score, reasons


def pointer_signature(data, p):
    """
    Capture a normalized local pointer-table signature.
    The target itself is represented as TARGET.
    Other 16-bit words remain as raw values.
    """
    start = max(0, p - 6)
    end = min(len(data), p + 10)

    out = []

    for q in range(start, end - 1, 2):
        value = data[q] | (data[q + 1] << 8)

        if q == p:
            out.append("TARGET")
        else:
            out.append(f"{value:04X}")

    return tuple(out)


def analyze_target(data, addr):
    hits = find_ptrs(data, addr)

    rows = []

    for p in hits:
        score, reasons = is_pointer_table_context(data, p)

        rows.append({
            "pos": p,
            "bank": loc(p)[0],
            "offset": loc(p)[1],
            "score": score,
            "reasons": reasons,
            "signature": pointer_signature(data, p),
        })

    return rows


def best_table_hits(rows):
    return [
        r for r in rows
        if r["score"] >= 100
    ]


usa = USA_ROM.read_bytes()
ita = ITA_ROM.read_bytes()

print("=" * 100)
print("PASS 5.4 — STRUCTURAL POINTER CORRESPONDENCE")
print("=" * 100)

all_results = []

for name, case in CASES.items():

    print()
    print("=" * 100)
    print(name)
    print("=" * 100)

    usa_rows = analyze_target(usa, case["usa"])
    usa_table = best_table_hits(usa_rows)

    print(f"USA target : 20:{case['usa']:04X}")
    print(f"USA refs   : {len(usa_rows)}")
    print(f"USA table  : {len(usa_table)}")

    for r in usa_table:
        print(
            f"  USA {r['bank']:02X}:{r['offset']:04X}"
            f" score={r['score']}"
            f" reasons={','.join(r['reasons'])}"
        )

    for ita_addr in case["ita"]:

        ita_rows = analyze_target(ita, ita_addr)
        ita_table = best_table_hits(ita_rows)

        print()
        print(f"ITA candidate : 20:{ita_addr:04X}")
        print(f"ITA refs      : {len(ita_rows)}")
        print(f"ITA table     : {len(ita_table)}")

        for r in ita_table:
            print(
                f"  ITA {r['bank']:02X}:{r['offset']:04X}"
                f" score={r['score']}"
                f" reasons={','.join(r['reasons'])}"
            )

        # Compare same physical bank/offset of the reference.
        usa_positions = {(r["bank"], r["offset"]) for r in usa_table}
        ita_positions = {(r["bank"], r["offset"]) for r in ita_table}

        same_position = usa_positions & ita_positions

        print(
            f"  SAME reference position(s): "
            f"{', '.join(f'{b:02X}:{o:04X}' for b,o in sorted(same_position)) or 'NONE'}"
        )

        # Compare relative layout around pointer tables.
        structural_matches = 0

        for ur in usa_table:
            for ir in ita_table:

                ub, uo = ur["bank"], ur["offset"]
                ib, io = ir["bank"], ir["offset"]

                # Same bank + nearby position.
                if ub == ib and abs(uo - io) <= 8:
                    structural_matches += 1

        print(f"  NEAR structural matches       : {structural_matches}")

        all_results.append({
            "symbol": name,
            "usa": case["usa"],
            "ita": ita_addr,
            "usa_table": len(usa_table),
            "ita_table": len(ita_table),
            "same_position": len(same_position),
            "near_matches": structural_matches,
        })


print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)

for r in all_results:
    print(
        f"{r['symbol']:<48} "
        f"USA={r['usa_table']:>2} "
        f"ITA={r['ita_table']:>2} "
        f"SAME={r['same_position']:>2} "
        f"NEAR={r['near_matches']:>2} "
        f"candidate=20:{r['ita']:04X}"
    )

print()
print("=" * 100)
print("FINE PASS 5.4")
print("=" * 100)
