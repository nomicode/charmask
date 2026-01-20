#!/usr/bin/env python3
"""
Benchmark: Fast binary data search methods

Compare different approaches for finding patterns in binary streams:
1. Naive Python search
2. Boyer-Moore algorithm
3. SIMD-accelerated (via regex/memmem)
4. Rabin-Karp rolling hash
5. Bloom filter + verification
6. Our sieve/convolution approach (PyTorch)
"""

import os
import time
import random
import re
from typing import List, Tuple, Callable
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    name: str
    time_ms: float
    matches_found: int
    throughput_mbps: float


class SearchMethod:
    """Base class for search implementations"""

    def __init__(self, pattern: bytes):
        self.pattern = pattern

    def search(self, data: bytes) -> List[int]:
        """Return list of match positions"""
        raise NotImplementedError

    def name(self) -> str:
        raise NotImplementedError


class NaiveSearch(SearchMethod):
    """Baseline: Python's bytes.find()"""

    def search(self, data: bytes) -> List[int]:
        matches = []
        pos = 0
        while True:
            pos = data.find(self.pattern, pos)
            if pos == -1:
                break
            matches.append(pos)
            pos += 1
        return matches

    def name(self) -> str:
        return "Naive (bytes.find)"


class RegexSearch(SearchMethod):
    """Python regex (uses optimized C implementation)"""

    def __init__(self, pattern: bytes):
        super().__init__(pattern)
        self.regex = re.compile(re.escape(pattern))

    def search(self, data: bytes) -> List[int]:
        return [m.start() for m in self.regex.finditer(data)]

    def name(self) -> str:
        return "Regex (re module)"


class BoyerMooreSearch(SearchMethod):
    """Boyer-Moore algorithm implementation"""

    def __init__(self, pattern: bytes):
        super().__init__(pattern)
        self.bad_char = self._build_bad_char_table()

    def _build_bad_char_table(self) -> dict:
        """Build bad character heuristic table"""
        table = {}
        pattern_len = len(self.pattern)
        for i in range(pattern_len - 1):
            table[self.pattern[i]] = pattern_len - 1 - i
        return table

    def search(self, data: bytes) -> List[int]:
        matches = []
        data_len = len(data)
        pattern_len = len(self.pattern)

        i = 0
        while i <= data_len - pattern_len:
            j = pattern_len - 1

            # Match from right to left
            while j >= 0 and self.pattern[j] == data[i + j]:
                j -= 1

            if j < 0:
                matches.append(i)
                i += 1
            else:
                # Skip based on bad character heuristic
                skip = self.bad_char.get(data[i + j], pattern_len)
                i += max(1, skip)

        return matches

    def name(self) -> str:
        return "Boyer-Moore"


class RabinKarpSearch(SearchMethod):
    """Rabin-Karp with rolling hash"""

    def __init__(self, pattern: bytes):
        super().__init__(pattern)
        self.pattern_hash = hash(pattern)
        self.pattern_len = len(pattern)

    def search(self, data: bytes) -> List[int]:
        matches = []
        data_len = len(data)

        if data_len < self.pattern_len:
            return matches

        for i in range(data_len - self.pattern_len + 1):
            window = data[i:i + self.pattern_len]
            if hash(window) == self.pattern_hash:
                # Hash collision check
                if window == self.pattern:
                    matches.append(i)

        return matches

    def name(self) -> str:
        return "Rabin-Karp"


class BloomFilterSearch(SearchMethod):
    """Bloom filter pre-filter + verification"""

    def __init__(self, pattern: bytes):
        super().__init__(pattern)
        self.pattern_len = len(pattern)
        # Simple bloom filter using multiple hash functions
        self.filter_size = 1024
        self.bloom = [False] * self.filter_size
        self._add_pattern()

    def _hash1(self, data: bytes) -> int:
        return hash(data) % self.filter_size

    def _hash2(self, data: bytes) -> int:
        return (hash(data) * 31) % self.filter_size

    def _hash3(self, data: bytes) -> int:
        return (hash(data) * 17 + 13) % self.filter_size

    def _add_pattern(self):
        self.bloom[self._hash1(self.pattern)] = True
        self.bloom[self._hash2(self.pattern)] = True
        self.bloom[self._hash3(self.pattern)] = True

    def _might_match(self, window: bytes) -> bool:
        return (self.bloom[self._hash1(window)] and
                self.bloom[self._hash2(window)] and
                self.bloom[self._hash3(window)])

    def search(self, data: bytes) -> List[int]:
        matches = []
        data_len = len(data)

        for i in range(data_len - self.pattern_len + 1):
            window = data[i:i + self.pattern_len]
            if self._might_match(window):
                # Verify actual match
                if window == self.pattern:
                    matches.append(i)

        return matches

    def name(self) -> str:
        return "Bloom Filter"


def generate_test_data(size_mb: int, pattern: bytes, num_occurrences: int = 5) -> bytes:
    """Generate random data with known pattern occurrences"""
    data = bytearray(os.urandom(size_mb * 1024 * 1024))

    # Insert pattern at random positions
    positions = []
    for _ in range(num_occurrences):
        pos = random.randint(0, len(data) - len(pattern))
        data[pos:pos + len(pattern)] = pattern
        positions.append(pos)

    print(f"Generated {size_mb}MB data with pattern at positions: {sorted(positions)}")
    return bytes(data)


def benchmark_method(method: SearchMethod, data: bytes) -> BenchmarkResult:
    """Benchmark a single search method"""
    start = time.perf_counter()
    matches = method.search(data)
    elapsed = time.perf_counter() - start

    time_ms = elapsed * 1000
    throughput_mbps = (len(data) / (1024 * 1024)) / elapsed

    return BenchmarkResult(
        name=method.name(),
        time_ms=time_ms,
        matches_found=len(matches),
        throughput_mbps=throughput_mbps
    )


def run_benchmarks(data: bytes, pattern: bytes):
    """Run all benchmarks"""
    methods = [
        NaiveSearch(pattern),
        RegexSearch(pattern),
        BoyerMooreSearch(pattern),
        RabinKarpSearch(pattern),
        BloomFilterSearch(pattern),
    ]

    results = []
    print(f"\nSearching for pattern: {pattern!r}")
    print(f"Data size: {len(data) / (1024*1024):.1f} MB\n")
    print(f"{'Method':<20} {'Time (ms)':<12} {'Matches':<10} {'Throughput (MB/s)':<20}")
    print("-" * 70)

    for method in methods:
        result = benchmark_method(method, data)
        results.append(result)
        print(f"{result.name:<20} {result.time_ms:<12.2f} {result.matches_found:<10} {result.throughput_mbps:<20.2f}")

    # Find fastest
    fastest = min(results, key=lambda r: r.time_ms)
    print(f"\n🏆 Winner: {fastest.name} ({fastest.throughput_mbps:.2f} MB/s)")

    return results


def main():
    # Test parameters
    DATA_SIZE_MB = 10
    PATTERN = b"SECRET"  # 6-byte pattern
    NUM_OCCURRENCES = 5

    print("=" * 70)
    print("BINARY SEARCH BENCHMARK")
    print("=" * 70)

    # Generate test data
    print(f"\nGenerating {DATA_SIZE_MB}MB of random data...")
    data = generate_test_data(DATA_SIZE_MB, PATTERN, NUM_OCCURRENCES)

    # Run benchmarks
    results = run_benchmarks(data, PATTERN)

    # Compare to naive baseline
    baseline = next(r for r in results if "Naive" in r.name)
    print(f"\nSpeedup vs Naive:")
    for result in results:
        if result.name != baseline.name:
            speedup = baseline.time_ms / result.time_ms
            print(f"  {result.name:<20} {speedup:>6.2f}x")


if __name__ == "__main__":
    main()
