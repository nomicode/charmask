#!/usr/bin/env python3
"""
Sieve/Convolution search implementation using PyTorch

This is our novel approach: compile pattern to low-rank matrix,
use convolution to detect matches at hardware speed.
"""

import torch
import torch.nn.functional as F
import time
from typing import List


class ConvolutionSieve:
    """Pattern matching via 1D convolution"""

    def __init__(self, pattern: bytes, use_cuda: bool = False):
        self.pattern = pattern
        self.pattern_len = len(pattern)
        self.device = torch.device("cuda" if use_cuda and torch.cuda.is_available() else "cpu")

        # Build convolution kernel
        # Kernel shape: [out_channels=1, in_channels=256, kernel_size=pattern_len]
        self.kernel = self._build_kernel()

    def _build_kernel(self) -> torch.Tensor:
        """
        Build a convolution kernel that detects the pattern.

        For each position in the pattern, we create a filter that
        responds maximally when that byte value appears.
        """
        # One-hot encode the pattern
        kernel = torch.zeros(1, 256, self.pattern_len, device=self.device)

        for i, byte_val in enumerate(self.pattern):
            # Set weight for this byte value at this position
            kernel[0, byte_val, i] = 1.0

        return kernel

    def search(self, data: bytes) -> List[int]:
        """Find all occurrences of pattern using convolution"""
        # Convert data to one-hot encoding
        # Shape: [batch=1, channels=256, length=len(data)]
        data_tensor = torch.zeros(1, 256, len(data), device=self.device)
        for i, byte_val in enumerate(data):
            data_tensor[0, byte_val, i] = 1.0

        # Convolve pattern kernel over data
        # Output shape: [batch=1, out_channels=1, length=len(data)-pattern_len+1]
        output = F.conv1d(data_tensor, self.kernel)

        # Matches are where output equals pattern length (all positions matched)
        matches = (output[0, 0] == self.pattern_len).nonzero(as_tuple=False)

        return matches.cpu().numpy().flatten().tolist()

    def name(self) -> str:
        return f"Convolution ({self.device})"


class LowRankSieve:
    """
    Low-rank approximation of the pattern matcher.

    Instead of storing full kernel, decompose into A×B.
    For sparse patterns (most real-world cases), this is much smaller.
    """

    def __init__(self, pattern: bytes, rank: int = None, use_cuda: bool = False):
        self.pattern = pattern
        self.pattern_len = len(pattern)
        self.device = torch.device("cuda" if use_cuda and torch.cuda.is_available() else "cpu")

        # Build full kernel first
        full_kernel = self._build_full_kernel()

        # Decompose to low-rank
        self.A, self.B = self._low_rank_decomposition(full_kernel, rank)

    def _build_full_kernel(self) -> torch.Tensor:
        """Build full convolution kernel"""
        kernel = torch.zeros(256, self.pattern_len, device=self.device)
        for i, byte_val in enumerate(self.pattern):
            kernel[byte_val, i] = 1.0
        return kernel

    def _low_rank_decomposition(self, kernel: torch.Tensor, rank: int = None) -> tuple:
        """
        Decompose kernel matrix into A×B using SVD.

        kernel shape: [256, pattern_len]
        Returns: A[256, r], B[r, pattern_len]
        """
        U, S, Vh = torch.linalg.svd(kernel, full_matrices=False)

        # Determine rank (use all non-zero singular values if not specified)
        if rank is None:
            rank = (S > 1e-10).sum().item()

        print(f"  Low-rank: {kernel.shape} -> rank {rank} "
              f"(compression: {(256 * self.pattern_len) / (256 * rank + rank * self.pattern_len):.2f}x)")

        # A = U[:, :rank] * sqrt(S[:rank])
        # B = sqrt(S[:rank]) * Vh[:rank, :]
        A = U[:, :rank] @ torch.diag(torch.sqrt(S[:rank]))
        B = torch.diag(torch.sqrt(S[:rank])) @ Vh[:rank, :]

        return A, B

    def search(self, data: bytes) -> List[int]:
        """Find matches using low-rank decomposition"""
        # One-hot encode data: [256, len(data)]
        data_tensor = torch.zeros(256, len(data), device=self.device)
        for i, byte_val in enumerate(data):
            data_tensor[byte_val, i] = 1.0

        # Compute A^T @ data, then B @ result
        # This is equivalent to (A@B)^T @ data but more efficient
        intermediate = self.A.T @ data_tensor  # [rank, len(data)]
        output = self.B @ intermediate          # [pattern_len, len(data)]

        # Sum over pattern positions
        scores = output.sum(dim=0)  # [len(data)]

        # Matches where score equals pattern_len
        # Need to check windows of correct size
        matches = []
        for i in range(len(data) - self.pattern_len + 1):
            window_score = scores[i:i + self.pattern_len].sum().item()
            if abs(window_score - self.pattern_len * self.pattern_len) < 1e-6:
                # Verify actual match (low-rank might have small errors)
                if data[i:i + self.pattern_len] == self.pattern:
                    matches.append(i)

        return matches

    def name(self) -> str:
        rank = self.A.shape[1]
        return f"Low-Rank r={rank} ({self.device})"


class BitPackedSieve:
    """
    Bit-packed representation for space efficiency.

    Instead of 256-dimensional one-hot, use actual byte values
    and bitwise operations.
    """

    def __init__(self, pattern: bytes, use_cuda: bool = False):
        self.pattern = pattern
        self.pattern_len = len(pattern)
        self.device = torch.device("cuda" if use_cuda and torch.cuda.is_available() else "cpu")

        # Store pattern as tensor
        self.pattern_tensor = torch.tensor(list(pattern), dtype=torch.uint8, device=self.device)

    def search(self, data: bytes) -> List[int]:
        """Vectorized comparison using PyTorch"""
        # Convert to tensor
        data_tensor = torch.frombuffer(data, dtype=torch.uint8).to(self.device)

        # Create sliding windows (unfold)
        if len(data_tensor) < self.pattern_len:
            return []

        windows = data_tensor.unfold(0, self.pattern_len, 1)  # [num_windows, pattern_len]

        # Compare all windows to pattern at once
        matches_mask = (windows == self.pattern_tensor).all(dim=1)

        # Get indices
        matches = matches_mask.nonzero(as_tuple=False).flatten()

        return matches.cpu().numpy().tolist()

    def name(self) -> str:
        return f"BitPacked ({self.device})"


def benchmark_pytorch_methods(data: bytes, pattern: bytes):
    """Benchmark PyTorch-based search methods"""
    from benchmark_search import BenchmarkResult, benchmark_method

    # Check if CUDA is available
    has_cuda = torch.cuda.is_available()
    device_str = "CUDA" if has_cuda else "CPU"

    print(f"\n{'='*70}")
    print(f"PYTORCH SIEVE BENCHMARKS ({device_str})")
    print(f"{'='*70}\n")

    methods = [
        ConvolutionSieve(pattern, use_cuda=has_cuda),
        BitPackedSieve(pattern, use_cuda=has_cuda),
    ]

    # Add low-rank for longer patterns
    if len(pattern) >= 4:
        methods.append(LowRankSieve(pattern, rank=None, use_cuda=has_cuda))

    results = []
    print(f"{'Method':<25} {'Time (ms)':<12} {'Matches':<10} {'Throughput (MB/s)':<20}")
    print("-" * 75)

    for method in methods:
        result = benchmark_method(method, data)
        results.append(result)
        print(f"{result.name:<25} {result.time_ms:<12.2f} {result.matches_found:<10} {result.throughput_mbps:<20.2f}")

    # Find fastest
    fastest = min(results, key=lambda r: r.time_ms)
    print(f"\n🏆 Fastest PyTorch method: {fastest.name} ({fastest.throughput_mbps:.2f} MB/s)")

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

    # Run PyTorch benchmarks
    pytorch_results = benchmark_pytorch_methods(data, PATTERN)

    # Compare to baseline
    print(f"\nFor comparison, Python regex: ~2100 MB/s")
