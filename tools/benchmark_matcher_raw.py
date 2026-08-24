#!/usr/bin/env python3

"""Repeatable, ROM-free benchmark for the RAW matcher fast path."""

from __future__ import annotations

import random
import time

from matcher import _find_best_raw_matches, _find_best_raw_matches_reference

WINDOW = 128
TARGET_SIZE = 0x4000
ITERATIONS = 20


def measure(function, source: bytes, target: bytes) -> float:
    start = time.perf_counter()
    for _ in range(ITERATIONS):
        function(source, target, 10)
    return (time.perf_counter() - start) / ITERATIONS


def main() -> int:
    source = random.Random(4435).randbytes(WINDOW)
    target = random.Random(60).randbytes(TARGET_SIZE)

    assert _find_best_raw_matches(source, target, 10) == (
        _find_best_raw_matches_reference(source, target, 10)
    )
    reference = measure(_find_best_raw_matches_reference, source, target)
    optimized = measure(_find_best_raw_matches, source, target)
    speedup = reference / optimized

    print(f"sample: window={WINDOW}, target={TARGET_SIZE}, iterations={ITERATIONS}")
    print(f"reference: {reference:.6f} s/run")
    print(f"optimized: {optimized:.6f} s/run")
    print(f"speedup: {speedup:.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
