#!/usr/bin/env python3

"""Regression tests for RAW reference and optimized window matching."""

from __future__ import annotations

import random

from matcher import (
    _find_best_raw_matches_optimized,
    _find_best_raw_matches_reference,
    find_best_matches,
    raw_similarity,
)


def assert_equivalent(source: bytes, target: bytes, limit: int) -> None:
    reference = _find_best_raw_matches_reference(source, target, limit)
    optimized = _find_best_raw_matches_optimized(source, target, limit)
    assert len(optimized) == len(reference)
    for (expected_score, expected_offset), (actual_score, actual_offset) in zip(reference, optimized):
        assert actual_offset == expected_offset
        assert actual_score == expected_score


def test_small_deterministic_inputs() -> None:
    cases = [
        (b"abc", b"abcabc", 10),
        (b"aaa", b"aaaaaa", 10),
        (b"\x00\xff\x00\xff", b"\xff\x00\xff\x00\xff\x00", 3),
        (bytes(range(64)), bytes(range(128)), 20),
        (bytes(range(256)) * 16, bytes(range(256)) * 17, 300),
    ]
    for source, target, limit in cases:
        assert_equivalent(source, target, limit)


def test_random_deterministic_inputs() -> None:
    generator = random.Random(4435)
    for window in (1, 2, 17, 128, 1024):
        source = generator.randbytes(window)
        target = generator.randbytes(window + 257)
        assert_equivalent(source, target, 10)


def test_dispatch_preserves_edge_cases_and_ordering() -> None:
    assert find_best_matches(b"", b"abc", raw_similarity) == []
    assert find_best_matches(b"abcd", b"abc", raw_similarity) == []
    assert find_best_matches(b"a", b"aaaa", raw_similarity, limit=0) == []
    assert find_best_matches(b"a", b"aaaa", raw_similarity, limit=-1) == []
    assert find_best_matches(b"ab", b"abab", raw_similarity, limit=1) == [(1.0, 0)]
    assert find_best_matches(b"ab", b"abab", raw_similarity, limit=10) == [
        (1.0, 0),
        (1.0, 2),
        (0.0, 1),
    ]
    assert find_best_matches([1, 2], [1, 2, 1], raw_similarity, limit=10) == [
        (1.0, 0),
        (0.0, 1),
    ]


if __name__ == "__main__":
    for name, function in sorted(globals().items()):
        if name.startswith("test_"):
            function()
    print("ok")
