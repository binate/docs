# 8. Conversions

> **Status:** normative · **Maturity:** mostly Stable  
> **Rule-ID prefix:** `conv`

A **conversion** changes the type of a value. Binate has a small **closed set
of implicit conversions** (§8.1–§8.4) — applied automatically where a value of
one type is used where another is expected — and two explicit conversion
built-ins, `cast` (§8.5) and `bit_cast` (§8.6). Everything not in the implicit
set requires an explicit conversion.

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
(§8.7).

> _Note._ The interface-satisfaction case (7) is stated fully in Ch.11
> (construction and dispatch); §8 lists it only for completeness of the implicit
> set.

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
element-level `readonly` is **not** implicit — it requires `cast` (§8.5) — with
one exception: a string literal's `[N]readonly char` is implicitly assignable to
a matching-length `[N]char` array, because the array is value-copied into an
independent destination (§8.1 case 8; §6.6).

## 8.4 The managed-to-raw borrow

`conv.managed-to-raw` — A managed pointer, managed-slice, or managed function
value is implicitly convertible to the corresponding **raw** form with an
identical pointee, element type, or signature — `@T` → `*T`, `@[]T` → `*[]T`,
`@func(…)` → `*func(…)` — with no element-level `readonly` drop. The conversion
is a **borrow**: it copies the value's pointer words and takes **no** reference
count, so the result borrows the managed source's pointee without owning it. The
reverse (raw → managed) is never implicit — it would invent a reference (§7.8).

> _Provisional._ This borrow is currently permitted in **all** assignment
> contexts, including storing the borrowed raw value into a longer-lived
> location (a field, a returned value) where it can outlive the managed source.
> A proposal would **restrict** the implicit borrow to genuine borrowing
> positions (such as argument passing) and require an explicit `cast` to store a
> raw borrow, so a dangling raw pointer cannot arise implicitly. The rule is
> marked Provisional pending that decision (`proposal-restrict-implicit-raw-conversion`).

## 8.5 `cast` — explicit value conversion

`conv.cast` — `cast(T, x)` is a built-in that converts the value `x` to type `T`
(Ch.15). Its result type is `T`. For the defined conversions, `cast` performs a
**value** conversion with well-defined semantics:

- **Integer ↔ integer:** the mathematical value is taken modulo the
  destination's width (two's-complement) — narrowing truncates, widening
  sign-extends a signed source and zero-extends an unsigned source. (`cast(uint, x)`
  of a negative `int` `x` yields its two's-complement value.)
- **Integer ↔ floating-point** and **floating-point ↔ floating-point:**
  converted by value. For **floating-point → integer**, a *finite, in-range*
  value converts by truncation toward zero; the **out-of-range / non-finite**
  edge (a magnitude outside the target integer type's range, `±Inf`, or `NaN`)
  is not yet well-defined — see the second Open note below.
- `cast` **drops `readonly`** (it yields exactly `T`); it is the sanctioned way
  to drop element-level `readonly` (§8.3) and may combine that with a width or
  pointer-target change in one step.

`conv.cast.unchecked` — At the **type-checking** layer, `cast(T, x)` is *not*
validated for convertibility: the checker resolves `T`, checks that `x` is
well-formed, and yields `T`. A `cast` whose source and target are not among the
defined value conversions above is therefore the programmer's responsibility
(its run-time meaning may be unspecified).

> _Open (notes vs. implementation)._ The design notes describe a compile-time
> **fit check** on a constant argument to `cast` (e.g. `cast(uint, -1)` an
> error). The current type-checker does **not** enforce this — `cast` accepts
> any well-formed argument. (This is distinct from the fit-check on a plain
> *assignment* of a constant, which **is** enforced — `var x uint8 = 256` is an
> error; Ch.6.) Whether `cast` should fit-check constant arguments is an open
> item (`conv.cast.literal-fit`, `claude-todo.md`).

> _Open (notes vs. implementation)._ **Float → integer at the out-of-range /
> non-finite edge is currently platform-dependent** (`conv.cast.float-int-saturation`).
> The ratified contract (2026-06-12) is **saturate to the target integer width's
> `[MIN, MAX]`, with `NaN` → `0`** — a single value defined identically across all
> targets, refining Go (which leaves the result implementation-specific but
> panic-free). The current implementation does **not** yet realize it: the LLVM
> backend emits a bare `fptosi`/`fptoui` (`codegen/emit_ops.bn`), so an
> out-of-range or `NaN` source is poison on that path, and the native back-ends
> inherit their ISA's behavior (arm64 `FCVTZS` saturates; x86-64 `CVTTSD2SI`
> yields `INT64_MIN`). Until the saturation lowering lands, this edge is a hole in
> the no-undefined-behavior promise (§19); it is tracked as a MAJOR item
> (`claude-todo.md`) and will be catalogued in Ch.21 once pinned.

## 8.6 `bit_cast` — bit reinterpretation

`conv.bit-cast` — `bit_cast(T, x)` reinterprets the bits of `x` as type `T`
without any value conversion — the "I know what I am doing" escape hatch
(Ch.15). It is used to move between a typed pointer and the opaque byte pointer
`*uint8` (§7.8), and between scalar bit patterns (for example an integer and a
floating-point value of the same width). Like `cast`, it is unchecked at the
type layer (it yields `T`); reinterpreting between types of different size, or in
a way that violates a type's invariants, is undefined (Ch.21).

## 8.7 Conversions at assignment boundaries

`conv.boundaries` — The assignability relation of §8.1 is applied at every
boundary where a value of one type meets an expected type: variable
initialization and assignment, argument passing, `return`, and stores into
struct fields and slice/array elements. The additional *receiver smoothing* that
adapts a receiver value to a method's receiver kind (the permissive→restrictive
directions among raw/managed/`readonly`) is part of method dispatch and is
specified in §7.11 and Ch.10, not here.
