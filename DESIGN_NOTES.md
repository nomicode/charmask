# Charmask Design Notes

## Project Vision

Charmask is a Unicode filtering library inspired by chardet, but for **defining and applying Unicode masks** - think of it as a "sieve" for text streams.

## Core Concept: The Sieve Metaphor

Instead of checking characters one-by-one or writing complex regex, we compile filtering rules into a matrix-based representation that can be applied at high speed.

### The Key Insight

Text streams can be treated as 2D data:
- **Dimension 1**: Codepoint value (what character it is)
- **Dimension 2**: Position in sequence (when it appears)

We slide **kernels** (like in image processing) over this to detect and filter patterns.

## Why This Approach?

### Single Codepoints (Easy Case)
- Unicode codespace: 0x0 to 0x10FFFF = 1,114,112 positions
- As bitmap: ~139KB (1 bit per codepoint)
- O(1) lookup - way faster than regex for category-based filtering

### Multi-Codepoint Sequences (Hard Case)
- Emoji with modifiers: 👋🏽 = U+1F44B + U+1F3FD
- ZWJ sequences: 👨‍👩‍👧 = MAN + ZWJ + WOMAN + ZWJ + GIRL
- Combining marks (NFC normalization helps)

Solution: Use convolution kernels of different sizes to match sequences.

## The Low-Rank (LoRA) Angle

### Why Low-Rank Decomposition Makes Sense

For sparse filtering rules (blocking 0.001% of sequences), we can decompose the pattern matrix:

```
Full matrix: [max_length, 256_bytes] = potentially large
Low-rank:    A[max_length, r] × B[r, 256] = much smaller
```

**Example**: Detecting a 32-byte password
- Full matrix: 32 × 256 = 8,192 elements
- Rank-1 decomposition: 32 + 256 = 288 elements
- **97% reduction!**

### When It Stops Working

When `rank × (dim1 + dim2) > dim1 × dim2`

For most real-world filters (sparse patterns, shared structure), rank stays low.

### Bonus Properties

1. **Compression**: Store many patterns efficiently
2. **Obfuscation**: Reverse-engineering A×B is harder than reading explicit rules
3. **"Salted sieves"**: Add randomization for security applications

## Grammar Design

### Two-Tier Syntax

**Tier 1: Named shortcuts (beginner-friendly)**
```
allow ascii-printable
allow cjk-unified
block emoji-modifiers
```

**Tier 2: UnicodeSet notation (power users)**
```
allow [:Lu:]              # Uppercase letters
allow [a-z] - [aeiou]     # Consonants
block [\p{Emoji_Modifier}]
```

**Mix and match:**
```
# Readable config with escape hatches
allow ascii-printable
allow [:script=Cyrillic:]
block emoji-modifiers
block sequence "👋🏽"
```

### Official Unicode Standards

We adopt notation from:
- **UTS #18**: Unicode Regular Expressions
- **ICU (International Components for Unicode)**: Reference implementation
- **UnicodeSet syntax**: Standard for property matching

#### Key Syntax Elements

**Character ranges:**
```
[a-z]           # Simple range
[\u0020-\u007E] # Hex notation
```

**Unicode properties (two flavors):**
```
[:Lu:]                    # POSIX-style (Uppercase Letter)
\p{Lu}                    # Perl-style
[:block=Greek:]           # Property with value
[:script=Arabic:]         # Script property
```

**Set operations:**
```
[A & B]   # Intersection
[A - B]   # Difference
[A + B]   # Union
[A ~ B]   # Symmetric difference (XOR)
[^A]      # Complement
```

## Benchmark Results

We compared various search methods on 10MB binary data:

| Method | Throughput | Notes |
|--------|-----------|-------|
| Python regex | 1890 MB/s | ✓ Winner (optimized C, SIMD) |
| bytes.find() | 1234 MB/s | ✓ Fast built-in |
| NumPy vectorized | 30 MB/s | Overhead dominates for small patterns |
| Boyer-Moore (Python) | 17 MB/s | Interpreted bytecode penalty |

### Key Insights

1. **We can't beat SIMD-optimized C** for simple pattern matching
2. **But that's not our goal** - we're building something different:
   - Complex multi-pattern Unicode filters
   - Compile-once, use-many-times
   - Clean DSL for Unicode categories/blocks/sequences
   - GPU acceleration potential for streaming data

3. **Where our approach wins:**
   - Multiple patterns searched simultaneously
   - Compiled patterns reused across many inputs
   - Complex Unicode filtering rules
   - Streaming applications where compilation cost is amortized

## Novel Applications Beyond Text Filtering

### 1. Network Security (Layer 2 Authentication)

**Rotating sieves for packet verification:**
```
Packet 0-4999:   Sieve_1 = f(shared_secret, epoch=0)
Packet 5000-9999: Sieve_2 = f(shared_secret, epoch=1)
```

- Embed canary patterns that zero out with current sieve
- Rotation uses packet sequence numbers (no clock sync needed!)
- Each packet independently verifiable (survives packet loss)
- Like TOTP but for streaming data

**Security properties:**
- Provenance verification (is this still from the right sender?)
- Integrity checking (has it been tampered with?)
- NOT confidentiality (use real encryption for that)
- Faster than crypto hashing for line-rate verification

**Use cases:**
- Industrial IoT (lightweight auth, lossy networks)
- Video streaming (verify frames at decoder speed)
- Network telemetry (verify monitoring data)
- Gaming (cheat detection on game state packets)

### 2. Steganography with Sieves as Keys

**The setup:**
```
1. Large noisy container (looks random)
2. Small encrypted message hidden inside
3. Sieve extracts only the signal bits
4. Without sieve, can't tell signal from noise
```

**Security model:**
- Container alone → can't distinguish signal (encryption protects)
- Sieve alone → can extract but can't decrypt (need separate key)
- Need BOTH sieve + encryption key for full access

Like VeraCrypt hidden volumes, but with mathematical extraction key.

### 3. High-Speed Secret Detection

**Applications:**
- WAF scanning for credentials at line rate (100Gbps)
- Network egress monitoring (detect SSH keys, API tokens)
- DLP (Data Loss Prevention) at wire speed

**Why low-rank helps:**
- 32-byte API key detection: 288 params after decomposition
- Fits in fast cache, ultra-quick filtering
- Can run on specialized hardware (ASIC/FPGA)

### 4. Homomorphic-ish Properties

**Research question:** Can we build sieves where:
- Sieve is public (shareable)
- Patterns are private (unrevealed)
- Operations are verifiable (can't be spoofed)

This touches on functional encryption and program obfuscation (active research areas).

## Implementation Roadmap

### Phase 1: Core Library
- [ ] Grammar definition with Lark parser
- [ ] UnicodeSet syntax support
- [ ] Named shortcuts (ascii-printable, emoji, etc)
- [ ] Bitmap implementation for single codepoints
- [ ] Trie for multi-codepoint sequences
- [ ] Python API

### Phase 2: Optimization
- [ ] Compilation to optimized representation
- [ ] Caching compiled masks
- [ ] Streaming API
- [ ] Grapheme cluster handling

### Phase 3: Advanced Features
- [ ] Low-rank decomposition option
- [ ] GPU acceleration (PyTorch backend)
- [ ] C extension for critical paths
- [ ] Security/obfuscation features

### Phase 4: Ecosystem
- [ ] CLI tool
- [ ] VSCode extension (syntax highlighting)
- [ ] Standard mask library (common patterns)
- [ ] Network protocol demo (rotating sieves)

## Open Questions

1. **Normalization strategy**: Always NFC? Let users choose?
2. **Grapheme vs codepoint**: Default to grapheme clusters or explicit opt-in?
3. **Performance target**: What's "good enough" for v1?
4. **API surface**: Functional (immutable masks) or OOP (mutable)?
5. **Security features**: Core library or separate package?

## References

- **UTS #18**: Unicode Regular Expressions
- **UTS #61**: UnicodeSet Notation
- **ICU Documentation**: https://unicode-org.github.io/icu/
- **Mark Pilgrim's chardet**: Inspiration for name and philosophy

## Fun Tangents

> "perhaps black holes are just the universe's loras"

This is the kind of 2am insight that makes sense right up until you try to sleep. 😄

The mathematical analogy is actually kind of beautiful though - both involve:
- Information compression (event horizon / low-rank)
- Irreversible transformation (singularity / matrix decomposition)
- Observable effects without seeing internal structure (gravitational lensing / filtering behavior)

Maybe we're not destroying Claude Shannon's reputation, but we might be onto something interesting.

---

*Last updated: 2026-01-20*
*Status: Design phase, benchmarks complete, ready to build*
