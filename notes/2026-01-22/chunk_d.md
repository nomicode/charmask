# Chunk D: Benchmarks, Validation & Text Diffusion ⭐

## Reality Check: Benchmark Results

### Test Setup
- 10MB random binary data
- 6-byte pattern (`b"SECRET"`)
- 5 random occurrences
- Various search methods

### Results

| Method | Throughput (MB/s) | Notes |
|--------|------------------|-------|
| **Python regex** | 1,890 | Winner (optimized C + SIMD) |
| bytes.find() | 1,234 | Fast built-in |
| NumPy vectorized | 30 | Array overhead dominates |
| Boyer-Moore (Python) | 17 | Interpreted bytecode penalty |
| Rabin-Karp | 9 | Hash computation overhead |
| Bloom filter | 5 | False positive checks expensive |

### Verdict

**We lost 60x to regex.** But that's okay.

## When Our Approach Wins

### Where Regex/Built-ins Win
- Single simple pattern
- Small data
- One-off searches

### Where Charmask Wins
✓ **Multiple patterns** searched simultaneously
✓ **Compiled once, reused many times**
✓ **GPU acceleration** (PyTorch/CUDA backend)
✓ **Streaming data** (amortize compilation cost)
✓ **Complex Unicode patterns** (grapheme clusters, category combinations)
✓ **Security applications** (obfuscation, low-rank compression)

## Experimental Proposals

### Experiment 1: Multi-Pattern Performance

**Hypothesis:** Charmask wins when filtering multiple patterns at once.

**Test:**
```python
patterns = [
    "allow [:Lu:]",           # Uppercase
    "block [:Emoji:]",        # All emoji
    "allow [:script=Latin:]", # Latin script only
    "block [\\x00-\\x1F]",    # Control chars
]

# Compare:
# 1. Multiple regex.sub() calls
# 2. Single compiled charmask
# 3. Measure throughput at 1, 10, 100, 1000 patterns
```

**Expected:** Regex degrades linearly, charmask stays constant (or better with batching).

**Open weights models needed:** None (pure algorithmic comparison)

**Estimated effort:** 2-3 hours

---

### Experiment 2: Streaming Unicode Normalization

**Hypothesis:** Combined NFC normalization + filtering is faster than separate passes.

**Test:**
```python
# Scenario: Filter 1GB of mixed Unicode text
# (Latin, CJK, Emoji, combining marks)

# Method A: unicodedata.normalize('NFC') then filter
# Method B: Normalize + filter in single pass (our approach)
# Method C: Pre-compiled sieve with grapheme awareness
```

**Datasets:**
- Wikipedia dumps (mixed scripts)
- Twitter emoji-heavy corpus
- Technical docs (mostly ASCII + code)

**Open source tools:**
- `unicodedata` (stdlib)
- `grapheme` library
- `regex` module (better Unicode support)

**Estimated effort:** 4-6 hours

---

### Experiment 3: Low-Rank Compression Validation

**Hypothesis:** Real-world filter rules have low intrinsic rank.

**Test:**
```python
# Build filter matrices for common use cases:
use_cases = [
    "Block all emoji (1500+ codepoints)",
    "Allow ASCII + Latin Extended",
    "Block common XSS chars",
    "Allow printable + CJK Unified",
]

for use_case in use_cases:
    matrix = build_filter_matrix(use_case)
    U, S, Vt = np.linalg.svd(matrix)

    # Find effective rank
    rank = (S > 1e-10).sum()
    compression_ratio = original_size / compressed_size

    print(f"{use_case}: rank={rank}, compression={compression_ratio}x")
```

**Expected:** Most cases have rank << matrix dimensions (high compression).

**Estimated effort:** 2 hours

---

### Experiment 4: GPU Acceleration Feasibility

**Hypothesis:** PyTorch GPU backend provides meaningful speedup for large-scale filtering.

**Test:**
```python
# Scenario: Filter 10GB text corpus
# Compare CPU vs GPU throughput

# Use Google Colab (free T4 GPU access)
import torch

data_sizes = [1, 10, 100, 1000]  # MB
patterns = load_common_patterns()

for size in data_sizes:
    data = generate_unicode_text(size)

    # CPU
    cpu_time = benchmark(filter_cpu, data, patterns)

    # GPU
    gpu_time = benchmark(filter_gpu, data, patterns)

    print(f"{size}MB: CPU={cpu_time}s, GPU={gpu_time}s, speedup={cpu_time/gpu_time}x")
```

**Open weights models:** None (pure computation)

**Free resources:** Google Colab, Kaggle notebooks

**Estimated effort:** 3-4 hours

---

### Experiment 5: Adversarial Sieve Reverse Engineering

**Hypothesis:** Low-rank decomposition makes rules harder to reverse-engineer than explicit lists.

**Test:**
```python
# Create secret pattern filter (e.g., SSN detection)
secret_pattern = compile_pattern("SSN_REGEX")

# Store three ways:
# 1. Raw regex string
# 2. Explicit pattern list
# 3. Low-rank decomposition A×B

# Attack: Give adversary black-box access
# Can they recover the pattern?

for storage_method in [raw, explicit, lowrank]:
    queries = adversarial_probe(storage_method, max_queries=10000)
    recovered = attempt_recovery(queries)
    accuracy = measure_recovery(secret_pattern, recovered)

    print(f"{storage_method}: recovered with {accuracy}% accuracy")
```

**Expected:** Low-rank significantly harder to reverse-engineer.

**Related work:** Program obfuscation, watermarking research

**Estimated effort:** 6-8 hours (complex)

---

## Text Diffusion Models (Tangent)

### What Exists in 2026

User asked about text diffusion (inspired by img2img, ControlNet, LoRAs).

**Major developments:**
- **Diffusion-LM (2022)**: Non-autoregressive text generation via diffusion
- **Google Gemini Diffusion (2025)**: 1,479 tok/s (5x faster), commercial parity
- **Discrete DLMs**: D3PM, DiffusionBERT, SEDD (ICML Best Paper)

### Capabilities That Actually Exist

✓ **txt2txt** (paraphrase generation)
✓ **Masking/inpainting** (fill blanks, edit spans)
✓ **Fine-grained control** (syntax, style, length, attributes)
✓ **Style transfer** (formality, tense, tone)
✓ **Compositional edits** (multiple style changes at once)

### The Mapping to Image Diffusion

| Image Concept | Text Equivalent | Status |
|--------------|-----------------|--------|
| img2img | Paraphrase/style transfer | ✅ Works (LDP, StylePTB) |
| ControlNet | Structural constraints | ✅ Works (Diffusion-LM) |
| Inpainting | Masked editing | ✅ Works (EdiText, Masked-Diffuse) |
| LoRA | Style adapters | ⚠️ Possible but not standardized |
| Prompt guidance | Attribute control | ✅ Works (classifier-free guidance) |

### Novel Writing Use Case

User's shower thought: Template-guided novel generation with theme LoRAs.

**This is feasible:**
```
Input: High-level structure (user's brainstorm notes)
+ Base model: Fine-tuned on user's writing corpus
+ LoRAs: Theme modules (gothic, mystery, YA, etc.)
+ Mask: Protect character descriptions, allow setting to evolve
+ Control: "1000 words, maintain mystery, add sensory detail"

Output: Fully fleshed-out chapter preserving narrative bones
```

**What's missing:**
- Easy-to-use tools (no Automatic1111 equivalent)
- Pre-trained models for download
- Standard LoRA ecosystem (like CivitAI for text)
- Visual UIs for masking

**It's where Stable Diffusion was in early 2022** - works in research, not consumer-ready.

### Experiment 6: Text Diffusion Prototype

**Hypothesis:** Can build usable text diffusion pipeline with open models.

**Test:**
```python
# Use HuggingFace diffusion models
from transformers import AutoModelForCausalLM
from diffusers import DiffusionPipeline  # If text diffusion available

# Scenario: Style transfer with masking
input_text = "The hero walked into the dark forest."
mask = "[The hero] walked into the [dark forest]."
         # ^ preserve  ^ allow modification

# Try different approaches:
# 1. Fine-tuned T5 with masking
# 2. Diffusion-LM (if available)
# 3. BERT-based masked language model

output = diffuse(
    input_text,
    mask=mask,
    style="gothic horror",
    model="stabilityai/stable-diffusion-text"  # Hypothetical
)
```

**Open source resources:**
- HuggingFace Transformers
- Diffusion models on HF Hub
- Papers with code implementations

**Expected challenges:**
- Text diffusion models less mature than image
- May need to implement from papers
- Inference speed might be slow

**Estimated effort:** 8-12 hours (exploratory)

---

## Next Steps Recommendation

**Priority order for experiments:**

1. **Experiment 3** (low-rank validation) - Fastest to prove core concept
2. **Experiment 1** (multi-pattern) - Validates main use case
3. **Experiment 2** (streaming Unicode) - Real-world applicability
4. **Experiment 4** (GPU) - Performance scaling
5. **Experiment 5** (adversarial) - Security claims
6. **Experiment 6** (text diffusion) - Fun but tangential

**Parallel work:**
- Implement basic grammar parser (Lark)
- Build minimal bitmap filter
- Create test corpus (mixed Unicode)

## Resources & Links

**Open source tools:**
- `lark-parser` (grammar parsing)
- `numpy`, `pytorch` (matrix ops)
- `unicodedata`, `grapheme` (Unicode handling)
- `regex` module (better Unicode than `re`)

**Datasets:**
- Wikipedia dumps (mixed scripts)
- Common Crawl (web text)
- Unicode test data (unicode.org)

**Computing:**
- Google Colab (free GPU)
- Kaggle notebooks (free GPU)
- GitHub Actions (CI/CD, benchmarks)

**References:**
- [Diffusion-LM Paper](https://arxiv.org/abs/2205.14217)
- [Text Diffusion Survey](https://pmc.ncbi.nlm.nih.gov/articles/PMC10909201/)
- [ICU Documentation](https://unicode-org.github.io/icu/)
- [UnicodeSet Syntax](https://github.com/Azmisov/unicodeset)

## Timeline Estimate

**Week 1:** Experiments 1-3, basic implementation
**Week 2:** Grammar parser, bitmap filter, tests
**Week 3:** Experiments 4-5, optimization
**Week 4:** Documentation, demo, polish

(Note: No specific hours/days per user request for no timelines)
