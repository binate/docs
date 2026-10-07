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
`( Expression )`; a function literal (§10.9); a built-in call (§15); or a
composite literal (§13.10). Postfix operators — selector `.name`, type assertion
`.(T)` (§13.8, §11.12), index/slice `[…]`, and call `(args)` — then apply (§13.8,
§13.9).

> _Note._ The order in which an expression's operands are evaluated is pinned
> where this specification says so — index and sub-slice operands left to right
> (`expr.index.eval-order`), a call's callee and then its arguments left to right
> (§10.3 `func.call.eval-order`), the short-circuit right operand of `&&` / `||`
> only when needed (`expr.logical`), and every assignment (§14.4
> `stmt.assign.eval-order`). Elsewhere — the two operands of an arithmetic,
> bitwise or comparison operator, for instance — it is **unspecified** (§21.5).

## 13.2 Operator precedence and associativity

`expr.precedence` — Operators bind at eleven precedence levels, from tightest
(11) to loosest (1). Like Go — and unlike C — the bitwise and shift operators
bind **tighter** than comparison (so `a & b == c` is `(a & b) == c`). The levels
are otherwise **C's distinct ladder, not Go's collapsed one**: shift binds looser
than additive (`x << 1 + 2` is `x << (1 + 2)`, where Go parses `(x << 1) + 2`),
and `&`, `^`, `|` bind looser still.

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
(MIN / -1)`). Unsigned types have no such case. A constant `MIN / -1` or
`MIN % -1` is instead a compile-time error (§6.4 `const.expr.typed`).

`expr.arith.unsafe` — `unsafe_div(a, b)` and `unsafe_rem(a, b)` (§15) perform the
same integer division and truncated remainder **without** the divide and MIN/−1
fault checks — hardware semantics, undefined on a zero or MIN/−1 divisor. They
are the opt-out for hot paths the caller has proven safe. With constant
operands they are constant expressions, evaluated like `a / b` and `a % b`, so a
zero divisor or `MIN / -1` there is a compile-time error.

## 13.5 Bitwise and shift operators

`expr.bitwise` — `&`, `|`, `^` (binary) and `~` (unary complement) require
**integer** operands. `~x` is the bitwise complement of `x`, of `x`'s own type
(sub-word-correct — `~` of a `uint8` is an 8-bit result). (`~` is the complement
operator; `^` is binary XOR.) When the operands are all untyped constants, the
operators act on their exact, width-independent values (§6.4
`const.expr.bitwise`): `var u uint8 = ~1` is an error (`~1` is -2), not `254`. On
an untyped non-constant integer expression they act at the type it acquires
(`expr.shift.untyped-value.typing`).

`expr.shift` — `<<` and `>>` require integer operands. The **count** (right
operand) may be any integer type, independent of the value's type; the **result
type is the value's** (left operand) type. `>>` is **arithmetic** (sign-filling)
for a signed value and **logical** (zero-filling) for an unsigned value; `<<` is
logical.

`expr.shift.overshift` — A **non-negative** shift count **≥ the value's bit
width** yields a **defined** result on every backend: `0` for a logical shift,
and a full sign-fill (all bits equal the sign bit) for an arithmetic `>>`. (It is
not hardware-masked.) The check reads the **untruncated** count, so a runtime
count wider than the value is detected correctly. (A constant shift of an
untyped value has no width and is exact instead, §6.4 `const.expr.shift`: `1 << 64`
is an error, not `0`.)

`expr.shift.negative` — A **negative** shift count is an error, not a defined
result: a **compile-time** error for a constant count, and a **defined
non-recoverable panic** (`runtime error: negative shift count`; §17.5) for a
runtime count. The guard-free intrinsics `unsafe_shl(v, n)` / `unsafe_shr(v, n)`
(§15.8) perform the shift **without** the negative-count and overshift handling —
the caller asserts `n` is in `[0, width)`, and an out-of-range `n` is undefined
(Ch.21).

`expr.shift.untyped-value` — A shift is a **constant expression** exactly when
both its value and its count are constants (§6.4). A shift that is not a
constant expression and whose value operand is **untyped** — an untyped integer
constant (§6.1 `const.untyped.coercion`: a literal, an untyped constant
expression, or an untyped `const` name) or an *untyped non-constant integer
expression* — is itself an **untyped non-constant integer expression**. So are:
a parenthesized untyped non-constant integer expression; a unary `-` or `~`
applied to one; and a binary arithmetic (`+ - * / %`) or bitwise (`& | ^`)
operator whose operands are each an untyped integer constant or an untyped
non-constant integer expression, at least one being the latter. (`(1 << n) << 2`
is one: its count is constant but its value is not.) An arithmetic or bitwise
operator combining an untyped non-constant integer expression with an untyped
floating-point, boolean, or string constant is an error (§6.5).

`expr.shift.untyped-value.typing` — An untyped non-constant integer expression
is typed **exactly as an untyped integer constant in the same position would
be** (Ch.6, §8.1). For example, it takes the type its context requires at a
conversion boundary (§8.8 `conv.boundaries`: a variable, field, element,
parameter — the element type `T` for a variadic trailing argument — or result),
from the other operand of an enclosing binary arithmetic, bitwise, or comparison
operator when that operand is typed (the typed operand wins: in
`var w int64 = x + (1 << n)` with `x int32` the shift is `int32`, and the
declaration is then an error), from the tag of the enclosing `switch` for a case
expression, or as the target of an enclosing `cast` / `unsafe_cast`; where the
required type is an interface type (`*I`, `@I`, `*any`, `@any`) it takes its
default type `int` and then converts as an `int` value would (§11.4); and where
no type is required it takes its **default type `int`** (§6.2) — for example in
a short or untyped variable declaration (`x := e`, `var x = e`), a blank
`_ = e` assignment, a `switch` tag, an index, sub-slice bound, `make_slice`
length, `unsafe_index` index, shift count, `bit_cast` / `box` operand,
`__c_call` argument, a selector receiver, or a comparison against another
untyped operand. (A type-parameter target takes whatever an untyped constant
takes there, Ch.12.)

The type flows down **only through the operands that make up the expression**
— the operands of `-`, `~`, and the arithmetic and bitwise operators, and the
value operand of each shift; a shift count is its own position (`int` by default
when it is untyped: in `var u uint8 = 1 << (1 << n)` the inner shift is `int`).
Every shift reached this way produces a result of that type; every **maximal
untyped constant subexpression** reached this way — including each shift's
value operand — is evaluated as a constant expression (§6.4) and its **value
must fit** that type (`const.expr.fit`): into a `uint8`, `(1 << n) + (300 - 100)`
is valid (200 fits) and `(1 << n) + (0 - 1)` is an error (-1 does not). A shift
count's type never contributes. The shifted result is not a constant: it is
computed at that type, with `expr.shift.overshift`.

`expr.shift.untyped-value.integer` — The type so determined must be an
**integer type** (an integer type, or a named-distinct, alias, or `readonly`
type whose underlying type is one); otherwise it is an error — the value of a
shift must be an integer. `cast(float64, 1 << n)` and `var f float64 = 1 << n`
are errors; write the width explicitly, `cast(float64, cast(int64, 1) << n)`.
An untyped floating-point, boolean, or string constant is never a valid shift
value (`1.0 << n` is an error).

`expr.shift.untyped-value.not-const` — Such an expression is not a constant, so
it cannot appear where a constant is required: `const C = 1 << n` and
`const C int64 = 1 << n` are errors, as is an array length `[1 << n]T`.
`1 << iota` is a constant shift and is unaffected.

`expr.shift.untyped-value.unsafe` — `unsafe_shl(v, c)` / `unsafe_shr(v, c)`
(§15.8 `builtin.internal`) are typed and folded exactly like `v << c` /
`v >> c`: a constant expression exactly when both operands are constants, and an
untyped non-constant integer expression under the same conditions as a shift.
As a constant expression, a negative count, and a count at least the width of a
typed value's type — both undefined for the unsafe forms at run time
(`expr.shift.negative`) — are compile-time errors: `unsafe_shl(cast(uint8, 1),
8)` is an error, while `unsafe_shl(1, 8)`, whose value is untyped, is `256`.

> _Example._ With `var n uint8 = 9`, `var m uint8 = 0xF0`, `var x int32 = 1`:
>
> ```
> var a uint8 = 1 << n                     // uint8: 0 (overshift at 8 bits)
> var b int64 = 1 << n                     // int64: 512
> c := 1 << n                              // int: 512 (default type)
> var d int64 = cast(int64, (0 + 1) << n)  // int64: 512 — typed like a literal value
> var e uint8 = m & ~(1 << n)              // uint8: the shift and `~` at m's type (0xF0)
> var f uint8 = (1 << n) << 2              // uint8
> var g int64 = x + (1 << n)               // error: the shift is int32 (x's type)
> var h uint8 = (1 << n) + 300             // error: 300 does not fit uint8
> var i int8 = -1 << n                     // int8: `(-1) << n`; 0 (overshift)
> var j int64 = 0x100000000 << n           // int64, on every target
> k := 0x100000000 << n                    // error on a 32-bit target: does not fit int
> var l uint8 = 256 << n                   // error: 256 does not fit uint8
> var p float64 = cast(float64, 1 << n)    // error: the value would be float64
> fmt.Print(1 << n)                        // int (an interface parameter)
> ```
>
> Precedence (§13.2): `1 << n + 1` is `1 << (n + 1)`; `x + 1 << n` is
> `(x + 1) << n`, whose value is typed, so these rules do not apply.

> _Open (residual)._ The native (aarch64/x64/arm32) sub-word `~` and negate paths
> are a tracked residual (Annex C).

## 13.6 Comparison and comparability

`expr.compare.equality` — `==` and `!=` require their operands to be **mutually
assignable** and yield a `bool`. They are defined on integers, floating-point,
`bool`, raw pointers `*T` and managed pointers `@T` (pointer comparison is
**address equality**), and named types over a comparable underlying. `nil` is
compared against the other operand's type (so `p == nil` is valid for a pointer).

`expr.compare.incomparable` — **Slices, interface values, and function values are
never comparable** with `==`/`!=` — not even to `nil`. Test presence with
`present(x)` (§15), or, for slices, with `len`. (Of the three, only **function
values** are nil-*assignable* (§7.7 `type.nil.literal`) — nil-assignable but not
nil-comparable, a deliberate asymmetry with pointers; slices and interface values
take `nil` in neither role.)

`expr.compare.aggregate` — A **struct** or **array** type supports `==` / `!=`
**iff every field / element type is comparable** (applied recursively for nested
aggregates). The comparison is **element-wise**: two values are equal when all
corresponding fields / elements compare equal (each by its own `==`), and `!=` is
the negation. A struct or array containing a non-comparable component (e.g. a
function-typed field) is itself not comparable. The relational operators (`<`, `>`,
`<=`, `>=`) are never defined on aggregates (`expr.compare.relational`).

A **string literal** compared to a comparable char array adopts the array's type
(§6.6 `const.string.compare`) and so compares element-wise under this rule; two
string literals default to `@[]readonly char`, and a string literal against a slice
adopts that slice — either way a slice, so *not* comparable
(`expr.compare.incomparable`).

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
  `getArray()[i]`, indexing a by-value array result, is **not** addressable);
- an **unchecked index** `unsafe_index(x, i)` (§15.6 `builtin.unsafe-index`) is
  addressable exactly when `x[i]` is.

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
a raw slice `*[]T` (§7.5–§7.6) — `*[]readonly T` for a `readonly` array, whose
elements are read-only (§7.5 `type.array.index-slice`).

`expr.index.bounds` — Indexing and sub-slicing a slice or array are
**bounds-checked**: an index outside `[0, len)`, or a sub-slice violating
`0 ≤ lo ≤ hi ≤ len`, is a **defined non-recoverable panic**
(`runtime error: index out of bounds`; §17). **Raw-pointer** indexing is **not**
bounds-checked (a pointer carries no length). `unsafe_index(x, i)` (§15) performs
the indexed access **without** the bounds check.

`expr.index.eval-order` — The operands of an index expression are evaluated
**left to right**, each exactly once: in `x[i]`, the base `x` (with its own
operands) and then the index `i`; in `x[lo:hi]`, `x`, then `lo`, then `hi`. The
order is the same wherever the expression appears — read, assigned to (§14.4),
incremented (§14.5), address-taken (`&x[i]`), or as the operand of a selector or
of a further index (`x[i].f`, `x[i][j]`): `(*p())[i()]++` calls `p` before `i`,
exactly as `(*p())[i()] += 1` and a read of `(*p())[i()]` do.

## 13.10 Composite literals

`expr.composite` — A composite literal builds a value of a struct, array, slice,
or string type, written `Type{ elements }`. Each evaluation constructs a **fresh,
independent** value (a const-element raw-slice literal may, however, alias shared
read-only static storage — sound because it cannot be mutated).

`expr.composite.struct` — A struct literal is **keyed** (`T{x: 1, y: 2}` — order
irrelevant; a key naming no field is an error) or **positional** (`T{1, 2}` — by
declaration order), never both. Omitted fields are zero-initialized (`T{}` is
all-zero); each value must be assignable to its field. A blank `_` field
(§7.4 `type.struct.decl`) cannot be keyed; a positional literal fills it in
order — the one way to give padding a non-zero value.

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
`*[]T{…}` is rejected (use `*[]readonly T{…}` or `@[]T{…}`). The scope-bound
backing holds its own copies of the elements: managed elements are retained when
the literal is evaluated and released when the enclosing scope exits, exactly as
for a local `[N]T` array, so the view stays valid for the whole scope. A string
literal has natural type `[N]readonly char` and **default type** `@[]readonly char` (a
managed-slice view); it is also assignable to the other char array/slice targets —
`@[]char`, `*[]readonly char`, `[N]char`, and `[N]readonly char` (§6.6, §8.1).

`expr.composite.generic` — A composite-literal head may be a **generic
instantiation**: `List[int]{…}`, `Pair[int, S]{first: …, second: …}` (§12). The
element rules are those of the underlying struct/array/slice (above) with the
type arguments substituted; the disambiguation between an instantiated literal
head and indexing is the expression-context rule of §13.11.

`expr.composite.lifetime` — A composite literal's storage is a temporary of its
statement (§18.4 `mem.temporary`): its managed fields or elements are released at
the end of the statement, and a raw pointer into it used after that is a use
after free (§18.7 `mem.raw-uaf`). A literal whose storage is **addressed** within
a local `var` / `:=` initializer instead **lives as long as the new binding** —
it is released when the binding's scope exits (§18.4 `mem.scope-exit`) — whether
its address is taken by `&` (of the literal, or of a field or element of it — an
element of a managed slice whose backing the literal owns included, see
`expr.composite.addr-store`), by
the implicit `&` of a pointer-receiver method call or method value (§10.5), by
sub-slicing an array literal, by an implicit value-borrow into a raw interface
(§11.4 `iface.construct.value-borrow`), or by a raw-slice view of a managed slice
whose backing the literal owns — its managed → raw conversion, implicit or by
`cast` / `unsafe_cast` (§8.4). So `var q *P = &P{name: mk()}`,
`var r *[]int = @[]int{1, 2}` and
`h := P{…}.Name` stay valid as long as `q`, `r` and `h`. One addressed within a `defer`
statement's operands likewise lives until the deferred call has run: it is
released with the function's exit releases, after the pending deferred calls
(§14.13 `stmt.defer`) — so `defer show(&P{…})`, `defer show(id(&P{…}))` and, for a
pointer-receiver `Show`, `defer P{…}.Show()` see the literal intact. Only the
release point moves:
no reference-count operation is added.

`expr.composite.addr-store` _(Constraint)_ — An **assignment** (to a variable,
field or element), a **`return`**, or the initializer of a named **package-level
`var`** (§17 `prog.init.vars`) may not store the address of a composite literal,
which would dangle at the end of the statement. A value **holds an
address into** a literal `L` when it is: `&X`, where `X` designates `L`'s storage
— `L`, a field or element of it, an element of a managed slice whose backing `L`
owns (`L` itself a managed-slice literal, whose one reference owns its backing;
a sub-slice of a slice `L` owns; or a slice held in a field or element of `L`
whose initializer is a managed slice owned so, its reference being held in `L`'s
storage), or a dereference `*p` (or a field or element
reached through `p`) where `p` holds an address into `L`; a sub-slice of an array
whose storage is `L`'s, or of a slice that holds an address into `L`; a `cast`,
`unsafe_cast` or `bit_cast` of such a value; a pointer-receiver method value whose
receiver is `L`'s storage or holds an address into it; an implicit value-borrow
of `L`'s storage into a raw interface (§11.4); a raw-slice view of a managed slice
whose backing `L` owns (as above; the managed → raw conversion, implicit or by
`cast` / `unsafe_cast`); or a field or element read out of a
composite literal — directly, through a pointer holding an address into it, or
out of a slice literal — whose initializer holds an address into `L` (for an
index that is not constant, any element's). The stored value may neither hold an
address into a literal nor contain one: as an element of a stored composite
literal, the operand of a conversion or of `box`, the receiver a value-receiver
method value copies, or the initializer a field or element read comes from.
`q = &P{…}`, `return &P{…}`, `s.h = P{…}.Name`, `q = S{p: &P{…}}.p` and, at
package level, `var g = &P{…}` are rejected. An address passed to a call is not stored by this rule; one the call
hands back is valid only while the literal is.
> _Open / known defects (composite literals)._ Several composite-literal features
> in the design are not correctly implemented and are flagged here pending fixes:
> - **Indexed array literals** `[N]T{ i: v }` (e.g. `[5]int{1: 10, 3: 30}`) are
>   **silently miscompiled** — the index keys are ignored and the values are
>   stored positionally (`{10, 30, 0, 0, 0}` instead of `{0, 10, 0, 30, 0}`).
>   (`expr.composite.array.indexed`, MAJOR; Annex C.)
> - **Inferred-length** `[...]T{…}` is **not implemented** (rejected as a
>   non-constant array length), though the design includes it
>   (`expr.composite.array.inferred-len`; Annex C).
> - **Positional struct elements are not assignability-checked** — a positional
>   struct-literal value is type-checked for well-formedness but **not** verified
>   to be assignable to its field's type, so `expr.composite.struct`'s "each value
>   must be assignable to its field" is unenforced for positional elements (it
>   **is** enforced for keyed elements). (`expr.composite.struct.positional-unchecked`,
>   MINOR; Annex C.) Over-count — more positional values than the struct
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
