# 7. Types

> **Status:** mixed · **Maturity:** mostly Stable (caveats per section)  
> **Rule-ID prefix:** `type`

This chapter is the type catalogue: value vs reference types (§7.1); scalar
types (§7.2); named-distinct types and aliases (§7.3); structs (§7.4); arrays
(§7.5); slices (§7.6); `nil`, empty, and the length-0 invariant (§7.7);
pointers (§7.8); function types (§7.9); interface value types and `any`
(§7.10); the `readonly` modifier (§7.11); and opaque (forward-declared) types
(§7.12). The memory **layout** of every type — the cross-mode ABI contract — is
specified separately in **[§7.13 Type Layout & Representation](07b-type-layout.md)**.

## 7.1 Value types and reference-bearing values

`type.value.categories` — Every Binate type is a **value type** in the copy
sense: assignment, parameter passing, and return copy the value, which lives
inline (on the stack or embedded in a containing aggregate). The value types
are: `bool`, the integer and floating-point scalars (§7.2), raw pointers `*T`,
managed pointers `@T`, structs, arrays `[N]T`, raw slices and managed-slices,
function values, and interface values. A **managed pointer `@T` is itself a value type**
— copying it is a value copy that additionally adjusts the pointee's reference
count.

`type.value.managed-arise` — A managed pointer is never taken from an lvalue:
the address operator `&x` always yields a *raw* pointer (§7.8). A managed
pointer arises only from `make`, `box`, or `make_slice` (Ch.15). To heap-manage
an array, write `@([N]T)` (and allocate with `make`).

`type.value.copy-semantics` — Copying a value that (recursively, through struct
fields, array elements, and named/alias/`readonly` wrappers) contains a managed
component — a managed pointer, managed-slice, managed function value, or managed
interface value — increments the reference counts of those components; a value
containing only scalars and raw pointers copies as a plain bit copy. A type
**needs destruction** iff it (recursively) contains a managed component (Ch.18).

## 7.2 Scalar types

`type.scalar.universe` — The predeclared scalar types are exactly: `bool`,
`char`, `int`, `int8`, `int16`, `int32`, `int64`, `uint`, `uint8`, `uint16`,
`uint32`, `uint64`, `float32`, `float64`, and `byte`. There is no `string` type
(text is `[N]readonly char` / `@[]readonly char`; §7.6) and no `uintptr` (`uint`
serves that role — pointer size equals word size on every target). `true`,
`false`, and `nil` are predeclared *constants*, not types (Ch.6, §7.7).

`type.scalar.int-width` — `int` and `uint` are the target word-sized signed and
unsigned integers: their width equals the target's pointer width (32 bits on a
32-bit target, 64 on a 64-bit target). The sized integers `int8`…`int64` /
`uint8`…`uint64` have the width named. Integers are two's-complement: a signed
`w`-bit type covers `[-2^(w-1), 2^(w-1)-1]`, an unsigned one `[0, 2^w-1]`.

`type.scalar.char-byte-uint8` — `char`, `byte`, and `uint8` are **the same
type** — an 8-bit unsigned integer — under three spellings; no conversion is
needed between them. (They are alternative names for one type, not distinct
alias types.) A character literal has type `char` (= `uint8`; Ch.6).

`type.scalar.bool` — `bool` is a distinct non-numeric type with values `true`
and `false`. It is not an integer, is not a relational operand, and is the
required operand type of the logical operators `&&` and `||` (Ch.13).

`type.scalar.no-implicit-mix` — There is no implicit conversion between scalar
types. A binary arithmetic, bitwise, or relational operator requires its two
typed operands to be the *same* type (same width and signedness for integers,
same width for floats); there is no implicit widening between integer types and
no implicit `int`↔`float` mixing. Convert explicitly with `cast` (Ch.8, Ch.15).
The untyped-constant rules that let a literal take a scalar type from context
are in Ch.6.

> _Note._ Scalar **sizes and alignments** — including the target-parameterized
> width of `int`/`uint` and the alignment clamp to the target's maximum — are
> specified in [§7.13](07b-type-layout.md).

## 7.3 Named-distinct types and aliases

`type.decl.two-forms` — There are two `type` declaration forms:

```
TypeDecl  = "type" identifier [ TypeParams ] TypeDef ;
TypeDef   = Type                       (* distinct: type X U  *)
          | "=" Type                   (* alias:    type X = U *)
          | (* empty *)                (* forward/opaque: type X — §7.12 *) ;
```

`type X U` (no `=`) declares a **distinct (named) type**: `X` is a new type
different from its **underlying type** `U`, may carry methods and implement
interfaces, and converts to/from `U` only with an explicit `cast`. `type X = U`
declares an **alias**: `X` is interchangeable with `U` (the same type) and may
not carry methods. A distinct type may be formed over any underlying — a scalar
(`type Celsius float64`), a pointer (`type Handle @Box`), a slice
(`type Buf @[]int`), an array, a struct, or a function value. `type`
declarations are package-level only; a function-local `type` is a parse error.

`type.alias.transparency` — An alias is the same type as its target in every
respect: identity, assignability, method resolution, and comparison see through
it. An alias of an interface is the same interface for `impl` matching.

`type.named.transparency` — A distinct type is **transparent** to its underlying
type for operators (arithmetic, bitwise, shift, relational, equality), the
built-ins that act on the underlying kind (`len`, `present`, `same`), indexing
`b[i]`, slicing `b[lo:hi]`, and field access `h.f` (including auto-dereference
when the underlying is a pointer). The checker peels the named wrapper (and any
`readonly` or alias wrapper) to the underlying before applying the operation.

`type.named.methods-not-inherited` — A distinct type does **not** inherit its
underlying type's methods or interface impls. Method and impl lookup uses the
distinct type's own method set; reach an underlying type's methods through an
explicit `cast` to that type. (Fields are transparent, methods are not — Go's
defined-type model.)

`type.named.assignability` — A value crosses a distinct-type boundary **without**
a `cast` iff exactly one side is the named type *and* its underlying is an
**unnamed composite** (a slice, managed-slice, pointer, managed-pointer, array,
or struct), in which case the ordinary assignability of the underlying applies.
Two named types never inter-assign implicitly, even with identical underlying
types. A scalar (or otherwise non-unnamed-composite) underlying always requires
a `cast` (so `Celsius`↔`float64` needs a cast — the underlying `float64` is a
scalar, not an unnamed composite).

> _Example._ `type Buf @[]int`: `var b Buf = make_slice(int, 3)` and
> `var s @[]int = b` both work (the underlying `@[]int` is an unnamed composite).
> But `type A @[]int; type B @[]int` are not inter-assignable without a `cast`.

`type.named.func-value-nominal` — As an exception to the unnamed-composite rule,
a named **function-value** type is *nominal*: a bare existing `@func(int) int`
value is **not** implicitly assignable to `Fn`. `Fn` is constructible from a
function *reference* (a named function); construction from a function *literal*
(`var f Fn = func(…){…}`) is a known gap — not yet supported and currently
rejected.

`type.named.comparison` — Comparability follows the underlying type: `type ID int`
is comparable. The one deviation from Go is that **slices are never comparable**
(§7.6), so a named slice type is not comparable at all. Equality on struct and
array types is not currently available (rejected). The full equality and
relational rules — including which aggregate types are comparable — are Ch.13.

`type.named.methods-same-package` — A method or `impl` requires a receiver that,
after stripping `*`/`@`/`readonly`, is a named type declared in the **same
package** as the method. Aliases, predeclared/builtin types, anonymous types,
and types imported from other packages may not be receivers. (The one carve-out
is the intrinsic package `pkg/builtins/lang`, which may declare methods on the
universe primitives `int`/`float`/`bool`; §20.1.)

`type.named.identity` — Two distinct types are identical iff they have the same
identity: a named struct is identified by its package-qualified name (e.g.
`pkg/foo.Box`), a named non-struct distinct type by the wrapper's own name. Two
cross-package types with the same short name are distinct.

> _Note (cast is unchecked at this layer)._ The "requires `cast`" rule is
> enforced *negatively* — implicit assignment across a distinct-type boundary is
> rejected. The `cast` built-in itself performs no source/target convertibility
> check at the type-checking layer; `cast(T, x)` yields `T` (Ch.8, Ch.15).

## 7.4 Structs

`type.struct.decl` — A named struct type is declared `type Name struct { … }`.
There is no `struct Name { … }` shorthand; `struct{ … }` is only a type
expression, named through a `type` declaration. A struct has an ordered list of
**fields**, each a `(name, type)` pair; field names and order are significant.
A field may be of any type, including managed types.

`type.struct.value` — A struct is a value type: copied on assignment and
parameter passing, living inline. Only a raw pointer may be taken to a struct
(`&s` → `*T`); a heap-managed struct is reached through `@T` (from `make`).

`type.struct.field-access` — Field access `x.f` looks up `f` by name on the
wrapper-peeled struct base; a named-distinct or alias wrapper and a single
pointer indirection are transparent (§7.3). A field takes precedence over a
same-named method. A `readonly` access path propagates onto the field type, so
a write through a read-only path is rejected (§7.11).

`type.struct.named-nominal` — Named structs are **nominal**: two struct types
are identical iff their package-qualified names match; field shape is irrelevant
once a struct is named. Two distinct named structs with identical fields are not
identical, and a named struct is never identical to an anonymous struct.

`type.struct.anonymous-structural` — An anonymous struct type (`struct{ … }`,
unnamed) uses **structural** equivalence: two anonymous structs are identical
iff they have the same number of fields and, position by position, equal field
*names* and identical field *types*. `type Foo = struct{ x int }` is an alias
for the anonymous type. Anonymous types may not be method receivers (§7.3).

> _Open._ A bare type name written as a struct field (an "embedded" field) is
> currently parsed but stored as an ordinary positional field with no name; no
> field or method **promotion** from embedded fields is provided. Whether Binate
> adopts embedding/promotion semantics is unspecified and not yet decided.

## 7.5 Arrays

`type.array.form` — An array type is `[N]T`, with length `N` and element type
`T`. The length `N` shall be a compile-time-constant non-negative integer (a
negative or non-constant length is rejected). Bare `[]T` is not an array — it is
rejected; raw slices are written `*[]T` (§7.6).

`type.array.value` — Arrays are value types: copied on assignment and parameter
passing, living inline. Only a raw pointer may be taken to an array; a
heap-managed array is `@([N]T)` (§7.8). Two array types are identical iff they
have equal length and identical element types.

`type.array.index-slice` — `arr[i]` yields the element type (`i` an integer).
Sub-slicing an array, `arr[lo:hi]`, yields a **raw slice `*[]T`** (a borrowing
view — an array has no reference-counted backing). Named/alias/`readonly`
wrappers around an array are transparent for both operations.

## 7.6 Raw slices and managed-slices

`type.slice.kinds` — There are exactly two slice kinds, both carrying an element
type: the **raw slice `*[]T`** and the **managed-slice `@[]T`**. They are
distinct types and never unified.

`type.slice.ownership` — A managed-slice `@[]T` **owns** its backing by reference
counting (it keeps the backing allocation alive and needs destruction) and may
refer only to a managed allocation. A raw slice `*[]T` **borrows** — it holds no
count, the caller manages the backing's lifetime, and it needs no destruction.
At an API boundary the kind communicates intent: `@[]T` retains, `*[]T` is
use-now.

`type.slice.make` — `make_slice(T, n)` returns a managed-slice `@[]T` of `n`
zero-initialized elements (`n` an integer). It is the only way to create a
runtime-sized slice; there is no raw-slice constructor (a runtime-sized slice
with no owner would have no defined lifetime).

`type.slice.decay` — A managed-slice is implicitly assignable to a raw slice of
the same element type (`@[]T` → `*[]T`) — a borrow, operationally a copy of the
first two words, with no refcount change. The reverse `*[]T` → `@[]T` is never
implicit (a raw slice has no backing to promote). This is the only implicit
slice-kind conversion. Element types must be identical with no element-level
`readonly` drop (§7.11).

`type.slice.subslice` — Sub-slicing preserves the slice kind: `@[]T[lo:hi]` →
`@[]T`, `*[]T[lo:hi]` → `*[]T` (and an array sub-slice → `*[]T`; §7.5). `lo`/`hi`
are integers. A managed sub-slice shares — and reference-counts — the same
backing; an empty (`lo == hi`) sub-slice is the no-backing empty (§7.7).

`type.slice.readonly-element` — A slice may carry a `readonly` element type
(`*[]readonly char`, `@[]readonly char`). Element-level `readonly` is a
capability: adding it is allowed, dropping it requires a `cast` (§7.11). String
literals have natural type `[N]readonly char` and default type `@[]readonly char`
(Ch.6); their permitted targets are `@[]readonly char`, `@[]char` (allocate +
copy), `*[]readonly char`, and a matching-length char array `[N]readonly char`
or `[N]char` (array copy) — but **not** `*[]char` (a mutable raw view of
read-only static data is unsound). See §6.6 for the authoritative target table.

`type.slice.no-nil-no-compare` — A slice is **not nillable** and **not
comparable**: it cannot be assigned from `nil`, and `==`/`!=` on slices (even
against `nil`) is rejected. Test emptiness with `len(s) == 0` or `present(s)`.
(`nil` is for pointers and function values; §7.7.)

## 7.7 `nil`, empty slices, and the length-0 invariant

`type.nil.literal` — `nil` is a predeclared constant of a distinct nil type,
assignable only to **nillable** types: raw and managed pointers, and function
values (§7.8, §7.9). It is not assignable to slices or interface values.

`type.slice.len0-no-backing` — *(representation invariant)* Every length-0 slice
has **no backing**: its representation is the nil-equivalent — `{null, 0}` for a
raw slice, `{null, 0, null, 0}` for a managed-slice (§7.13). Empty and "nil"
slices are therefore indistinguishable; there is no "empty view of live backing"
state. Every slice-producing operation establishes this (`make_slice(T, 0)`, an
empty sub-slice, and empty/static literals all yield the no-backing empty).
Conversely, a **non-empty** managed-slice may itself have an **unowned** backing —
null, or an immortal sentinel — when it views immortal static read-only data
(a `@[]readonly char` literal), so a null backing does **not** by itself imply an
empty slice. The full owned-vs-unowned backing contract is §7.13.6
(`type.layout.slice-managed.backing`).

> _Note._ This is a **representation** contract enforced when slices are produced
> (in lowering and at run time), not a type-checker rule — the type system
> tracks only the static slice kind. An earlier "empty view pins its backing"
> design was reversed in favor of this rule.

## 7.8 Pointers

`type.ptr.kinds` — There are two pointer constructors, both written as a prefix:
the **managed pointer `@T`** (reference-counted) and the **raw pointer `*T`**
(unmanaged). Both are single-word value types. Copying `@T` is a value copy that
additionally increments the pointee's reference count; copying `*T` is a plain
bit copy with no refcount effect. `@T` needs destruction; `*T` does not.

`type.ptr.semantics` — `@T` is the default, owning reference to a heap-allocated
managed value (it participates in the reference-counting lifecycle; Ch.18). `*T`
is an unmanaged, non-owning **escape hatch** with manual lifetime — used for
breaking reference cycles (a raw pointer to a managed value is an unowned/weak
reference; keeping the pointee alive is the programmer's responsibility),
borrowing, and hot paths.

`type.ptr.address-of` — `&x` takes the address of an lvalue and yields a **raw**
pointer `*T`, always — even when `x` is a managed value. There is no operator
that takes a *managed* address; managed pointers arise only from
`make`/`box`/`make_slice`. `&` of a `const` (which has no storage) is an error.
The `.` operator auto-dereferences a pointer of either kind (there is no `->`).

`type.ptr.managed-to-raw` — `@T` → `*T` is an **implicit** conversion (a managed
pointer decays to a raw pointer to the same pointee — a borrow that owns no
reference). The reverse `*T` → `@T` is never implicit (it would invent a
reference). The same managed→raw decay applies to slices (`@[]T` → `*[]T`; §7.6),
function values (`@func` → `*func`; §7.9), and interface values
(`@Iface` → `*Iface`, same interface; §7.10).

`type.ptr.opaque-byte` — `*uint8` is the **opaque byte pointer**, the analog of
C's `void*`; there is no separate void/opaque pointer type. Reinterpret between
a typed pointer and `*uint8` with `bit_cast` (Ch.15). The interface-value type
`*any` is *not* a `void*` — it is a two-word interface value (§7.10).

`type.ptr.array-parens` — A pointer to an array shall be written with
parentheses — `@([N]T)` or `*([N]T)` — because the bare `@[`/`*[` forms are
reserved for the slice sugar `@[]T`/`*[]T`. Likewise, parentheses disambiguate a
managed pointer to a managed/raw pointer or interface value (e.g. `@(@T)`,
`@(*Iface)`).

> _Note._ Both bare `@[N]T` and bare `*[N]T` (a base after `[` other than `]`)
> are syntax errors requiring the parenthesized form; the parser rejects each
> with a message pointing at the canonical `@([N]T)` / `*([N]T)` spelling.

`type.ptr.nullability` — In v1 all pointers are **nullable**: `nil` is assignable
to any raw or managed pointer type. Non-nullable pointers (a future `!`
annotation) are a *reserved* feature, not part of v1.

> _Note._ The managed-allocation header that backs every `@`-pointee — the
> reference count and free-function words — is specified in
> [§7.13](07b-type-layout.md), `type.layout.header`.

## 7.9 Function types

`type.func.value-spelling` — A function type used as a **value** is written
`*func(params) results` (raw) or `@func(params) results` (managed). A bare
`func(…)` is **not** a usable type expression. Parameter names are not part of a
function-value type (parameters are types only). A trailing `...T` in the
parameter position marks a **variadic** function-value type (§10.3).

`type.func.kinds` — The two function-value kinds — raw `*func(…)` and managed
`@func(…)` — differ only in whether the capture/data pointer is reference-counted
(a managed function value needs destruction). Function-value type identity is
**structural** on the signature: same kind, identical parameter types in order,
identical result types in order, **and identical variadic-ness of the final
parameter** (a variadic `*func(...T)` is never identical to a fixed `*func(*[]T)`;
§10.3 `func.variadic.identity`) — names ignored; the kind is part of identity, so
`*func(int) int` and `@func(int) int` are not identical (their `@func` → `*func`
decay is the managed→raw rule, §7.8).

`type.func.nillable` — Function-value types are **nillable** (a nil function
value is both words zero and a meaningful state). A reference to a named
top-level function or method is assignable to a matching `*func`/`@func` type.
Full semantics of function values and closures are Ch.10.

## 7.10 Interface value types and `any`

`type.iface.value-spelling` — An interface used as a **value** is written
`*Iface` (raw) or `@Iface` (managed) — each a two-word value (§7.13), *not* a
pointer to an interface. The bare interface name `Iface` is not a usable
value-type expression (use `*Iface` or `@Iface`). `@Iface` is reference-counted
(it needs destruction). A pointer *to* an interface value is written with
parentheses where needed (`@(*Iface)`, `@(@Iface)`).

`type.iface.identity` — Interface-value type identity is **nominal**: two
interface-value types are identical iff they wrap the same interface (same
package and name). Cross-package interfaces with the same short name are
distinct.

`type.iface.no-readonly-slot` — There is no inner-`readonly` qualifier on an
interface-value type (no `*readonly Iface`); a whole-type `readonly` wrapper is
layout-transparent (§7.11), and read-only dispatch is expressed through
`readonly` receivers on the impl (Ch.11).

`type.iface.any` — `any` is the single built-in universal (empty) interface,
usable only as `*any` or `@any` (bare `any` is rejected as a value type, except
in generic-constraint position, where it means "no constraint"; Ch.12). `any` is
satisfied by **every** type, with no `impl` required. A *user-declared* empty
interface is a distinct nominal interface that **still** requires an explicit
`impl` to satisfy — Binate interfaces are nominal, not structural, so "zero
methods" does not mean "anything fits". `*any` is a two-word interface value, not
`void*`.

> _Note._ Construction-site and dispatch semantics (how a concrete value becomes
> an interface value, satisfaction, upcasting) are Ch.11; this section states
> only the type-level facts.

## 7.11 The `readonly` modifier

`type.readonly.surface` — `readonly` is a **prefix type modifier** that binds to
the type immediately on its right. It marks the value at the qualified access
path as not writable through that path; it is a property of the **type** (a
capability about modifiability), not of a variable's storage. It is a different
concept and keyword from `const` (the compile-time-constant declaration, Ch.9).

```
readonly *int          // read-only handle, mutable pointee
*readonly int          // mutable handle, read-only pointee
readonly *readonly int // both read-only
*[]readonly char       // raw slice of read-only chars (element-level)
```

`type.readonly.shallow` — `readonly` is **shallow**: it qualifies only the level
it is written on, not nested element types (no deep immutability). It is
**layout-transparent**: `readonly T` has the same size, alignment, and
representation as `T` (§7.13).

`type.readonly.lattice-outer` — Outermost (top-level) `readonly` is permissive in
**both** directions: `T` → `readonly T` (widening) and `readonly T` → `T` (a
value copy — the read-only handle is unaffected). Types differing only in
outermost `readonly` are assignable both ways.

`type.readonly.lattice-element` — `readonly` on an **element** type (behind a
pointer, slice, or array handle) is a **capability**. *Adding* element-level
`readonly` is allowed (`*T` → `*readonly T`, `@[]T` → `@[]readonly T`).
*Dropping* it is rejected (`*readonly T` → `*T`, `@[]readonly T` → `@[]T` require
a `cast`). The managed→raw decay paths carry the same element-`readonly` check.

`type.readonly.object-dispatch` — Method dispatch keys off **object**-readonly,
not handle-readonly. A read-only object (`*readonly Box`, `@(readonly Box)`, or a
`readonly Box` value) may call only methods whose receiver pointee is itself
read-only; a read-only *handle* to a mutable object (`readonly *Box`,
`readonly @Box`) may call any method. Value receivers are always read-only. There
are no const-method annotations — the receiver type is the sole statement of the
mutable-vs-read-only need (Ch.10).

`type.readonly.param-signature` — The outermost `readonly` on a function
**parameter** type is local discipline only (the parameter cannot be reassigned
in the body); it is not part of the function's type signature and is ignored for
signature matching and function-value assignability. Element-level `readonly`
inside a parameter type still matters.

`type.readonly.cast-drops` — `cast(T, x)` yields `T` regardless of the source's
`readonly`-ness — it is the sanctioned way to drop element-level `readonly`
(which implicit assignment rejects), and may combine a `readonly` drop with a
width or pointer-target change. There is no separate `const_cast`.

`type.readonly.vs-const` — `readonly` (type modifier) and `const` (compile-time
constant, Ch.9) are distinct. A `const` has no storage and no address (`&` of it
is an error) and is scalar-only. Immutable **storage** is `var x readonly T = …`,
which *does* have storage and an address (`&x` → `*readonly T`).

## 7.12 Opaque (forward-declared) types

`type.opaque.forward` — `type Foo` — an identifier with no body (`=`, `struct`,
or underlying type expression) and a following statement terminator — is a
**forward declaration**: it declares that `Foo` is a named type without
specifying its layout. Placed in a package's `.bni` interface file with the full
definition (`type Foo struct { … }`) in the package's `.bn`, it exports `Foo`
**opaquely** (Ch.16). The bare-identifier-then-terminator shape is the syntax;
`type Foo U` (a type expression follows) is instead the distinct-type form
(§7.3).

`type.opaque.handles` — The pointer and handle types over an opaque type — `*Foo`
and `@Foo` — are first-class: declared, passed, returned, assigned, and
dispatched on. A `.bni` may declare methods on a forward-declared type (with
pointer or managed-handle receivers). This is how callers operate on an opaque
value: through its exported functions and methods. (Use `@Foo` and `make` for
opaque handles; `*Foo` returning the address of a local is a raw-pointer lifetime
error.)

`type.opaque.field-rejection` — Direct field access on a value of opaque type is
**rejected** ("cannot access field on this type"), even where the field exists in
the defining package — the cross-package encapsulation guarantee. (A
named-distinct type with a *concrete* underlying struct is peeled and its fields
*are* reachable; §7.3. The distinction is whether the underlying is visible.)

`type.opaque.single-source` _(Constraint)_ — A type is declared **full** at most
once per package. The valid forms are: a full `type S struct{ … }` in the `.bni`
(transparent — fields visible everywhere); a forward `type S` in the `.bni` plus
the full body in one `.bn` (opaque export); or a full definition only in a `.bn`
(package-private). A full definition in **both** the `.bni` and a `.bn`, or two
full definitions across `.bn` files, is rejected ("duplicate type definition";
the `.bni`/`.bn` case reports "declared in full in both the .bni and a .bn").
Generics are included. A repeated forward declaration is idempotent.

`type.opaque.builtin-rejection` _(Constraint)_ — `make`, `make_slice`, `sizeof`,
and `alignof` on an opaque type are rejected (its layout is unknown), alongside
the field-access restriction above; the gate peels named-distinct, alias, and
`readonly` wrappers, so a distinct type over an opaque type is rejected too. See
§15.2 (`builtin.opaque-gate`). Opaque export is for non-generic types only in
this version.

## 7.13 Type Layout and Representation

The memory layout of every type — sizes, alignment, field offsets, and the
exact word layout of slices, the managed-allocation header, interface values,
and function values — is the cross-mode ABI contract and is specified in its own
section: **[§7.13 Type Layout & Representation](07b-type-layout.md)**.
