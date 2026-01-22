# Chunk C: Grammar Design & Unicode Standards

## Research Phase

User: "Can we be extra nerdy and check what language real Unicode devs use?"

Goal: Use proper terminology from Unicode standards rather than inventing our own.

## Unicode Standards Research

### Standards Discovered

- **UTS #18**: Unicode Regular Expressions
- **UTS #61**: UnicodeSet Notation (canonical spec)
- **ICU (International Components for Unicode)**: Reference implementation

### UnicodeSet Syntax

**Character ranges:**
```
[a-z]           # Simple range
[a c d-f m]     # Multiple ranges with whitespace
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
[A - B]   # Difference (A minus B)
[A + B]   # Union
[A ~ B]   # Symmetric difference (XOR)
[^A]      # Complement
```

### Key Terminology

Official terms to use:
- **Block** (not "range"): `[:block=BasicLatin:]`
- **Category**: `[:Lu:]` (uppercase), `[:Cc:]` (control)
- **Script**: `[:script=Han:]`
- **Property**: Generic term for character attributes
- **UnicodeSet**: The data structure
- **Pattern**: String representation

## Grammar Design Decision

### Two-Tier Approach

**Tier 1: Named shortcuts (beginner-friendly)**
```
allow ascii-printable     # Predefined range
allow cjk-unified
block emoji-modifiers
block sequence "👋🏽"      # Direct Unicode input
```

**Tier 2: Raw UnicodeSet (power users)**
```
allow [:Lu:]              # Direct property access
allow [a-z] - [aeiou]     # Set operations
block [\p{Emoji_Modifier_Base}\p{Emoji_Modifier}]
```

**Mix & Match:**
```
# Super readable mask definition
allow ascii-printable
allow [:script=Cyrillic:]     # Drop to UnicodeSet when needed
block emoji-modifiers
allow [\u2000-\u206F]         # Precise control

# Direct Unicode for sequences
block sequence "👋🏽"
```

### Why Both Tiers?

1. **Learning curve**: Start with `ascii-printable`, graduate to `[:block=BasicLatin:]`
2. **Readability**: `emoji-modifiers` clearer than `[\p{Emoji_Modifier}]` in config
3. **Power**: Drop to raw UnicodeSet for precision
4. **Compatibility**: ICU-familiar users can use what they know

Named shortcuts are **syntactic sugar** that expand to UnicodeSet patterns.

## Grammar Structure (EBNF-style)

```ebnf
statement    := "allow" pattern | "block" pattern
pattern      := named_set | unicodeset | sequence_literal
named_set    := IDENTIFIER ("-" IDENTIFIER)*   # kebab-case
unicodeset   := "[" ... "]"                    # UnicodeSet syntax
sequence_literal := "sequence" STRING

COMMENT      := "#" /[^\n]*/
```

## Parser Generator Choice

**Lark** identified as best option:
- Clean EBNF-style grammars
- Great error messages
- Easy to learn
- Pure Python

Alternatives considered: PLY, pyparsing, ANTLR

## Compilation Architecture

```
.mask file → Lark Parser → AST → Compiler → Optimized kernels → Fast filter
```

Users never touch PyTorch directly - just define masks in clean syntax.

## Open Questions

1. **File extension**: `.mask`, `.umask`, `.charmask`?
2. **Case sensitivity**: Force lowercase or allow mixed?
3. **Implicit behavior**: Default to "block all" or "allow all"?
4. **Multi-line patterns**: Allow operations to span lines?
5. **Normalization**: Always NFC or configurable?

## Bonus: Editor Support

With proper grammar, we get for free:
- Syntax highlighting (TextMate rules)
- LSP potential (autocomplete/validation)
- Error messages with line numbers
- CLI validation tool
