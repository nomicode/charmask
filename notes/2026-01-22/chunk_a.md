# Chunk A: Project Concept & Unicode Filtering

## Context

Initial confusion - assistant attempted Python implementation before understanding project scope. User clarified: brand new repo, spiritual successor to chardet.

## Core Concept

**Charmask**: Unicode filtering library allowing users to define "masks" for codepoint filtering.

### Key Metaphor: The Sieve

- Unicode codespace = matrix (1,114,112 codepoints)
- Create binary mask of same dimensions
- Zero out unwanted codepoints
- Filter text streams through this "sieve"

### Why This Approach?

**Single codepoints (easy):**
- Bitmap: ~139KB (1 bit per codepoint)
- O(1) lookup
- Much faster than regex for category-based filtering

**Multi-codepoint sequences (hard):**
- Emoji with modifiers: 👋🏽 = U+1F44B + U+1F3FD
- ZWJ sequences: 👨‍👩‍👧 = MAN + ZWJ + WOMAN + ZWJ + GIRL
- Combining marks (NFC normalization helps but not complete solution)

## The Question

User: "Is this completely bonkers?"

**Answer: No.** Core idea solid for single codepoints, multi-codepoint needs hybrid approach.

## Initial Solution Direction

1. **Bitmap for single codepoints** (fast path)
2. **Sequence trie or rules** for multi-codepoint patterns (slow path)
3. **Process grapheme-by-grapheme**, not codepoint-by-codepoint

## Conceptual Leap

User insight: Treat text as 2D signal processing problem
- Dimension 1: Codepoint value (what)
- Dimension 2: Position in sequence (when)
- Apply **convolution kernels** like image processing

This led to matrix mechanics discussion in Chunk B.

## Is It Novel?

- Bitmap character sets exist
- **Novel part:** Modern Python API with grapheme-aware filtering, ergonomic mask definition, and compilation to efficient representations
- Fills gap between "use regex" and "write custom parser"

## User Motivation

"Sick of seeing answers online being overly simple or involving a page full of minified regex. I just want a sieve!"
