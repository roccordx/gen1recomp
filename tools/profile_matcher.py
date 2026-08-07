import json
import time

import matcher as matcher_module
from analyzer import RomAnalyzer
from rom_data import RomImage, SymbolTable
from symbol_database import SymbolDatabase


class MatcherProfiler:

    def __init__(self):
        self.symbols_processed = 0
        self.total_window_bytes = 0
        self.candidate_windows = 0
        self.total_bytes_compared = 0
        self.raw_similarity_calls = 0
        self.raw_similarity_time = 0.0
        self.slice_creation_time = 0.0
        self.candidate_list_time = 0.0
        self.sorting_time = 0.0
        self.matcher_time = 0.0

    def record_raw_similarity(self, elapsed, size):
        self.raw_similarity_calls += 1
        self.total_bytes_compared += size
        self.raw_similarity_time += elapsed

    def record_slice_creation(self, elapsed):
        self.slice_creation_time += elapsed

    def record_window(self, window):
        self.symbols_processed += 1
        self.total_window_bytes += window

    def record_candidate_windows(self, count):
        self.candidate_windows += count

    def record_candidate_list(self, elapsed):
        self.candidate_list_time += elapsed

    def record_sorting(self, elapsed):
        self.sorting_time += elapsed

    def record_matcher(self, elapsed):
        self.matcher_time += elapsed


def average(total, count):
    if count:
        return total / count
    return 0.0


def timing(value):
    return f"{value:.2f} s"


def main():
    with open("tools/rom_manifest.json", encoding="utf8") as f:
        manifest = json.load(f)

    symbols = SymbolTable(manifest["symbols"])
    database = SymbolDatabase(manifest["symbols"])
    usa = RomImage("red-usa.gb", expected_sha1=None)
    ita = RomImage("red-ita.gb", expected_sha1=None)

    profiler = MatcherProfiler()
    original_matcher = matcher_module.SymbolMatcher.find
    original_raw = matcher_module.MATCHERS["raw"]

    def profiled_raw(source, candidate):
        start = time.perf_counter()
        try:
            return original_raw(source, candidate)
        finally:
            profiler.record_raw_similarity(
                time.perf_counter() - start,
                len(source),
            )

    def profiled_find(self, *args, **kwargs):
        start = time.perf_counter()
        result = original_matcher(self, *args, **kwargs)
        profiler.record_window(result.window)
        profiler.record_matcher(time.perf_counter() - start)
        return result

    matcher_module.MATCHERS["raw"] = profiled_raw
    matcher_module.SymbolMatcher.find = profiled_find
    matcher_module._profiler = profiler

    try:
        RomAnalyzer(usa, ita, symbols, database).scan_rom()
    finally:
        matcher_module.MATCHERS["raw"] = original_raw
        matcher_module.SymbolMatcher.find = original_matcher
        matcher_module._profiler = None

    average_window = average(
        profiler.total_window_bytes,
        profiler.symbols_processed,
    )
    average_candidates = average(
        profiler.candidate_windows,
        profiler.symbols_processed,
    )
    raw_average = average(
        profiler.raw_similarity_time,
        profiler.raw_similarity_calls,
    )
    other_time = max(
        0.0,
        profiler.matcher_time
        - profiler.candidate_list_time
        - profiler.sorting_time,
    )

    print("------------------------------------------------------------")
    print("Matcher profiling")
    print("------------------------------------------------------------")
    print()
    print(f"Symbols processed..............{profiler.symbols_processed:,}")
    print(f"Average window.................{average_window:.0f} bytes")
    print(f"Average candidate windows......{average_candidates:.0f}")
    print(f"Total bytes compared...........{profiler.total_bytes_compared:,}")
    print()
    print("raw_similarity()")
    print()
    print(f"Calls.........................{profiler.raw_similarity_calls:,}")
    print(f"Time..........................{timing(profiler.raw_similarity_time)}")
    print(f"Average.......................{raw_average * 1000000:.1f} µs")
    print()
    print("------------------------------------------------------------")
    print("Slice creation")
    print()
    print(f"Time..........................{timing(profiler.slice_creation_time)}")
    print()

    print("------------------------------------------------------------")
    print("Candidate list")

    print(f"Time..........................{timing(profiler.candidate_list_time)}")

    print("------------------------------------------------------------")
    print("Sorting")

    print(f"Time..........................{timing(profiler.sorting_time)}")

    print("------------------------------------------------------------")
    print("Other")

    print(f"Time..........................{timing(other_time)}")

    print("------------------------------------------------------------")
    print("TOTAL")

    print(f"Matcher.......................{timing(profiler.matcher_time)}")


if __name__ == "__main__":
    main()
