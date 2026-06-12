# 6. Constants

> **Status:** normative · **Maturity:** Stable  
> **Rule-ID prefix:** `const`

This chapter defines **constants** — values known at compile time — and in
particular how literals are typed: which literals are *untyped* and how an
untyped constant takes a type (§6.1–§6.2); the integer-constant value range and
constant-expression arithmetic (§6.3–§6.4); floating-point constants and the
strict integer/floating rule (§6.5); string and character literal typing
(§6.6); and overflow checking (§6.7).

> _Note._ "Constant" is used in two distinct senses. This chapter concerns
> **untyped literals and constant expressions** over them. The **`const`
> declaration** (Ch.9), which binds a name to a compile-time constant value, is
> a separate construct; the keyword `const` (`term.const`) is unrelated to the
> type modifier `readonly` (`term.readonly`).

## 6.1 Untyped literals

`const.untyped` — An **integer**, **floating-point**, **string**, or
**boolean** literal is *untyped*: it has no inherent type and takes a type from
its context (§6.2, §6.5, §6.6), defaulting as in §6.2. A literal is assignable
to any type whose value space includes the literal's value. A **character**
literal, by contrast, is *typed* as `char` (§6.6).

> _Example._ `123` may be used as an `int`, `uint`, `int32`, `byte`, …; `3.14`
> as a `float32` or `float64`; `"abc"` as any of the string-literal targets in
> §6.6.

`const.untyped.coercion` — Untyped-constant coercion applies to untyped
literals, to constant expressions composed of them, and to a `const`-declared
name whose declaration supplies **no explicit type** (such a name carries an
untyped type and narrows at each use, like a literal). A `const` declared *with*
an explicit type has that definite type and does not coerce (Ch.9).

> _Open (design note vs. implementation)._ `claude-notes.md` records a decision
> that untyped coercion does *not* extend to named constants (only literals);
> the current implementation, however, lets an untyped `const` coerce at each
> use (as Go does). This section describes the **implemented** behavior; whether
> the no-coercion decision should instead be enforced is an open item (tracked
> in `claude-todo.md`).

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
type** is `[N]readonly char` — exactly the `N` bytes written, with no implicit
NUL terminator (§5.9) — and whose **default type** is `@[]readonly char` (a
managed-slice view of the static data). Its assignable targets are:

| Target | Effect |
|--------|--------|
| `@[]readonly char` | managed-slice borrowing the static data (zero cost) — the default |
| `*[]readonly char` | raw slice borrowing the static data |
| `@[]char` | allocate and copy (a mutable owned copy) |
| `[N]readonly char` / `[N]char` | array copy (length must match) |

Assigning a string literal to `*[]char` is **not** permitted (a raw slice
cannot own a mutable copy, and a mutable borrow of read-only static data is
unsound). There is no `string` type; these rules generalize the slice/array
literal rules (Ch.7, Ch.13).

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
