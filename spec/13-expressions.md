# 13. Expressions

> **Status:** normative · **Maturity:** Stable (with flagged composite-literal defects)  
> **Rule-ID prefix:** `expr`

This chapter covers operands and primary expressions (§13.1), operator
precedence (§13.2), arithmetic (§13.3) and its exceptions (§13.4), bitwise and
shift operators (§13.5), comparison and comparability (§13.6), logical operators
(§13.7), unary operators and member access (§13.8), index/slice/bounds
(§13.9), composite literals (§13.10), and the grammar disambiguation rules
(§13.11). There is **no operator overloading**.

## 13.1 Operands and primary expressions

`expr.primary` — A primary expression (operand) is one of: a literal (integer,
floating-point, string, character; or `true`/`false`/`nil`); an identifier or
package-qualified selector (`pkg.name`); a parenthesized expression
`( Expression )`; a function literal (§10.10); a built-in call (§15); or a
composite literal (§13.10). Postfix operators — selector `.name`, type assertion
`.(T)` (§13.8, §11.12), index/slice `[…]`, and call `(args)` — then apply (§13.8,
§13.9).

## 13.2 Operator precedence and associativity

`expr.precedence` — Operators bind at eleven precedence levels, from tightest
(11) to loosest (1). This is the Go model — the bitwise and shift operators bind
**tighter** than comparison (so `a & b == c` is `(a & b) == c`), unlike C.

| Level | Operators |
|-------|-----------|
| 11 (tightest) | postfix `.` `.(T)` `[]` `()` |
| 10 | unary prefix `!` `~` `-` `*` `&` |
| 9 | `*` `/` `%` |
| 8 | `+` `-` |
| 7 | `<<` `>>` |
| 6 | `&` |
| 5 | `^` |
| 4 | `\|` |
| 3 | `==` `!=` `<` `>` `<=` `>=` |
| 2 | `&&` |
| 1 (loosest) | `\|\|` |

`expr.associativity` — Binary operators are **left-associative** (`a - b - c` is
`(a - b) - c`); unary prefix operators are right-associative; postfix operators
apply left to right. **Comparisons do not chain**: `a < b < c` is rejected
(§13.6). Assignment operators (`=`, `+=`, …) and `++`/`--` are **statements**,
not expressions (§14).

> _Note._ Where this precedence and the prose in `claude-notes.md` differ, this
> table (matching the canonical `binate.ebnf`) governs.

## 13.3 Arithmetic operators

`expr.arith.defined` — `+`, `-`, `*`, `/`, `%` operate on two operands of the
**same** numeric type (no implicit int↔float mixing — `cast` is required; §8).
`%` requires **integer** operands (there is no floating-point remainder). For
integers:

- `/` truncates the quotient **toward zero**; `%` (remainder) takes the **sign of
  the dividend**, satisfying `(a/b)*b + a%b == a`.
- signed `+`, `-`, `*` overflow is **defined two's-complement wraparound** (there
  is no overflow trap on `+`/`-`/`*`).
- signed vs unsigned division/remainder is chosen by the (signed or unsigned)
  result type.

`expr.arith.float` — Floating-point `+`, `-`, `*`, `/` follow IEEE-754: there is
**no panic** — division by zero yields ±∞ (or NaN for `0.0/0.0`), and NaN/∞
propagate.

## 13.4 Arithmetic exceptions

`expr.arith.divzero` — Integer `/` or `%` by a **zero** divisor is a **defined
non-recoverable panic** (`runtime error: integer divide by zero`; §17) — not
undefined behavior. A constant division/remainder by zero is instead a
compile-time error (§6).

`expr.arith.minover` — For **signed** integer `/` or `%`, the case *dividend is
the type's most-negative value and divisor is −1* (the two's-complement overflow
case) is a **defined non-recoverable panic** (`runtime error: integer overflow
(MIN / -1)`). Unsigned types have no such case.

`expr.arith.unsafe` — `unsafe_div(a, b)` and `unsafe_rem(a, b)` (§15) perform the
same integer division and truncated remainder **without** the divide and MIN/−1
fault checks — hardware semantics, undefined on a zero or MIN/−1 divisor. They
are the opt-out for hot paths the caller has proven safe.

## 13.5 Bitwise and shift operators

`expr.bitwise` — `&`, `|`, `^` (binary) and `~` (unary complement) require
**integer** operands. `~x` is the bitwise complement of `x`, of `x`'s own type
(sub-word-correct — `~` of a `uint8` is an 8-bit result). (`~` is the complement
operator; `^` is binary XOR.)

`expr.shift` — `<<` and `>>` require integer operands. The **count** (right
operand) may be any integer type, independent of the value's type; the **result
type is the value's** (left operand) type. `>>` is **arithmetic** (sign-filling)
for a signed value and **logical** (zero-filling) for an unsigned value; `<<` is
logical.

`expr.shift.overshift` — A **non-negative** shift count **≥ the value's bit
width** yields a **defined** result on every backend: `0` for a logical shift,
and a full sign-fill (all bits equal the sign bit) for an arithmetic `>>`. (It is
not hardware-masked.) The check reads the **untruncated** count, so a runtime
count wider than the value is detected correctly.

`expr.shift.negative` — A **negative** shift count is an error, not a defined
result: a **compile-time** error for a constant count, and a **defined
non-recoverable panic** (`runtime error: negative shift count`; §17.5) for a
runtime count. The guard-free intrinsics `unsafe_shl(v, n)` / `unsafe_shr(v, n)`
(§15.8) perform the shift **without** the negative-count and overshift handling —
the caller asserts `n` is in `[0, width)`, and an out-of-range `n` is undefined
(Ch.21).

> _Open (residual)._ The native (aarch64/x64/arm32) sub-word `~` and negate paths
> are a tracked residual (`claude-todo.md`).

## 13.6 Comparison and comparability

`expr.compare.equality` — `==` and `!=` require their operands to be **mutually
assignable** and yield a `bool`. They are defined on integers, floating-point,
`bool`, raw pointers `*T` and managed pointers `@T` (pointer comparison is
**address equality**), and named types over a comparable underlying. `nil` is
compared against the other operand's type (so `p == nil` is valid for a pointer).

`expr.compare.incomparable` — **Slices, interface values, and function values are
never comparable** with `==`/`!=` — not even to `nil`. Test presence with
`present(x)` (§15), or, for slices, with `len`. (These types *are* nil-assignable
but not nil-comparable — a deliberate asymmetry with pointers.)

`expr.compare.aggregate` — Struct and array types are comparable in principle
(element-wise, comparable iff every field/element is). **Implementation gap:**
this lowering is not implemented, so `==`/`!=` on a struct or array is currently
rejected ("not yet implemented"). The intended rule is element-wise comparison
(`claude-todo.md`).

`expr.compare.relational` — `<`, `>`, `<=`, `>=` require **numeric** operands
(integer or floating-point, including named types over a numeric underlying) and
yield a `bool`; they are not defined on pointers or aggregates. **No chaining**:
`a < b < c` is an error (§13.2).

`expr.compare.typeparam` — None of the comparison operators (`==`, `!=`, `<`,
`>`, `<=`, `>=`) is available on a value whose type is a **generic type parameter**
(§12): a type parameter is never one of the concrete numeric/comparable types the
rules above require, **regardless of its interface constraints** — an interface
constraint does not make an operator applicable. Generic code compares through the
constraint's **method** instead: `a.Compare(b) == 0` for equality and
`a.Compare(b) < 0` (etc.) for order, on a `Comparable`/`Orderable`-constrained type
parameter (§11.10, §20.1). (Comparison over an interface *value* is likewise a
`Compare` call, not an operator — interface values are `expr.compare.incomparable`.)

`expr.compare.float` — Floating-point comparisons are the ordered IEEE-754
predicates: `==`, `<`, `<=`, `>`, `>=` are **false** when either operand is NaN,
and `!=` is **true** when either operand is NaN. In particular `x == x` is false
and `x != x` is true when `x` is NaN.

## 13.7 Logical operators

`expr.logical` — `&&` and `||` require **`bool`** operands (there is no
truthiness coercion) and yield a `bool`. They **short-circuit**: in `a && b`, `b`
is evaluated only if `a` is `true`; in `a || b`, `b` is evaluated only if `a` is
`false`. `||` binds looser than `&&` (§13.2).

## 13.8 Unary operators and member access

`expr.unary` — The unary operators are `-` (numeric negation), `!` (logical NOT,
on a `bool`), `~` (bitwise complement, §13.5), `*` (pointer dereference, §7.8),
and `&` (address-of). There is **no unary `+`**. `&x` yields a **raw** pointer
`*T` to `x`'s storage (always raw, even for a managed value; §7.8).

`expr.addressable` — An expression is **addressable** when it denotes storage
whose address exists; `&` (`expr.unary.addr`), an assignment target
(`stmt.assign.simple`, §14), and the implicit `&` of receiver smoothing
(`func.method.smoothing`, §10) all require it. Addressability is **recursive**:

- a **variable** — a local, a parameter, or an imported package variable
  (`pkg.v`) — is addressable;
- a **dereference** `*p` (raw or managed) is addressable: it denotes the pointee's
  storage (so `&*p` equals `p`);
- a **composite literal** `T{…}` is addressable: it has a backing alloca (so
  `&Point{1, 2}` is valid);
- a **field selector** `x.f` is addressable **iff** `x` is addressable **or** `x`
  is a pointer (raw or managed) — a pointer base auto-dereferences one level
  (`expr.member`), and the pointee has storage;
- an **index** `x[i]` is addressable when `x` is a **slice** or a **pointer** — it
  reaches storage through the data/base pointer, even when `x` itself is an
  ephemeral value — or an **array** whose base `x` is itself addressable (so
  `getArray()[i]`, indexing a by-value array result, is **not** addressable).

Every **other** operand is a computed value with **no storage** and is **not**
addressable: a **named constant** (§9.1); a **bare literal** (`5`, `3.14`, `true`,
`'a'`, `"s"`, `nil`, or a func literal `func(){}`); a **named function** (`g`,
`pkg.f`) — a function value is obtained by naming the function directly,
`var fp *func() = g`, not by addressing it — or a **method value** (`obj.m`) /
**method expression** (`T.m`); and the result of a **call**, an arithmetic /
unary / comparison expression, or a `make` / `cast` / `bit_cast` / sub-slice
operation. By the recursion, a field or element **of a by-value call result** —
`getStruct().f`, `getArray()[i]` — is therefore **not** addressable (the result
is ephemeral, with no storage), whereas one reached **through a returned pointer**
— `getStructPtr().f` — **is**, via the auto-deref. These rules match Go, except
that a composite literal is addressable in its own right (Go permits only the
`&T{…}` address-of shortcut, not general addressability).

`expr.unary.addr` — The operand of `&` must be **addressable** (`expr.addressable`):
addressing a non-addressable value — most commonly a call result or other computed
value with no storage — is a compile error.

`expr.member` — Member access uses `.` only — there is **no `->`**. A selector
`x.name` auto-dereferences **one** pointer level (raw or managed) to reach a
field or method (§10.5); a field takes precedence over a same-named method. A
selector `pkg.name` resolves a package member; `T.M` is a method expression
(§10.11).

`expr.type-assert` — A **type assertion** `x.(K T)` is a postfix on the `.`
selector, distinguished from a `.name` selector by the `(` that follows the dot
(the token after `.` decides; grammar D13). It recovers a concrete type — or a
narrower interface — from an **interface-value** operand at run time. The operand
and target rules, the **mandatory** `*`/`@`/value recovery kind, the two forms
(the plain expression `x.(K T)` aborts on a miss; the two-target `v, ok := x.(K T)`
is comma-ok), and the exact-vs-implements match are all specified in **§11.12**
(`iface.assert`, `iface.assert.kind`). As a postfix it binds at the tightest
precedence level (§13.2). The related **type switch** statement is §14.10 (§11.12
`iface.typeswitch`).

## 13.9 Index, slice, and bounds

`expr.index` — `x[i]` indexes a slice, array, or raw pointer (or a wrapper
thereof) by an **integer** `i`, yielding the element (or pointee) type. `x[lo:hi]`
takes a sub-slice (endpoints optional and integer; `s[:]`, `s[lo:]`, `s[:hi]`
shorthands); sub-slicing a slice preserves its kind, sub-slicing an array yields
a raw slice `*[]T` (§7.5–§7.6).

`expr.index.bounds` — Indexing and sub-slicing a slice or array are
**bounds-checked**: an index outside `[0, len)`, or a sub-slice violating
`0 ≤ lo ≤ hi ≤ len`, is a **defined non-recoverable panic**
(`runtime error: index out of bounds`; §17). **Raw-pointer** indexing is **not**
bounds-checked (a pointer carries no length). `unsafe_index(x, i)` (§15) performs
the indexed access **without** the bounds check.

## 13.10 Composite literals

`expr.composite` — A composite literal builds a value of a struct, array, slice,
or string type, written `Type{ elements }`. Each evaluation constructs a **fresh,
independent** value (a const-element raw-slice literal may, however, alias shared
read-only static storage — sound because it cannot be mutated).

`expr.composite.struct` — A struct literal is **keyed** (`T{x: 1, y: 2}` — order
irrelevant; a key naming no field is an error) or **positional** (`T{1, 2}` — by
declaration order). Omitted fields are zero-initialized (`T{}` is all-zero); each
value must be assignable to its field.

`expr.composite.array` — An array literal `[N]T{…}` fills positions in order;
omitted trailing positions are zero (`[3]int{7}` → `{7, 0, 0}`; `[N]T{}` is
all-zero).

`expr.composite.array.indexed` — An array literal may set positions **by
index**: `[N]T{i: v}` places `v` at index `i` (a constant in `[0, N)`); positions
not named are zero (`[5]int{1: 10, 3: 30}` → `{0, 10, 0, 30, 0}`). Keyed and
positional elements within one literal are not mixed.

`expr.composite.array.inferred-len` — `[...]T{…}` infers the array length from
the number of elements: `[...]int{1, 2, 3}` has type `[3]int`.

`expr.composite.slice` — A managed-slice literal `@[]T{…}` builds a fresh
managed-slice (a new backing, reference count 1; managed elements are retained).
A raw-slice literal is permitted only with **const elements**, `*[]readonly T{…}`
(a read-only view of static data or a scope-bound stack backing); a non-const
`*[]T{…}` is rejected (use `*[]readonly T{…}` or `@[]T{…}`). A string literal has
natural type `[N]readonly char` and **default type** `@[]readonly char` (a
managed-slice view); it is also assignable to the other char array/slice targets —
`@[]char`, `*[]readonly char`, `[N]char`, and `[N]readonly char` (§6.6, §8.1).

`expr.composite.generic` — A composite-literal head may be a **generic
instantiation**: `List[int]{…}`, `Pair[int, S]{first: …, second: …}` (§12). The
element rules are those of the underlying struct/array/slice (above) with the
type arguments substituted; the disambiguation between an instantiated literal
head and indexing is the expression-context rule of §13.11.

> _Open / known defects (composite literals)._ Several composite-literal features
> in the design are not correctly implemented and are flagged here pending fixes:
> - **Indexed array literals** `[N]T{ i: v }` (e.g. `[5]int{1: 10, 3: 30}`) are
>   **silently miscompiled** — the index keys are ignored and the values are
>   stored positionally (`{10, 30, 0, 0, 0}` instead of `{0, 10, 0, 30, 0}`).
>   (`expr.composite.array.indexed`, MAJOR, `claude-todo.md`.)
> - **Inferred-length** `[...]T{…}` is **not implemented** (rejected as a
>   non-constant array length), though the design includes it
>   (`expr.composite.array.inferred-len`, `claude-todo.md`).
> - **Positional struct elements are not assignability-checked** — a positional
>   struct-literal value is type-checked for well-formedness but **not** verified
>   to be assignable to its field's type, so `expr.composite.struct`'s "each value
>   must be assignable to its field" is unenforced for positional elements (it
>   **is** enforced for keyed elements). (`expr.composite.struct.positional-unchecked`,
>   MINOR, `claude-todo.md`.) Over-count — more positional values than the struct
>   has fields — **is** rejected.

## 13.11 Grammar disambiguation

`expr.disambiguation` — The grammar resolves several ambiguities (the full set,
**D1–D11**, is consolidated in Annex A once authored; until then the per-construct
prose here and the design notes govern). The expression-relevant ones:

- **D1** — a simple statement is parsed as an expression list, then reinterpreted
  by the trailing token (`:=`, `=`, a compound assignment, `++`/`--`, or none →
  expression statement; §14).
- **D4** — in the condition of `if`/`for`/`switch`, a bare composite literal
  `Type{…}` is **not** recognized (the `{` begins the block); the value must be
  produced another way — e.g. by **parenthesizing** it
  (`expr.disambiguation.d4-paren`).
- **D5** — a postfix `[…]` is a slice when it contains `:`, a generic
  instantiation when it has multiple type arguments or its head is a generic
  function, and otherwise an index (resolved during type-checking; §12.2).
- **D8** — `*`/`&`/`-` at the start of an operand are the unary operators; after
  a complete operand they are binary (resolved by precedence; §13.2).

`expr.disambiguation.d4-paren` — A composite literal **may** be used in a
control-flow condition by **parenthesizing** it: `(Point{…})` (e.g.
`if (Point{…}).x == 9 { … }`). Entering parentheses clears the D4
composite-literal suppression.
