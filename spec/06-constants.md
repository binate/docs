# 6. Constants

> **Status:** normative · **Maturity:** Stable  
> **Rule-ID prefix:** `const`

This chapter defines **constants** — values known at compile time — and in
particular how literals are typed: which literals are *untyped* and how an
untyped constant takes a type (§6.1–§6.2); the integer-constant value range and
constant-expression arithmetic, bitwise, and shift operations (§6.3–§6.4);
floating-point constants and the strict integer/floating rule (§6.5); string and
character literal typing (§6.6); and overflow checking (§6.7).

> _Note._ "Constant" is used in two distinct senses. This chapter concerns
> **untyped literals and constant expressions** over them. The **`const`
> declaration** (Ch.9), which binds a name to a compile-time constant value, is
> a separate construct; the keyword `const` (`term.const`) is unrelated to the
> type modifier `readonly` (`term.readonly`).

## 6.1 Untyped literals

`const.untyped` — An **integer**, **floating-point**, **string**, or
**boolean** literal is *untyped*: it has no inherent type and takes a type from
its context (§6.2, §6.5, §6.6), defaulting as in §6.2. (An untyped integer
constant used as the value of a non-constant shift is typed the same way, as
part of an untyped non-constant integer expression; §13.5
`expr.shift.untyped-value`.) A literal is assignable
to any type that can represent it: an **integer** literal to any integer type
whose range includes its value (the fit *is* enforced — §6.4, §6.7), a
**floating-point** literal to any floating-point type (no magnitude or precision
fit-check is performed at assignment), a **string** literal to its char-slice
and char-array targets (§6.6), and a **boolean** literal to `bool`. A
**character** literal, by contrast, is *typed* as `char` (§6.6).

> _Example._ `123` may be used as an `int`, `uint`, `int32`, `byte`, …; `3.14`
> as a `float32` or `float64`; `"abc"` as any of the string-literal targets in
> §6.6.

`const.untyped.coercion` — Untyped-constant coercion applies to untyped
literals, to constant expressions composed of them, and to a `const`-declared
name whose declaration supplies **no explicit type** (such a name carries an
untyped type and narrows at each use, like a literal). A `const` declared *with*
an explicit type has that definite type and does not coerce (Ch.9).

## 6.2 Default types

`const.default` — When an untyped constant is used where a type is required but
none is supplied by context (for example `x := 123`, or an unconstrained
position), it takes its **default type**:

| Untyped constant | Default type |
|------------------|--------------|
| integer literal | `int` |
| floating-point literal | `float64` |
| string literal | `@[]readonly char` (§6.6) |
| boolean literal | `bool` |

A character literal is already typed `char` (§6.6) and needs no default.

`const.default.int-width` — The default `int` is target-width (32 bits on a
32-bit target, 64 bits on a 64-bit target; Ch.7). An integer literal whose value
does not fit the target's `int` cannot use the default and shall be given an
explicit type (e.g. `var x int64 = 100000000000` or
`cast(int64, 100000000000)`).

## 6.3 Integer constant value range

`const.int.range` — An integer literal shall have a value in the closed range
`[-2^63, 2^64-1]` — the union of the `int64` and `uint64` ranges. A literal
outside this range is rejected at compile time. Thus `0xFFFFFFFFFFFFFFFF`
(= 2^64−1) is a valid literal but `0x10000000000000000` (= 2^64) is not. All
bases (decimal, hexadecimal, octal, binary) denote values in this one space.

`const.int.sign` — A constant whose value fits in `int64` is a signed value
(possibly negative); a constant whose value requires `uint64` (greater than the
`int64` maximum) is a non-negative value. A literal carries no sign of its own
(§5.7); a leading `-` is the unary negation operator applied to the constant.

## 6.4 Constant-expression arithmetic

`const.expr.precision` — A **constant expression** is evaluated on abstract
integer values at **union-range precision** (`[-2^63, 2^64-1]`); each operation
yields the exact mathematical result. If any **intermediate** result falls
outside the union range, the constant expression is rejected at compile time.
There is no wraparound and no arbitrary-precision (bignum) evaluation.

```
1000 - 1000                         -> 0                  (ok)
0xFFFFFFFFFFFFFFFF - 1              -> 2^64 - 2           (ok; fits uint64)
0xFFFFFFFFFFFFFFFF + 1              -> 2^64               (rejected: exceeds union range)
0xFFFFFFFFFFFFFFFF + 1 - 1          -> rejected           (intermediate overflows)
```

> _Note (acknowledged limitation)._ A chain whose final value is representable
> but whose intermediates overflow the union range is rejected; reorder or split
> the expression in source. Go avoids this with arbitrary precision; Binate
> deliberately does not, in exchange for a fixed-width implementation.

`const.expr.signedness` — Constant arithmetic operates at abstract precision
across signedness: e.g. `0xFFFFFFFFFFFFFFFF + (-1)` evaluates to 2^64−2, a
non-negative value usable in a `uint64` context.

`const.expr.fit` — The mathematical value of a constant (literal or constant
expression) must fit the range of the type required by context: a signed target
of `n` bits requires the value to lie in `[-2^(n-1), 2^(n-1)-1]`; an unsigned
target of `n` bits requires `[0, 2^n-1]`. Otherwise it is a compile error
(§6.7).

`const.expr.bitwise` — A bitwise operator `~`, `&`, `|`, or `^` whose operands
are all **untyped** integer constants acts on each constant's
**two's-complement representation extended infinitely to the left**: a
non-negative value has infinitely many leading `0` bits, a negative value
infinitely many leading `1` bits. Each result is therefore an exact integer that
depends on no width: `~x` is `-x - 1`, and `a & b`, `a | b`, `a ^ b` combine the
two representations bit by bit. As for every constant operation, a result
outside the union range is rejected (`const.expr.precision`); the value then
fits a type, or does not, like any other constant (`const.expr.fit`).

`const.expr.shift` — A shift that is a constant expression (both operands
constants, §13.5 `expr.shift.untyped-value`) whose value `x` is an **untyped**
integer constant, with count `k` (a negative constant count is an error,
`expr.shift.negative`), is exact for every `x` of either sign: `x << k` is
`x·2^k`, and `x >> k` is `⌊x / 2^k⌋` (rounded toward −∞, so the sign fills in).
The value has no width, so `expr.shift.overshift` does not apply: for a large
`k`, `x >> k` is `0` when `x ≥ 0` and `-1` when `x < 0`, and `0 << k` is `0`;
any other result outside the union range is rejected — `1 << 64` is an error,
not `0`. `unsafe_shl(x, k)` and `unsafe_shr(x, k)` with constant operands fold
the same way (§13.5 `expr.shift.untyped-value.unsafe`).

```
~1                            -> -2
~-1                           -> 0
-2 | 1                        -> -1
-2 & 0xFF                     -> 254
-2 ^ 3                        -> -3
0xFFFFFFFFFFFFFFFF & ~1       -> 2^64 - 2       (fits uint64)
-1 << 3                       -> -8
-1 << 63                      -> -2^63
-16 >> 2                      -> -4
-3 >> 1                       -> -2             (rounded toward −∞)
-1 >> 1000                    -> -1
~0xFFFFFFFFFFFFFFFF           -> -2^64          (rejected: outside the union range)
0xFFFFFFFFFFFFFFFF ^ -1       -> -2^64          (rejected)
1 << 64                       -> 2^64           (rejected)
var v uint8 = -2 | 1          -> error: -1 does not fit uint8
```

> _Note._ Of these operations on in-range values, `~x` for `x ≥ 2^63` and `^`
> of a value `≥ 2^63` with a negative value always leave the union range
> (landing in `[-2^64, -2^63-1]`); `&` and `|` never do. A left shift leaves it
> exactly when `x·2^k` lies outside it.

> _Note._ Because an untyped constant keeps its exact value until it is typed,
> a complemented untyped mask does not fit an unsigned type: with `x` of any
> unsigned type, `x & ~1` is an error (`~1` is -2), and so are
> `var u uint8 = ~1`, `const C uint8 = ~1`, `Mask uint8 = ~(1 << iota)` in a
> `const` group, and `(1 << n) & ~1` in a `uint8` context (`~1` is its maximal
> untyped constant subexpression, §13.5 `expr.shift.untyped-value.typing`).
> Write the mask directly (`x & 0xFE`), or complement a typed constant
> (`x & ~cast(uint8, 1)`, where `~` is taken at `uint8`'s width, §13.5
> `expr.bitwise`). By contrast `m & ~(1 << n)` is valid at `m`'s type:
> `1 << n` is not a constant, so its `~` is taken at the type the expression
> acquires.

## 6.5 Floating-point constants

`const.float.untyped` — A floating-point literal is untyped with default type
`float64`; it is assignable to `float32` or `float64`. (There is no hexadecimal
floating-point literal and no NaN or infinity literal; §5.8.)

`const.float.no-int-mix` — An untyped **integer** constant is **not** implicitly
converted to a floating-point type: mixing an integer and a floating-point
operand, or assigning an integer constant to a floating-point type, without an
explicit conversion is a type error. Conversions are written with `cast` (e.g.
`cast(float64, n)`, `cast(int, x)`; Ch.8, Ch.15).

> _Note._ This strict no-implicit-`int`↔`float` rule is more restrictive than
> Go's untyped-constant mixing; it may be relaxed for untyped constants in the
> future.

## 6.6 String and character literals

`const.string.types` — A string literal is an untyped constant whose **natural
type** is `[N]readonly char` — exactly the `N` bytes the literal denotes after
escape decoding (§5.11), with no implicit NUL terminator (§5.9) — and whose **default type** is `@[]readonly char` (a
managed-slice view of the static data). Its assignable targets are:

| Target | Effect |
|--------|--------|
| `@[]readonly char` | managed-slice borrowing the static data (zero cost) — the default |
| `*[]readonly char` | raw slice borrowing the static data |
| `@[]char` | allocate and copy (a mutable owned copy) |
| `[M]readonly char` / `[M]char` | array copy; **exact** length `M = N` in general — a **variable-declaration or struct-literal initializer** additionally accepts a *shorter* literal (`M > N`), copying the `N` bytes and **zero-padding** the tail (`M − N`) |

For an array target the literal's `N` bytes must *fit*. At a **variable-declaration
or struct-literal initializer** a shorter literal is allowed (`M ≥ N`): an exact fit
(`M = N`) copies all bytes and a larger buffer (`M > N`) zero-pads the tail (`M − N`)
— a fixed-size string buffer initialized from a shorter literal. In **any other**
position (a `return`, call argument, plain assignment, or comparison) the length
must be **exact** (`M = N`). An **over-long** literal (`N > M`) never fits and is a
compile-time error. The `M > N` zero-pad is an *initializer-only, literal-only*
convenience: it applies only when the source is syntactically a string literal, never
to an arbitrary `[N]readonly char` value (whose array copy always requires an exact
length match — Ch.7).

Assigning a string literal to `*[]char` is **not** permitted (a raw slice
cannot own a mutable copy, and a mutable borrow of read-only static data is
unsound). There is no `string` type; these rules generalize the slice/array
literal rules (Ch.7, Ch.13).

`const.string.compare` — In an `==` / `!=` comparison a string literal takes the
**other operand's** type, exactly as any untyped constant does (§6.1). Against a
comparable **char array** `[N]char` (including a `readonly`-element array or a named
type over one) it therefore compares **element-wise** at **exact** length `N` (§13.6
`expr.compare.aggregate`) — `arr == "abc"` tests whether `arr` holds those bytes, in
either operand order and as a `switch` case; a length mismatch is a type error, not a
comparison. Against **another string literal** neither side has a concrete peer to
adopt, so each takes its default `@[]readonly char` — a slice, which is **not
comparable** with `==` / `!=` (§13.6 `expr.compare.incomparable`); `"a" == "b"` is
rejected. Against a **slice** operand the literal adopts that slice type, likewise
not comparable. (There is no `string` type; comparing arbitrary string *contents*
compares the char values.)

`const.char.type` — A character literal has type **`char`**, which **is**
`uint8` (Ch.7) — not a distinct named type. It is a *typed* constant, so it is
freely usable where `uint8` / `byte` is expected, but requires an explicit
`cast` for other integer types (e.g. `cast(int, c)`, `cast(char, n)`; Ch.8).

## 6.7 Overflow and range checking

`const.overflow` — Assigning a constant — a literal or a constant expression —
to a type that cannot hold its mathematical value is a **compile-time error**.
Fit is checked at compile time against the target type's range (§6.4
`const.expr.fit`).

```
var x uint8  = 256                     // error: 256 not in [0, 255]
var x uint64 = -1                      // error: -1 not in [0, 2^64-1]
var x int64  = 0xFFFFFFFFFFFFFFFF      // error: 2^64-1 not in int64 range
var x uint64 = 0xFFFFFFFFFFFFFFFF      // ok: fits [0, 2^64-1]
```

> _Note._ This compile-time fit-checking applies to *constants*. The runtime
> conversion of a *typed, non-constant* value with `cast` instead wraps or
> truncates with defined hardware semantics (Ch.8, Ch.15).
