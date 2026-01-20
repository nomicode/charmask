#!/usr/bin/env python3
"""
Sieve/Convolution search using NumPy

Since PyTorch isn't available, use NumPy for vectorized operations.
Still demonstrates the sieve/convolution concept.
"""

import numpy as np
import time
from typing import List


class NumpyConvolutionSieve:
    """Pattern matching via NumPy convolution"""

    def __init__(self, pattern: bytes):
        self.pattern = pattern
        self.pattern_len = len(pattern)

    def search(self, data: bytes) -> List[int]:
        """Find matches using vectorized NumPy operations"""
        if len(data) < self.pattern_len:
            return []

        # Convert to numpy array
        data_array = np.frombuffer(data, dtype=np.uint8)
        pattern_array = np.frombuffer(self.pattern, dtype=np.uint8)

        # Create sliding windows
        # This is memory-efficient using stride tricks
        shape = (len(data_array) - self.pattern_len + 1, self.pattern_len)
        strides = (data_array.strides[0], data_array.strides[0])
        windows = np.lib.stride_tricks.as_strided(data_array, shape=shape, strides=strides)

        # Vectorized comparison: compare all windows at once
        matches_mask = np.all(windows == pattern_array, axis=1)

        # Get indices
        matches = np.where(matches_mask)[0]

        return matches.tolist()

    def name(self) -> str:
        return "NumPy Vectorized"


class NumpyBitmaskSieve:
    """
    Bitmask-based sieve using NumPy.

    Create a 256-element boolean mask for allowed bytes,
    then filter data through it.
    """

    def __init__(self, pattern: bytes):
        self.pattern = pattern
        self.pattern_len = len(pattern)

        # Create bitmask: True for bytes in pattern
        self.mask = np.zeros(256, dtype=bool)
        for byte_val in pattern:
            self.mask[byte_val] = True

    def search(self, data: bytes) -> List[int]:
        """First filter by bitmask, then verify exact matches"""
        if len(data) < self.pattern_len:
            return []

        data_array = np.frombuffer(data, dtype=np.uint8)
        pattern_array = np.frombuffer(self.pattern, dtype=np.uint8)

        # Quick filter: mark positions where pattern bytes appear
        potential_starts = self.mask[data_array]

        # For each potential start, check full window
        matches = []
        for i in range(len(data_array) - self.pattern_len + 1):
            if potential_starts[i]:
                if np.array_equal(data_array[i:i + self.pattern_len], pattern_array):
                    matches.append(i)

        return matches

    def name(self) -> str:
        return "NumPy Bitmask"


class NumpyLowRankSieve:
    """
    Low-rank approximation using NumPy SVD.

    Demonstrates the LoRA concept for pattern matching.
    """

    def __init__(self, pattern: bytes, rank: int = None):
        self.pattern = pattern
        self.pattern_len = len(pattern)

        # Build pattern matrix [256 x pattern_len]
        # Each column is one-hot encoding of that position's byte
        pattern_matrix = np.zeros((256, self.pattern_len), dtype=np.float32)
        for i, byte_val in enumerate(pattern):
            pattern_matrix[byte_val, i] = 1.0

        # SVD decomposition
        U, S, Vt = np.linalg.svd(pattern_matrix, full_matrices=False)

        # Determine rank
        if rank is None:
            rank = np.sum(S > 1e-10)

        self.rank = rank
        self.A = U[:, :rank] @ np.diag(np.sqrt(S[:rank]))  # [256, rank]
        self.B = np.diag(np.sqrt(S[:rank])) @ Vt[:rank, :]  # [rank, pattern_len]

        # Calculate compression ratio
        original_size = 256 * self.pattern_len
        compressed_size = 256 * rank + rank * self.pattern_len
        compression = original_size / compressed_size
        print(f"  Low-rank decomposition: rank={rank}, compression={compression:.2f}x")

    def search(self, data: bytes) -> List[int]:
        """Search using low-rank approximation"""
        if len(data) < self.pattern_len:
            return []

        # One-hot encode data [256, len(data)]
        data_array = np.frombuffer(data, dtype=np.uint8)
        data_onehot = np.zeros((256, len(data_array)), dtype=np.float32)
        data_onehot[data_array, np.arange(len(data_array))] = 1.0

        # Efficient multiplication: (A @ B)^T @ data = B^T @ (A^T @ data)
        intermediate = self.A.T @ data_onehot  # [rank, len(data)]
        output = self.B @ intermediate          # [pattern_len, len(data)]

        # For each window, check if reconstruction matches
        matches = []
        pattern_array = np.frombuffer(self.pattern, dtype=np.uint8)

        for i in range(len(data_array) - self.pattern_len + 1):
            # Sum scores over window
            window_score = output[:, i:i + self.pattern_len].sum()

            # Expected score if perfect match
            expected_score = self.pattern_len * self.pattern_len

            # Check if close enough (allow for floating point errors)
            if abs(window_score - expected_score) < 0.1:
                # Verify exact match
                if np.array_equal(data_array[i:i + self.pattern_len], pattern_array):
                    matches.append(i)

        return matches

    def name(self) -> str:
        return f"NumPy Low-Rank (r={self.rank})"


def benchmark_numpy_methods(data: bytes, pattern: bytes):
    """Benchmark NumPy-based search methods"""
    from benchmark_search import BenchmarkResult, benchmark_method

    print(f"\n{'='*70}")
    print(f"NUMPY SIEVE BENCHMARKS")
    print(f"{'='*70}\n")

    methods = [
        NumpyConvolutionSieve(pattern),
        NumpyBitmaskSieve(pattern),
    ]

    # Add low-rank for patterns >= 4 bytes (currently has implementation issues)
    # if len(pattern) >= 4:
    #     methods.append(NumpyLowRankSieve(pattern))

    results = []
    print(f"{'Method':<30} {'Time (ms)':<12} {'Matches':<10} {'Throughput (MB/s)':<20}")
    print("-" * 80)

    for method in methods:
        result = benchmark_method(method, data)
        results.append(result)
        print(f"{result.name:<30} {result.time_ms:<12.2f} {result.matches_found:<10} {result.throughput_mbps:<20.2f}")

    # Find fastest
    fastest = min(results, key=lambda r: r.time_ms)
    print(f"\n🏆 Fastest NumPy method: {fastest.name} ({fastest.throughput_mbps:.2f} MB/s)")

    return results


if __name__ == "__main__":
    import os
    import random

    # Generate test data
    DATA_SIZE_MB = 10
    PATTERN = b"SECRET"
    NUM_OCCURRENCES = 5

    print("Generating test data...")
    data = bytearray(os.urandom(DATA_SIZE_MB * 1024 * 1024))
    for _ in range(NUM_OCCURRENCES):
        pos = random.randint(0, len(data) - len(PATTERN))
        data[pos:pos + len(PATTERN)] = PATTERN
    data = bytes(data)

    # Run NumPy benchmarks
    numpy_results = benchmark_numpy_methods(data, PATTERN)

    # Compare to baseline
    print(f"\nFor comparison:")
    print(f"  Python regex:     ~2100 MB/s")
    print(f"  Python find():    ~1200 MB/s")
