# 5. Lexical Elements

> **Status:** normative · **Maturity:** mostly Stable  
> **Rule-ID prefix:** `lex`

This chapter defines how the source text of a Binate file is partitioned into
**tokens**: source representation (§5.1), whitespace and comments (§5.2),
identifiers (§5.3), keywords and builtin-operation keywords (§5.4–§5.5),
predeclared names (§5.6), literals (§5.7–§5.10), escape sequences (§5.11),
operators and punctuation (§5.12), automatic semicolon insertion (§5.13), and
the lexical error model (§5.14).

> _Note._ Most rules in this chapter were established directly against the
> lexer implementation; several long-standing design notes and the reference
> grammar are stale relative to it (e.g. the `readonly` and `Self` keywords and
> four builtin keywords are missing from the grammar). Where this chapter and the
> grammar differ, this chapter governs until the grammar reconciliation
> completes (see Annex A, `notation.grammar.source`).

## 5.1 Source representation

`lex.source.bytes` — A source file is a sequence of bytes. The lexical grammar
classifies **raw bytes**; the source character set is **ASCII**, and no
Unicode decoding is performed. A byte outside the ASCII range is meaningful
only inside a comment, a string literal, or a character literal (where it is
carried through verbatim); anywhere else it is an illegal character
(`lex.error.illegal`).

> _Note._ The design notes did not previously record a source-encoding
> decision; this is the normative rule. Non-ASCII content in string/character
> literals is stored as the literal bytes (UTF-8 is the conventional choice but
> is not interpreted by the language).

`lex.source.eof` — End of input is the boundary past the last byte. An
embedded NUL byte (`0x00`) is treated as end of input; consequently a source
file should not contain an embedded NUL except as end-of-input.

Line and column positions are tracked for diagnostics; lines are delimited by
the newline byte `0x0A`, which is also significant for automatic semicolon
insertion (§5.13).

## 5.2 Whitespace and comments

`lex.whitespace` — Whitespace is exactly the bytes space (`0x20`), horizontal
tab (`0x09`), carriage return (`0x0D`), and newline (`0x0A`). Whitespace
separates tokens and is otherwise insignificant, except that a newline can
trigger semicolon insertion (§5.13). No other byte is whitespace (in
particular vertical tab and form feed are not).

`lex.comment.line` — A **line comment** begins with `//` and runs to the end
of the line (the terminating newline is not part of the comment but still
counts for §5.13).

`lex.comment.block` — A **block comment** begins with `/*` and ends at the
**first** following `*/`. Block comments **do not nest**: a `/*` inside a block
comment has no special meaning, and the first `*/` closes the comment.

> _Note._ An unterminated block comment (no `*/` before end of input) consumes
> the remainder of the file. The current implementation reports no diagnostic
> for this; whether an unterminated comment should be a required diagnostic is
> an open item (`lex.comment.unterminated`, see §5.14).

A comment is treated as whitespace.

## 5.3 Identifiers

`lex.ident.form` — An identifier begins with an ASCII letter or underscore and
continues with ASCII letters, underscores, and digits.

```
identifier  = letter { letter | digit } ;
letter      = "A" … "Z" | "a" … "z" | "_" ;
digit       = "0" … "9" ;
```

Identifiers are case-sensitive and ASCII-only (no `$`, no Unicode). The
single underscore `_` is a valid identifier; its use as a discard target (the
blank identifier) is defined where it applies (Ch.9, Ch.14), not lexically.

An identifier that spells a reserved keyword (§5.4) or a builtin-operation
keyword (§5.5) is that keyword token; otherwise it is an identifier token.

## 5.4 Keywords

`lex.keywords.reserved` — The following 24 identifiers are **reserved
keywords** and shall not be used as ordinary identifiers. Matching is exact and
case-sensitive.

```
break     case      const     continue  default
else      false     for       func      if
impl      import    in        interface nil
package   readonly  return    Self      struct
switch    true      type      var
```

`Self` is the only capitalized keyword (Ch.11). `true`, `false`, and `nil` are
keywords, not identifiers, and denote the corresponding predeclared values
(Ch.6, Ch.7).

> _Note._ Both `const` and `readonly` are reserved: `const` introduces a
> compile-time constant declaration, `readonly` is the type modifier (Ch.9).
> They are distinct keywords, not a rename.

## 5.5 Builtin-operation keywords

`lex.builtins.set` — The following identifiers are **builtin-operation
keywords**: they are reserved (a program shall not use them as ordinary
identifiers) and have special call syntax because several take a *type* as an
argument. Their semantics are defined in Ch.15 (and cross-referenced from
Ch.8).

```
make   make_slice   box    cast   bit_cast   len
unsafe_index   unsafe_div   unsafe_rem   sizeof   alignof
present   same
```

Two further reserved builtin spellings exist for low-level operations:
`_func_handle` (a raw function-address operation; Ch.10) and `__c_call`
(the C-call escape hatch; Annex D). The legacy spelling `_raw_func_addr` is a
**deprecated alias** for `_func_handle` and is slated for removal.

> _Note._ Because these are reserved, identifiers such as `make`, `len`,
> `cast`, and `present` cannot name user variables, functions, or fields.

## 5.6 Predeclared names are not keywords

`lex.predeclared.are-idents` — The predeclared type names — `int`, `uint`, the
sized integer types (`int8`/`int16`/`int32`/`int64`,
`uint8`/`uint16`/`uint32`/`uint64`), `bool`, `byte`, `char`, `any`, `float32`,
`float64` — are **not** keywords. Lexically they are ordinary identifiers; their
predeclared meaning comes from the universe scope (Ch.3, Ch.9) and they may be
shadowed by a user declaration. By contrast `true`, `false`, and `nil` are
reserved **keywords** (§5.4) that denote constant values and cannot be used as
identifiers; and `iota`, though lexically an ordinary identifier, is *not* a
universe binding — it has a special meaning only inside a grouped `const` block
(§9.1). This chapter does not treat any of these as a lexical category.

## 5.7 Integer literals

`lex.literal.int.bases` — Integer literals are written in one of four bases.
The base prefix letter is case-insensitive; hexadecimal digits may be upper- or
lower-case.

```
int_literal  = decimal_lit | hex_lit | octal_lit | binary_lit ;
decimal_lit  = "1" … "9" { digit } | "0" ;
hex_lit      = "0" ( "x" | "X" ) hex_digit { hex_digit } ;
octal_lit    = "0" ( "o" | "O" ) octal_digit { octal_digit } ;
binary_lit   = "0" ( "b" | "B" ) ( "0" | "1" ) { "0" | "1" } ;
hex_digit    = digit | "a" … "f" | "A" … "F" ;
octal_digit  = "0" … "7" ;
```

`lex.literal.int.zero` — A single `0` is the integer zero. The prefixed forms
`0x`/`0o`/`0b` are the only way to write hexadecimal, octal, and binary; there
is no C-style leading-zero octal.

`lex.literal.int.leading-zero` — A multi-digit numeral beginning with `0` and
not using a base prefix (`0123`, `00`) is a **lexical error**, not a decimal
literal (`decimal_lit` admits a leading `0` only as the single digit `0`). The
lexer reports the whole numeral as one illegal token; write `0o…` for octal.

`lex.literal.int.no-sign` — An integer literal contains no sign. A leading `-`
or `+` is a separate unary operator (Ch.13); literal typing and range are
defined in Ch.6.

`lex.literal.int.no-separators` — Digit separators are not supported in any
base. A `_` immediately following digits ends the number and begins an
identifier (so `1_000` is the literal `1` followed by the identifier `_000`).

## 5.8 Floating-point literals

`lex.literal.float.forms` — Floating-point literals are decimal only and take
one of these forms: an integer part with a `.` and an optional fraction and
optional exponent; an integer part with a mandatory exponent and no `.`; or a
leading-`.` form. A trailing dot (`1.`) is permitted.

```
float_literal = digit { digit } "." { digit } [ exponent ]
              | digit { digit } exponent
              | "." digit { digit } [ exponent ] ;
exponent      = ( "e" | "E" ) [ "+" | "-" ] digit { digit } ;
```

`lex.literal.float.range-carveout` — Two dots in a row are never part of a
float: `1..2` is the tokens `1`, `.`, `.`, `2` (the `..` is reserved for future
range syntax), and a leading-`.` float is not recognized when the preceding
token is `.`. A `.` followed by a non-digit is the selector operator, so
`1.field` is `1` then `.` then `field`.

`lex.literal.float.no-hexfloat` — There are no hexadecimal floating-point
literals, and there is no literal syntax for the special values NaN or
infinity (written bare, `NaN`/`Inf` are ordinary identifiers).

## 5.9 String literals

`lex.literal.string.token` — A string literal is a sequence of bytes enclosed
in double quotes (`"`). Lexically, the token's value is the source text between
the quotes; **escape sequences are not interpreted at this stage** (§5.11), and
there is no implicit NUL terminator — the literal denotes exactly the bytes
written (after later escape decoding). A literal newline is not permitted
inside a string literal and ends it.

`lex.literal.string.no-concat` — Adjacent string literals are **not** joined
lexically; each quoted run is a separate token. Concatenation of adjacent
string literals is a syntactic construct defined in Ch.13.

> _Note._ The current implementation does not diagnose an unterminated string
> literal (one ended by end of line or end of input rather than a closing
> quote); it forms a token from the text scanned so far. Whether an
> unterminated string literal must be diagnosed is an open item
> (`lex.literal.string.unterminated`, §5.14).

The natural and default types of a string literal are defined in Ch.6
(`[N]readonly char` and `@[]readonly char` respectively).

## 5.10 Character literals

`lex.literal.char.token` — A character literal is enclosed in single quotes
(`'`). A character literal denotes a single byte value of type `char`
(`= uint8`; Ch.7). Lexically the token's value is the source text between the
quotes; escape sequences are not interpreted at this stage (§5.11).

`lex.literal.char.one` _(Constraint)_ — A character literal shall denote
exactly one byte (one source byte or one escape sequence). An empty character
literal (`''`) or one denoting more than one byte is ill-formed.

> _Note._ This constraint is **not enforced** by the current implementation: an
> empty `''` is silently decoded to the byte `0x00` and a multi-byte literal is
> silently truncated to its first byte/escape, with no diagnostic. It is listed
> among the undiagnosed lexical conditions in §5.14.

## 5.11 Escape sequences

`lex.escape.set` — Within string and character literals, the following escape
sequences are recognized when the literal's bytes are decoded:

| Escape | Meaning |
|--------|---------|
| `\n` `\r` `\t` | newline (`0x0A`), carriage return (`0x0D`), tab (`0x09`) |
| `\\` | backslash |
| `\'` `\"` | single quote, double quote |
| `\0` | NUL (`0x00`) |
| `\xHH` | the byte with the given two hexadecimal digits |

`lex.escape.unsupported` — There is **no** `\uHHHH` (Unicode) escape, and no
`\a`, `\b`, `\f`, `\v`, octal (`\NNN`), or eight-digit `\U` escape. A backslash
followed by any character not listed in `lex.escape.set` is an error, reported as
`unknown escape sequence`; a malformed `\xHH` (a non-hexadecimal digit, or fewer
than two digits) is reported as `\x escape requires two hex digits`.

> _Note (lexical vs. decoding)._ The scanner does not validate or decode
> escapes — it carries the raw text through, and decoding to bytes happens in a
> later phase. A string/character literal's *value* is therefore its decoded
> form; its *token text* is the raw source spelling.

## 5.12 Operators and punctuation

`lex.operators.set` — The operators are:

```
+   -   *   /   %   &   |   ^   ~   <<   >>
==  !=  <   >   <=  >=  &&  ||  !
=   :=  +=  -=  *=  /=  %=  &=  |=  ^=  <<=  >>=   ++  --
```

`lex.punctuation.set` — The punctuation tokens are:

```
.   ,   ;   :   @   #   (   )   [   ]   {   }   ...
```

`@` is the managed-pointer / managed-slice sigil (Ch.7) and `#` introduces an
annotation (Ch.17); both are single tokens at this level. There is no `->`,
`=>`, `::`, `?`, or `>>>`.

`lex.operators.maximal-munch` — Tokenization is greedy (longest match): at each
position the longest token that forms a valid prefix is taken. Thus `<<=` is
one token, not `<<` then `=`; `...` is one token, not `.` `.` `.`.

## 5.13 Automatic semicolon insertion

`lex.semicolon.insertion` — A semicolon is automatically inserted when a
newline (or end of input) immediately follows a token of one of these kinds:

- an identifier;
- an integer, floating-point, string, or character literal;
- one of the keywords `true`, `false`, `nil`, `break`, `continue`, `return`;
- one of `++`, `--`, `)`, `]`, `}`.

After any other token — including binary operators, the opening delimiters
`(`, `[`, `{`, a comma, and other keywords — no semicolon is inserted at a
newline, so expressions, lists, and blocks continue across lines. Newlines
inside comments count for insertion. An explicit `;` is always a statement
terminator.

`lex.semicolon.trailing-comma` — Because a comma does not trigger insertion but
a value-like token does, a multi-line comma-separated list whose closing
delimiter is on a later line **requires a trailing comma** after the last
element; otherwise a semicolon is inserted after that element and breaks the
list. (This matches the corresponding rule in Go.)

## 5.14 Lexical errors

`lex.error.illegal` — A byte that cannot begin any token, and a malformed
numeric literal (for example a base prefix `0x`/`0o`/`0b` with no following
valid digit, or an exponent with no digits), produce an **illegal token**. The
lexer does not abort: it emits the illegal token and continues, so a single
malformed token does not prevent the rest of the file from being scanned. A
program containing an illegal token is ill-formed.

The following lexical conditions are accepted by the current implementation
without a diagnostic; whether each must be a required diagnostic is an **open
item** (and a candidate spec conformance test once decided):

- `lex.comment.unterminated` — an unterminated block comment (§5.2).
- `lex.literal.string.unterminated` — an unterminated string literal (§5.9).
- the single-byte character-literal constraint `lex.literal.char.one` (§5.10) —
  an empty `''` or a multi-byte `'ab'` is currently accepted and silently
  mis-decoded (to `0x00`, or to the first byte) rather than diagnosed.
