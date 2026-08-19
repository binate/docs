# 8. Conversions

> **Status:** normative · **Maturity:** mostly Stable  
> **Rule-ID prefix:** `conv`

A **conversion** changes the type of a value. Binate has a small **closed set
of implicit conversions** (§8.1–§8.4) — applied automatically where a value of
one type is used where another is expected — and three explicit conversion
built-ins on two orthogonal axes: the **logical** conversions `cast` (§8.5, safe
only) and its possibly-unsafe superset `unsafe_cast` (§8.7), and the low-level
**bit reinterpret** `bit_cast` (§8.6). Everything not in the implicit set requires
an explicit conversion.

## 8.1 Assignability — the closed set of implicit conversions

`conv.assignable` — A value of type `S` is **assignable** to type `D` (used
where `D` is expected, with no explicit conversion) iff at least one of the
following holds:

1. `S` and `D` are identical (§7).
2. `S` is an **untyped constant** whose value the type `D` can represent (Ch.6).
3. `S` or `D` is a **named-distinct** type, exactly one side is named, that named
   side's underlying is an **unnamed composite**, and the underlying is
   assignable to the other side (`conv.named`, §7.3).
4. `S` and `D` differ only by **outermost `readonly`** (in either direction), or
   `D` adds **element-level `readonly`** to `S` (`conv.readonly`, §8.3).
5. `S` is a **managed** pointer / slice / function value and `D` is the
   corresponding **raw** form with an identical pointee/element/signature
   (`conv.managed-to-raw`, §8.4).
6. `S` is `nil` and `D` is a **nillable** type — a raw or managed pointer, or a
   function value (§7.7).
7. `S` satisfies the interface that `D` is an interface value of, via a matching
   `impl` (or `D` is `*any`/`@any`), or `S` and `D` are interface values related
   by interface extension (Ch.11).
8. `S` is a string-literal natural type `[N]readonly char` and `D` is one of its
   permitted **char-slice targets** (`@[]readonly char`, `*[]readonly char`,
   `@[]char`) or a **matching-length char array** (`[N]readonly char`,
   `[N]char`) — the string/array-literal decay of §6.6. The `[N]char` form drops
   element-level `readonly`, which is permitted here because the array is
   value-copied (§8.3).
9. `S` is a **reference to a declared function** and `D` is a function-value type
   (`*func(…)` or `@func(…)`, including a named function-value type; §7.3) with a
   matching signature (Ch.10).

The implicit conversions are exactly cases 1–9. This same assignability relation
governs assignment, argument passing, return, and field and element stores
(§8.8).

> _Note._ The interface-satisfaction case (7) is stated fully in Ch.11
> (construction and dispatch); §8 lists it only for completeness of the implicit
> set. A **value** source satisfying `I` constructing a **raw** `*I`/`*any` is
> admitted via the implicit borrow of §11.4 `iface.construct.value-borrow` (Provisional,
> position-restricted); a **managed** `@I`/`@any` from a value still requires an
> explicit `box` (no implicit heap).

## 8.2 No implicit numeric or named conversions

`conv.no-implicit-numeric` — There is **no** implicit conversion between distinct
scalar types: not between signed and unsigned (`int` ↔ `uint`), not between
different integer widths (`int` ↔ `int64`), and not between integer and
floating-point types (`int` ↔ `float64`). A binary operator requires its two
typed operands to be the same type (§7.2). Convert explicitly with `cast`
(§8.5).

`conv.no-implicit-named` — Two **named** types never inter-convert implicitly,
even with identical underlying types, and a named scalar type never converts
implicitly to or from its underlying (`Celsius` ↔ `float64` requires a `cast`;
§7.3). The only implicit named-type crossing is case 3 of `conv.assignable` (a
single named side over an unnamed composite underlying).

## 8.3 `readonly`-adding conversions

`conv.readonly` — `readonly` conversions follow the lattice of §7.11. Outermost
`readonly` is permissive in both directions (`T` ↔ `readonly T`). Adding
element-level `readonly` (behind a pointer, slice, or array handle) is an
implicit *widening* (`*T` → `*readonly T`, `@[]T` → `@[]readonly T`). **Dropping**
element-level `readonly` is **not** implicit and is **not** a `cast` either — it
is an *unverifiable* conversion (another live handle may rely on the `readonly`
view's immutability) and requires **`unsafe_cast`** (§8.7) — with one exception: a
string literal's `[N]readonly char` is implicitly assignable to
a matching-length `[N]char` array, because the array is value-copied into an
independent destination (§8.1 case 8; §6.6).

## 8.4 The managed-to-raw borrow

`conv.managed-to-raw` — A managed pointer, managed-slice, or managed function
value is implicitly convertible to the corresponding **raw** form with an
identical pointee, element type, or signature — `@T` → `*T`, `@[]T` → `*[]T`,
`@func(…)` → `*func(…)` — with no element-level `readonly` drop. The conversion
is a **borrow**: it copies the value's pointer words and takes **no** reference
count, so the result borrows the managed source's pointee without owning it. The
reverse (raw → managed) is never implicit — it would invent a reference (§7.8) —
and has **no `cast`**. For a **pointer** it is the explicit `unsafe_cast(@T, p)`
(§8.7), which asserts a management header exists at the pointee's `−2W` offset. For
a **slice** or **function value** there is no reinterpretation at all — the managed
form carries words the raw form lacks (`@[]T` is four words, `*[]T` two; §7.13) —
so it must be **constructed** explicitly, not cast (`*[]T → @[]T` is under-determined:
`backing`/`backingLen` are not present in the raw value).

> _Provisional._ This borrow is currently permitted in **all** assignment
> contexts, including storing the borrowed raw value into a longer-lived
> location (a field, a returned value) where it can outlive the managed source.
> A proposal would **restrict** the implicit borrow to genuine borrowing
> positions (such as argument passing) and require an explicit `cast` to store a
> raw borrow, so a dangling raw pointer cannot arise implicitly. The rule is
> marked Provisional pending that decision (`proposal-restrict-implicit-raw-conversion`).

## 8.5 `cast` — explicit safe value conversion

> _Draft (redesign in progress)._ The safe-set **gate** (`conv.cast.safe`), the
> aggregate retype (`conv.cast.aggregate-retype`), and the companion `unsafe_cast`
> built-in (§8.7) are specified ahead of the implementation. Until it lands, `cast`
> is realized in the older ungated form, so a `cast` outside the safe set below is
> currently a latent defect (a silent miscompile), not yet the compile-time error
> specified here.

`conv.cast` — `cast(T, x)` is a built-in that converts the value `x` to type `T`
(Ch.15); its result type is `T`. `cast` performs only **safe** conversions — each
is **defined** and cannot corrupt the memory or reference-counting model. Its
accepted set is the union of two parts.

**(1) Everything assignable.** If `x`'s type is assignable to `T` (§8.1, any of
cases 1–9), `cast(T, x)` is permitted, with the same meaning as the implicit
conversion — so `cast` is a strict superset of assignability: identity,
outermost-`readonly` adjustment, the managed→raw borrow, untyped-constant adoption,
the single-named-side composite crossing, and **interface widening** (a concrete
`@T` to an interface value it satisfies, or a sub-interface to a super-interface —
assignability case 7) are all valid casts. (Constructing a **managed** interface
value `@I`/`@any` still needs an already-managed source: a bare **value** is not
assignable to `@I` — it requires an explicit `box` first, no implicit heap (§8.1
note) — so `cast(@I, value)` is rejected with that guidance.)

**(2) Explicit safe conversions** that are not implicit — the numeric scalar
conversions, the named↔underlying scalar crossing, constant typing
(`conv.cast.const-not-laundered`), and the aggregate retype
(`conv.cast.aggregate-retype`):

- **Integer ↔ integer:** the mathematical value modulo the destination's width
  (two's-complement) — narrowing truncates, widening sign-extends a signed source
  and zero-extends an unsigned source. (`cast(uint, x)` of a negative `int` `x`
  yields its two's-complement value.)
- **Integer ↔ floating-point** and **floating-point ↔ floating-point:** converted
  by value. For **floating-point → integer**, a *finite, in-range* value converts
  by truncation toward zero; the **out-of-range / non-finite** edge **saturates** —
  a magnitude above the target type's range (including `+Inf`) yields its `MAX`,
  below its range (including `-Inf`) yields its `MIN` (`0` for unsigned), and `NaN`
  yields `0` (`conv.cast.float-int-saturation` below; catalogued in §21.7).
- **`bool` → numeric:** a `bool` converts to any integer or floating-point type,
  yielding `0` or `1` — a defined, total widening. The **reverse** (`numeric →
  bool`) is **not** a `cast`: a value outside `{0, 1}` is not a valid `bool`, so
  that direction is unverifiable and requires `unsafe_cast` (§8.7).
- **Named ↔ underlying:** a named type converts to and from its underlying, and
  between two named types with the same underlying (`Celsius` ↔ `float64`, or two
  structs sharing one layout); §8.2 requires a `cast` here. This holds for **any**
  type, not just scalars — it is a same-layout retype (no reinterpret, no
  reference-count change), so it is always safe.

`cast` does **not** drop element-level `readonly` — that moves to `unsafe_cast`
(§8.7). (Outermost `readonly` on the whole value needs no `cast`: it is adjusted
implicitly in both directions — part 1 above, §8.3.) A `T` that removes `readonly`
from behind a shared pointer/slice/array handle — `*readonly U → *U`, `@[]readonly U
→ @[]U` — is **not** in the safe set (§8.3).

`conv.cast.safe` — A `cast` whose (source, target) pair is outside the accepted set
above is a **compile-time error** (the checker validates the pair; this replaces the
older "unchecked — the programmer's responsibility" form). The diagnostic names the
correct alternative:

- **`unsafe_cast`** (§8.7) — an *unverifiable* conversion: drop element-level
  `readonly`, raw pointer → managed pointer (`*T → @T`), unchecked interface
  **narrowing**, or an invariant-breaking scalar direction (e.g. `int8 → bool`).
- **`bit_cast`** (§8.6) — a pure same-size **bit reinterpret** (e.g.
  `@[]int32 → @[]float32`, a value-changing element conversion that is not a cast).
- **a type assertion `x.(T)`** (§11.12 `iface.assert`) — a *checked* interface
  narrowing (extract-and-verify; panics on a miss).
- **explicit construction** (allocate + copy) — an under-determined conversion with
  no reinterpretation: `*[]T → @[]T` (a managed-slice cannot be conjured from a raw
  one, §8.4), or an **array → managed-slice** (`[N]T → @[]T`: neither the size nor
  the representation matches — the case the older ungated `cast` silently
  miscompiled).
- **`box`** — a bare value → a managed interface value `@I`/`@any` (no implicit
  heap; §8.1 note).

> _Note (transitivity)._ The safe set is **transitive within each relation**: if
> `cast(T, s)` and `cast(R, t)` are both valid casts of the **same kind** (both
> scalar-numeric, or both aggregate retypes — `conv.cast.aggregate-retype`), then
> `cast(R, s)` is a valid cast too. The scalar and aggregate relations do **not**
> compose across each other. This is a well-formedness property of the safe set,
> used as a design filter: a conversion that would break transitivity is not
> admitted.

`conv.cast.const-not-laundered` — A `cast` does **not** launder a constant. If
`x` is a constant — an untyped literal, a constant expression, or a
`const`-declared name, **including** one given a type by an enclosing `cast` —
then `cast(T, x)` is **itself a constant**, and its mathematical value must fit
`T`'s range, exactly as for a constant assignment (§6.4 `const.expr.fit`). An
out-of-range constant cast is a **compile-time error**:

```
cast(uint, -1)                     // error: -1 not in uint range
cast(uint8, 256)                   // error: 256 not in [0, 255]
cast(int8, cast(int, 200))         // error: still the constant 200, not in int8
const C int = 200; cast(int8, C)   // error: same — no constant→runtime escape
```

A `cast`, like a `const` declaration, is one of the ways a literal acquires a
type, so there is **no** constant→runtime escape: if `const C int8 = 200` is an
error, then every cast naming that same out-of-range value, however nested, is
also an error. To produce an out-of-range value deliberately, **mask** for a
different-size truncation (`cast(uint8, N & 0xff)`) or **`bit_cast`** for a
same-size reinterpret (`bit_cast(uint64, cast(int64, neg))`; §8.6).

`conv.cast.aggregate-retype` — A **container** type — a raw slice `*[]T`,
managed-slice `@[]T`, or array `[N]T` — may be `cast` to the same container shape
over a **different element type** `S` (`*[]S` / `@[]S` / `[N]S`) **iff** both hold:

1. `sizeof(S) == sizeof(T)` — so the element count and the `len` / `backingLen`
   invariants are preserved (a size change would make `len` count the wrong span);
2. the element conversion from `T` to `S` is **total** (defined for every value),
   **bit-preserving** (`cast(S, ·)` equals `bit_cast(S, ·)` on every element), and
   does **not** drop element-level `readonly`.

The retype then reinterprets the elements in place with no per-element work:
`@[]int8 → @[]uint8` and `[4]int8 → [4]uint8` qualify. A **managed** container
retype establishes a new owning handle to the *same* backing and therefore takes a
**reference** (a `RefInc`, exactly like any managed-value copy, §18); a **raw**
container retype **borrows** (no reference). When condition (2) fails — a
value-changing element conversion (`int32 → float32`), a **partial** one
(`int8 → bool`), or an element-`readonly` drop — the container conversion is **not**
a `cast`: use `bit_cast` for a pure reinterpret (§8.6), `unsafe_cast` for the unsafe
element direction (§8.7), or convert element-by-element.

> _Note (leaf rule)._ Condition (2) is the general **leaf-conversion** test: a
> scalar/element conversion qualifies for a container `cast` iff it is total and
> **bit-preserving**. It is deliberately **asymmetric** for `bool` — `bool → int8`
> is bit-preserving (`0`/`1` are valid `int8`, `cast == bit_cast`), while `int8 →
> bool` is not (most `int8` values are not a valid `bool` bit pattern) and needs
> `unsafe_cast`. Note this element/leaf bit-preservation is stricter than the scalar
> `bool → numeric` conversion above: `bool → float32` is a valid **scalar** `cast`
> (a defined widening) but not a **bit-preserving element** retype, so `@[]bool →
> @[]float32` is not a container `cast`.

`conv.cast.float-int-saturation` — **Float → integer at the out-of-range /
non-finite edge saturates** to a single value defined identically across every
backend and the interpreter. The ratified contract (2026-06-12): a value above
the target integer type's `[MIN, MAX]` (including `+Inf`) → `MAX`; below it
(including `-Inf`) → `MIN` (`0` for an unsigned target); `NaN` → `0`; an in-range
value truncates toward zero. This refines Go (which leaves the result
implementation-specific but panic-free) by pinning a defined value, closing what
would otherwise be a hardware-divergence gap (arm64 `FCVTZS` saturates, x86-64
`CVTTSD2SI` yields `INT64_MIN`, a raw LLVM `fptosi` is poison). The normalization
is emitted **once** in shared IR-gen, so every backend and the VM inherit it
without per-backend logic; it is realized and conformant in the current tree
(`conformance/732_float_int_saturation`). The behavior-catalogue entry is §21.7
(`behavior.well-defined`).

## 8.6 `bit_cast` — bit reinterpretation

`conv.bit-cast` — `bit_cast(T, x)` reinterprets the bits of `x` as type `T` with
**no** value conversion — the low-level "I know what I am doing" escape hatch
(Ch.15). Its one **checked** precondition is size: `bit_cast(T, x)` is permitted
**iff** `sizeof(source) == sizeof(T)`, comparing the **proximal** (top-level) size
of the two types — **not** element-wise. Anything of equal size may be
reinterpreted: a typed pointer and the opaque byte pointer `*uint8` (§7.8); an
integer and a floating-point value of the same width; a managed pointer and its raw
form (`@T ↔ *T`, both one word); and — the reason the rule is proximal — a slice or
other aggregate and its **explicit aggregate form**: a managed-slice `@[]T` and a
4-word `struct{data, len, backing, backingLen}`, a raw slice `*[]T` and a 2-word
`struct{data, len}`, an array and a same-size struct. An element-wise reinterpret of
a container (`@[]int32 → @[]float32`) is likewise a single **flat** `bit_cast` (the
proximal sizes are equal — both are 4-word managed-slice headers), **not** a
per-element map.

`bit_cast` takes **no** reference (it never `RefInc`s or `RefDec`s — it is a pure
bit view, not a managed copy); the programmer is responsible for the
reference-count consequences of any managed pointer it thereby fabricates or
duplicates.

A `bit_cast` between types of **different** proximal size is a
**compile-time error**. A same-size `bit_cast` whose **source alignment does not
meet the target's**, or that **violates a type's invariants** — for example reinterpreting
`*[]int32` as `*[]int64` (equal 2-word proximal size, but the result's `len` then
counts a span twice the backing) — is **undefined** (Ch.21).

## 8.7 `unsafe_cast` — possibly-unsafe conversion

> _Draft (redesign in progress)._ `unsafe_cast` is specified ahead of its
> implementation; it does not yet exist as a built-in in the current tree.

`conv.unsafe-cast` — `unsafe_cast(T, x)` is the **possibly-unsafe** companion of
`cast` (Ch.15); its result type is `T`. It accepts a **superset** of `cast`
(`cast ⊆ unsafe_cast`): everything `cast` permits, **plus** the *unverifiable*
conversions `cast` rejects — those whose safety the compiler cannot establish and
the **programmer asserts**. A conversion `cast` already accepts should be written as
`cast`; there is no per-conversion choice between the two spellings — use `cast`
(which errors when the conversion is unsafe) or `unsafe_cast` (which accepts the
risk). The additional conversions `unsafe_cast` permits over `cast` are:

- **Drop element-level `readonly`** — `*readonly T → *T`, `@[]readonly T → @[]T`
  (the `const_cast`-like operation). The programmer asserts no other live handle
  relies on the dropped view's immutability (§8.3, §7.11).
- **Raw pointer → managed pointer** — `*T → @T`. This asserts a valid management
  header exists at the pointee's `−2W` offset (§7.13.7); it is the sanctioned
  explicit raw→managed escape the implicit set forbids (§8.4). (The slice and
  function-value reverses `*[]T → @[]T` / `*func → @func` are **not** included —
  they are under-determined constructions, not reinterpretations; §8.4.)
- **Unchecked interface narrowing** — `@I → @T` / `*I → *T` (a super-interface or
  concrete recovery) that extracts the interface value's data word **without** the
  runtime type check. Contrast the **checked** type assertion `x.(T)` (§11.12
  `iface.assert`), which verifies the dynamic type and panics on a miss;
  `unsafe_cast` performs no check and is **undefined** if the dynamic type does not
  match (Ch.21).
- **Invariant-breaking scalar directions** — a leaf conversion that is defined but
  **not** invariant-preserving, e.g. `int8 → bool` (an `int8` outside `{0, 1}` is
  not a valid `bool`; §8.5 leaf rule).

For the conversions it **shares** with `cast`, `unsafe_cast` behaves exactly like
`cast` — including the value construction and any `RefInc` (a managed interface-value
construction, an aggregate retype; §8.5). The **additional** conversions above are
reference-count-**neutral** reinterpretations of a pointer or data word (no `RefInc`
/ `RefDec`); the programmer is responsible for their reference-count correctness. In
particular `unsafe_cast(@T, p)` and `bit_cast(@T, p)` are operationally identical for
a pointer `p` — a bare pointer-word reinterpret — differing only in stated intent
("logically a `@T`, unchecked" vs "reinterpret the pointer bits").

## 8.8 Conversions at assignment boundaries

`conv.boundaries` — The assignability relation of §8.1 is applied at every
boundary where a value of one type meets an expected type: variable
initialization and assignment, argument passing, `return`, and stores into
struct fields and slice/array elements. The additional *receiver smoothing* that
adapts a receiver value to a method's receiver kind (the permissive→restrictive
directions among raw/managed/`readonly`) is part of method dispatch and is
specified in §7.11 and Ch.10, not here.
