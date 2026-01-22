# Meeting Notes: 2026-01-22

## Brainstorming Session: Charmask Design & Implementation

**Topics Covered:**

1. **[Project Concept & Unicode Filtering Approach](chunk_a.md)**
   - What charmask is (inspired by chardet)
   - Unicode masks as bitmaps/matrices
   - Multi-codepoint challenges (emoji, ZWJ sequences)
   - Core sieve metaphor

2. **[Matrix Math & Novel Applications](chunk_b.md)**
   - Low-rank decomposition (LoRA analogy)
   - Convolution kernels for pattern matching
   - Security applications: WAF scanning, network auth, steganography
   - "Salted sieves" concept

3. **[Grammar Design & Unicode Standards](chunk_c.md)**
   - Research into UnicodeSet notation (ICU/UTS standards)
   - Two-tier grammar (named shortcuts + raw UnicodeSet)
   - Parser generator approach (Lark)
   - Terminology from Unicode developers

4. **[Benchmarks, Validation & Text Diffusion](chunk_d.md)** ⭐ *Most actionable*
   - Benchmark results vs existing methods
   - When our approach wins/loses
   - Text diffusion models (current state 2026)
   - Experimental proposals for validation

## Quick Links

- [Full design notes](../../DESIGN_NOTES.md)
- [Benchmark code](../../benchmark_all.py)
- [Project repo](https://github.com/nomicode/charmask)

## Status

- ✅ Concept validated through benchmarks
- ✅ Grammar designed
- ✅ Novel applications identified
- ⏳ Implementation pending
