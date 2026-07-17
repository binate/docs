# 7.13 Type Layout and Representation

> **Status:** normative · **Maturity:** Stable (the cross-mode ABI contract)  
> **Rule-ID prefix:** `type.layout`  
> Part of Ch.7 ([Types](07-types.md)).

This section defines the in-memory **layout** of every type: sizes, alignment,
field offsets, and the exact word layout of slices, the managed-allocation
header, interface values, and function values. Layout is the **cross-mode ABI
contract**: compiled and interpreted execution share one heap and call each
other through function pointers, so they **shall** use byte-identical layout
(§7.13 `type.layout.keystone`). It is defined once, parameterized by the target
(`type.layout.target-info`), and used by every compiler backend, the
interpreter, and the runtime.

## Latitude

Each layout fact is classified (§3.1):

- **target-invariant** — fixed on every target: the composite **word counts**
  and **field orders** below, the struct padding/alignment **algorithm**, the
  rule that a managed-slice's first two words equal a raw slice, and the
  >16-byte by-value parameter cutoff.
- **target-parameterized** — a function of `TargetInfo`: every absolute byte
  size, offset, and alignment (all derive from `PointerSize`/`IntSize`/`MaxAlign`).
- **implementation-defined** — **byte order (endianness)**
  (`type.layout.byte-order`): fixed and documented per target, identical across
  modes. Currently little-endian on every target; `TargetInfo` carries no
  endianness field yet.
- **backend-private** — concrete type-representation spellings (e.g. LLVM
  `i8*`/`%Struct`), instruction selection, register allocation, calling-convention
  register choices, and binary/debug formats (Annex B).

## 7.13.1 The target description

`type.layout.target-info` — Layout is parameterized by a target description:

```
TargetInfo {
    PointerSize int    // bytes per pointer: 4 (32-bit) or 8 (64-bit)
    IntSize     int    // bytes per `int`/`uint`; equals PointerSize
    MaxAlign    int    // caps scalar alignment; typically == PointerSize
}
```

`SizeOf`, `AlignOf`, `FieldOffset`, and the struct-layout computation are
defined once over this description (the single authoritative layout used by every
backend, the bytecode interpreter, and the runtime). Below, `W` denotes `PointerSize` (the word size; `IntSize == W`).

## 7.13.2 Scalars

`type.layout.scalar` — Scalar sizes (bytes): `bool` = 1; `int`/`uint` = `W`
(target word size); `int8`/`uint8`/`char`/`byte` = 1, `int16`/`uint16` = 2,
`int32`/`uint32` = 4, `int64`/`uint64` = 8; `float32` = 4, `float64` = 8. A
scalar's natural alignment equals its size, **clamped to `MaxAlign`**. Thus on a
32-bit target with `MaxAlign` = 4, `int64` and `float64` are 8 bytes but align to
4. (`int`/`uint` align to `W`.)

## 7.13.3 Structs

`type.layout.struct` — A struct's fields are laid out in declaration order. Each
field is placed at the lowest offset, at or above the running offset, that meets
the field's alignment (inserting padding before it as needed). The struct's
alignment is the maximum field alignment (minimum 1). The struct's size is the
offset past the last field, rounded up to the struct's alignment (trailing
padding). An empty struct (no fields) has size 0. The field **order** and this
**algorithm** are target-invariant; the resulting byte offsets and sizes are
target-parameterized.

## 7.13.4 Arrays

`type.layout.array` — An array `[N]T` occupies exactly `N × SizeOf(T)` contiguous
bytes at stride `SizeOf(T)` (no inter-element padding); its alignment is `T`'s
alignment. A zero-length array has size 0. Contiguity and the stride
(`= SizeOf(elem)`) are target-invariant.

## 7.13.5 Raw slices

`type.layout.slice-raw` — A raw slice `*[]T` is **always 2 words**:

| Offset | Word | Field |
|--------|------|-------|
| `0` | 0 | `data` — raw pointer to the first element of the view |
| `W` | 1 | `len` — element count (target `int`) |

Size `2W`, alignment `W`. The `nil`/empty raw slice is `{null, 0}`.

## 7.13.6 Managed-slices

`type.layout.slice-managed` — A managed-slice `@[]T` is **always 4 words**:

| Offset | Word | Field |
|--------|------|-------|
| `0` | 0 | `data` — raw pointer to the **view** start |
| `W` | 1 | `len` — element count of the view (target `int`) |
| `2W` | 2 | `backing` — managed pointer to the backing allocation **start** (reference-counted; may differ from `data` after sub-slicing) |
| `3W` | 3 | `backingLen` — total backing element count (for destructor iteration) |

Size `4W`, alignment `W`. The **first two words are byte-identical** to a raw
slice — which is what makes the `@[]T` → `*[]T` decay (§7.6) a field extraction.
A length-0 managed-slice has no backing: `{null, 0, null, 0}` (§7.7).

`type.layout.slice-managed.backing` — The `backing` word records whether the
slice **owns** a reference-counted allocation. The backing is **owned** — its
`RefDec` frees it when the count reaches 0, running the element destructor across
`backingLen` (§18.2) — **iff** `backing` is **non-null** *and* the allocation's
reference count is a normal **positive** value. It is **unowned / immortal** —
`RefInc`/`RefDec` are no-ops and it is never freed — in either of two forms:

- **`backing == null`** (no managed header): the slice is either empty
  (`{null, 0, null, 0}`, §7.7) **or** a non-owning **view of effectively-immortal
  storage** — storage that outlives **every reference** to the slice — with a
  non-null `data`. The operational contract is purely lifetime-based: an unowned
  backing makes `RefInc`/`RefDec` no-ops and is never freed (§18.2 `mem.immortal`),
  and it does **not** require the storage to be static, read-only, or in a program
  image. Immortal static read-only data — a compiled `@[]readonly char` literal
  (the environment-lifetime note below) — is the **canonical example, not the
  definition**: the same mechanism represents any effectively-immortal storage, and
  on a target with no read-only-data section it is how such data is held at all.
  Soundness rests on the borrow discipline (§18.1 `mem.managed-vs-raw`, §18.7
  `mem.raw-uaf`): a null backing is a borrow carried in a managed slice's owning
  slot, so — the reference-count machinery being inert — the **producer** must
  guarantee the referent outlives every reference, exactly as for a raw borrow.
- **`backing != null` carrying the immortal sentinel**: the backing is a
  **static-managed** allocation whose `{refcount, free_fn}` header (§7.13.7) holds
  the deeply-negative `STATIC_REFCOUNT` sentinel, so the refcount operations
  short-circuit on the negative count (§18.2 `mem.immortal`).

Consequently a **null backing does not imply an empty slice** (a non-empty view of
effectively-immortal storage also has an unowned backing), and an unowned backing
may be **null *or* a sentinel allocation**. Because an unowned backing's `RefDec`
never reaches 0, its element destructor never runs — so any **managed** elements
held by such a backing must themselves be immortal.

> _Environment-lifetime of a `@[]readonly char` literal._ A `@[]readonly char`
> string/char-slice literal lives **at least as long as its environment**, and its
> `backing` form realizes that lifetime — which **differs by execution mode**. This
> is an accepted mode-specific realization, **not** marshalling or a layout
> divergence (§19.3 `exec.contract.layout`): the 4-word layout and the
> reference-counting mechanism (§18) are identical in both modes, and the value is
> self-describing (its own `backing` + refcount govern `RefInc`/`RefDec`).
>
> - **Compiled** — the environment is the program image, so the literal is
>   **immortal**: `{data, len, null, len}` (a null-backing view of immortal static
>   read-only data; `data` non-null, `backingLen == len`).
> - **Interpreted** — the environment is the **VM instance**, which **interns** the
>   literal and **holds a reference** to it. The backing is therefore a normal
>   **owned** allocation (non-null, positive refcount, `backingLen == len`): the
>   literal is created once and lives at least as long as the VM, independent of any
>   user reference.
>
> **Exchanging** a **managed** reference to such a literal **across environments**
> is safe (the holder's refcount keeps it alive) — including between distinct VM
> instances, possibly routed through compiled code. The one unsafe case is a **raw**
> `*[]readonly char` borrow retained **outside its originating environment** — e.g.
> past the VM instance's teardown — which is ordinary borrow-misuse (Ch.21), not a
> defined cross-mode guarantee.

## 7.13.7 The managed-allocation header

`type.layout.header` — Every managed allocation is prefixed by a **2-word header
at a negative offset** from the payload pointer:

| Offset | Field |
|--------|-------|
| `-2W` | `refcount` — the reference count |
| `-W` | `free_fn` — the deallocation function (allocator-chosen) |

Header size `2W` (16 bytes on a 64-bit target, 8 on a 32-bit target). There is
**no destructor pointer** in the header: a value's destructor is statically
known per type and is supplied at each `RefDec` site, not stored with the object
(interface/closure drop information lives in the relevant vtable; Ch.18).
`free_fn` is the deallocation step, distinct from the destructor (the per-type
destructor logic; Ch.18).

`type.layout.immortal` — Static (immortal) managed data carries a reserved
**sentinel** reference count (a deeply negative value); `RefInc`/`RefDec`
short-circuit on a negative count, so immortal data is never freed (Ch.18). This
lets static data be referred to through managed pointers without ever being
destroyed.

## 7.13.8 Interface values

`type.layout.iface-value` — An interface value (raw `*Iface` or managed `@Iface`)
is **always 2 words**:

| Offset | Word | Field |
|--------|------|-------|
| `0` | 0 | `data` — the held value / managed pointer (the managed form reference-counts it) |
| `W` | 1 | `vtable` — the dispatch table |

Size `2W`, alignment `W`. The vtable begins with an offset-0 **"any-block"** — the
block every interface vtable shares (the fixed-offset upcast target, §11.6) —
holding the destructor handle (the "dtor-first" convention) and a **`*TypeInfo`**
pointer to the concrete type's RTTI record (§7.13.14); methods follow (Ch.11,
Annex B). The `*TypeInfo` is what a **type assertion** reads to recover the
dynamic type (§11.12 `iface.rtti`). Every **nested** sub-vtable (a parent's block
inside a descendant's vtable, §11.6) carries the **same concrete-leaf-type**
`*TypeInfo` and destructor — the any-block identifies the value's *dynamic
(concrete)* type, not the interface the sub-vtable dispatches — so an assertion or
type switch recovers the concrete type however far the value has been upcast.

## 7.13.9 Function values

`type.layout.func-value` — A function value (raw `*func` or managed `@func`) is
**always 2 words**, but in the **opposite field order** to an interface value:

| Offset | Word | Field |
|--------|------|-------|
| `0` | 0 | `vtable` — `{dtor, call}` (slot 0 destructor, null for a non-capturing value; slot 1 the callable shim) |
| `W` | 1 | `data` — capture/context pointer (the managed form reference-counts it; `null` for a non-capturing value) |

Size `2W`, alignment `W`. This `{vtable, data}` order is the **reverse** of the
interface value's `{data, vtable}` — a deliberate ABI asymmetry that every mode
must observe.

> _Note (ABI hardening — implementation)._ This field order, and the interface
> value's, are currently encoded as fixed indices in the IR-gen and backends
> rather than as named offset helpers in the shared layout layer (unlike the
> slice and header offsets). Compiled and interpreted modes agree by convention;
> hardening the orders into shared helpers is a tracked follow-up
> (`type.layout.funcval-order-hardening`, `claude-todo.md`). The orders stated
> here are the normative contract regardless.

> _Note._ A function-value vtable carries **no** `*TypeInfo`: function values are
> not type-asserted (only interface values are; §11.12). RTTI lives only in
> interface vtables (§7.13.8, §7.13.14).

## 7.13.10 Transparent wrappers

`type.layout.transparent` — `readonly T`, an alias of `T`, and a named-distinct
type over `T` are **layout-identical** to `T`: same size, alignment, and field
offsets. `SizeOf` and `AlignOf` peel all three wrappers; `FieldOffset` peels only
aliases, so a caller passing a `readonly`- or named-wrapped struct type must strip
it to the concrete struct first. They introduce no representation change (§7.3,
§7.11).

## 7.13.11 Aggregate parameter passing

`type.layout.byval-cutoff` — An aggregate value (struct, array, slice,
managed-slice, function value, or interface value) passed as a parameter is
passed **by value when its size is ≤ 16 bytes** and **by indirect reference when
its size exceeds 16 bytes** (measured with the target-aware `SizeOf`, after
peeling transparent wrappers). The 16-byte threshold is target-invariant (it
matches the common 64-bit calling conventions); the measured size is
target-parameterized. This is a single layout fact that IR-gen and every backend
must agree on.

## 7.13.12 Byte order

`type.layout.byte-order` — The byte order (endianness) of multi-byte scalars is
**implementation-defined** (§21.4 `behavior.impl-defined`): an implementation
**shall** fix and document a single byte order per target, and — where both modes
exist — its compiled and interpreted modes **shall agree** on that order
(§7.13.13 `type.layout.keystone`). Byte order is observable through `bit_cast` and
the representation-introspection built-ins (Ch.15), so a per-target choice that
disagreed across modes would be a conformance violation.

The current implementation fixes byte order as **little-endian** on every target,
and `TargetInfo` (§7.13.1 `type.layout.target-info`) carries **no** endianness
field. A complete, target-parameterized layout description (needed to describe a
big-endian or cross-endian target) requires adding an endianness field to
`TargetInfo`; doing so — and adding big-endian support — is a tracked
implementation follow-up (`claude-todo.md`), not yet done.

## 7.13.13 The cross-mode agreement requirement

`type.layout.keystone` — *(normative; the master ABI invariant)* A conforming
implementation's compiled and interpreted modes **shall** use byte-identical
layout for every type on a given target — every word count, field order, size,
offset, alignment, the header layout, and the by-value cutoff above. Because
compiled and interpreted code share one heap and pass values across the mode
boundary without marshalling (Ch.19), any divergence silently corrupts data.
High-level slice and array operations lower to primitive load/offset sequences
that **encode** this layout (data pointer = word 0, length = word 1, element
stride = `SizeOf(elem)`), so a backend cannot independently choose a different
representation. This requirement is the reason layout is a language-level
contract rather than a backend decision (Ch.2, Annex B). It applies equally to the
type-information record below (§7.13.14), which is likewise shared across modes.

## 7.13.14 Type-information (RTTI) record

`type.layout.typeinfo` — Each concrete type that can appear as the dynamic type of
an interface value has one static **`TypeInfo`** record, referenced by the
`*TypeInfo` pointer in every interface vtable's any-block (§7.13.8). It is the
substrate for **type assertions and type switches** (§11.12 `iface.rtti`) and, as
a later phase, for the reflection type-metadata surface (§20.3). A `TypeInfo`
carries:

| Field | Meaning |
|-------|---------|
| identity | a per-type token; a concrete assertion tests **equality** of the scrutinee's and target's `TypeInfo` (pointer-equality *within* a mode) — the equality *result*, not any particular address, is what is observable |
| destructor | the type's destructor handle (the same one the vtable any-block holds) |
| size, align | `SizeOf`/`AlignOf` of the type (the target's values) |
| name | the type's name, as a `*[]readonly char` into static storage |

There is **exactly one** `TypeInfo` per type **program-wide** (not per module) so
that the **result** of an identity comparison **agrees across compiled and
interpreted execution** — the record is part of the cross-mode agreement contract
(§7.13.13 `type.layout.keystone`; `conf.cross-mode.scope`, §2.4). Each engine may
use its own native `TypeInfo` for a type and compare by pointer-equality *within*
its mode (the same self-describing-handle model as vtable and function-value
handles, §19.4); it is the boolean *result* that must coincide, not a shared
address. The record's exact field order is **informative** (Annex B); normative are
its contents and the cross-mode agreement of every assertion result. Interface
**satisfaction** is *not* carried in `TypeInfo` — see `type.layout.satisfaction`.

> _Note (name-less types)._ A type with **no nominal identity** — a slice, or any
> other unnamed composite (unnamed struct / array / function type) — can still be
> **boxed** into `any` (`conv.assignable` case 7), so it too needs a well-formed
> any-block. Boxing a name-less type produces a **valid** `TypeInfo` (not a
> half-built box), and a concrete assertion over it is a **guaranteed miss** that
> falls to `default`, never a crash. The baseline gives every name-less type **one
> shared opaque** `TypeInfo` — sound because no assertion target can name such a
> type (§11.12 `iface.assert`), so its identity is never compared against a written
> target. _(The current toolchain does **not** yet conform: boxing a slice into
> `any` emits a malformed box and a match over it crashes — a tracked MAJOR, Annex
> C / `claude-todo.md`.)_
>
> _Draft — ratified, not yet implemented (`proposal-slice-type-identity`)._ The
> slice-target extension (§11.12 `iface.assert.slice`) upgrades **slices** from the
> shared opaque record to a **distinct structural** `TypeInfo` per slice spelling —
> keyed on `{ managed | raw, element-readonly?, element-type }`, so `@[]char` and
> `*[]int` compare unequal. The unnamed struct / array / function constructors keep
> the shared opaque record until (if ever) they gain their own structural identity.
> The record **layout is unchanged** either way: a slice's `name` field is its
> structural spelling, its destructor the slice's element-drop.

`type.layout.satisfaction` — Interface **satisfaction** (which interfaces a type
implements) is resolved through a **distributed registry** keyed on
`(concrete type, interface)`, **not** a table inside `TypeInfo`. Because `impl`
declarations may live in **any** package (no orphan rule, §11.8
`iface.crosspkg.no-orphan`), no single translation unit — not even the type's
defining package — sees a type's **complete** impl set, so a per-type satisfaction
table cannot be built. Instead **each `impl T : I` site** emits a satisfaction
entry for `I` **and every transitive ancestor of `I`** (computable there from `I`'s
extension declaration, §11.6), mapping `(T, K)` to the corresponding sub-vtable
`vtable(T, K)`; entries are `weak_odr`-deduplicated exactly like the `(T, I)`
vtables they reference. An **interface** assertion `x.(K J)` looks up
`(dynamic-type, J)` in this registry and, on a hit, forms `{data, vtable(T, J)}`
(§11.12 `iface.rtti`). The registry's search structure is **informative** (Annex B);
normative is that its lookup **result agrees across modes** (§2.4) and covers
exactly the satisfaction relation (`iface.impl.nominal` + `iface.extend.transitive`).
