# 15. Built-in Operations

> **Status:** mixed · **Maturity:** mostly Stable (the VM `panic` no-op is flagged; `print`/`println` formatting is provisional)  
> **Rule-ID prefix:** `builtin`

A **built-in operation** is invoked with call syntax but is not an ordinary
function. There are two kinds:

- The eleven **keyword-builtins** (§15.1) — reserved keywords with special
  syntax, several of which take a **type** as an argument (which an ordinary call
  cannot supply). Being keywords, they are **reserved** and cannot be shadowed.
- Three **predeclared functions** — `print`, `println`, `panic` (§15.7) — which
  are ordinary universe-scope identifiers (variadic, checked specially), and
  therefore *can* be shadowed.

Several built-ins are specified in full elsewhere and only summarized here:
`cast`/`bit_cast` conversion semantics in Ch.8, `sizeof`/`alignof` layout in
§7.13, and `unsafe_index`'s relationship to checked indexing in §13. The
reference-counting effects of the allocating built-ins are §18.

## 15.1 The keyword-builtins

`builtin.keywords` — The keyword-builtins are:

```
BuiltinCall = "make" "(" Type ")"
            | "make_slice" "(" Type "," Expression ")"
            | "box" "(" Expression ")"
            | "cast" "(" Type "," Expression ")"
            | "bit_cast" "(" Type "," Expression ")"
            | "len" "(" Expression ")"
            | "unsafe_index" "(" Expression "," Expression ")"
            | "sizeof" "(" Type ")"
            | "alignof" "(" Type ")"
            | "present" "(" Expression ")"
            | "same" "(" Expression "," Expression ")" ;
```

`builtin.reserved` — Each of these eleven names is a **reserved keyword**: it
always lexes as the built-in, so a program cannot declare a variable, function,
or type with that name. (Contrast the predeclared functions of §15.7, which are
ordinary identifiers and may be shadowed.) A built-in that takes a **type**
argument (`make`, `make_slice`, `cast`, `bit_cast`, `sizeof`, `alignof`) parses
that argument as a type, not an expression; this is the reason these cannot be
ordinary functions.

`builtin.result-types` — The result type of each built-in:

| Built-in | Argument shape | Result |
|----------|----------------|--------|
| `make(T)` | a type | `@T` |
| `make_slice(T, n)` | element type + integer size | `@[]T` |
| `box(v)` | a value | `@T` (T = default type of `v`) |
| `cast(T, e)` | a type + a value | `T` |
| `bit_cast(T, e)` | a type + a value | `T` |
| `len(e)` | a value | `int` (signed) |
| `unsafe_index(c, i)` | a value + an integer | the element type of `c` |
| `sizeof(T)` | a type | `uint` (unsigned) |
| `alignof(T)` | a type | `uint` (unsigned) |
| `present(x)` | a value | `bool` |
| `same(a, b)` | two values | `bool` |

## 15.2 Allocation: `make`, `make_slice`, `box`

`builtin.make` — `make(T)` allocates a fresh managed `T` and returns `@T`. The
allocation is **zero-initialized** (every field/element is the zero value; there
are no constructors) and its reference count is **1**. `T` may be **any** type:
`make(Point)` → `@Point`; `make([100]int)` → `@([100]int)` (a managed pointer to
a fixed-size array); `make(*[]int)` → `@(*[]int)` (a managed pointer to a
zero-value raw slice — **not** a managed-slice). There is no size argument
(`make_slice` is the runtime-sized allocator).

`builtin.make-slice` — `make_slice(T, n)` allocates a fresh, runtime-sized
**managed-slice** of `n` elements and returns `@[]T`. The size `n` is an integer
value; the elements are zero-initialized; the result is the canonical 4-word
managed-slice `{data, len, backing, backingLen}` with `len == n` and its backing
at reference count 1. This is the **only** way to create a runtime-sized
managed-slice; there is no capacity argument (growth is a library concern). Two
boundary rules:

- `make_slice(T, 0)` produces the **no-backing** empty slice — the canonical
  `{nil, 0, nil, 0}` (the length-0 ⟹ no-backing invariant, §7.7); `present` of it
  is false (§15.5).
- A **negative** `n` is a defined **runtime trap** ("runtime error: make_slice
  with negative length"), not a silently nil-backed negative-length slice (§17).

`builtin.box` — `box(v)` allocates a fresh managed copy of the value `v` and
returns `@T`, where `T` is the default type of `v` (an untyped literal is
materialized first: `box(42)` → `@int`). The new allocation holds a byte copy of
`v` at reference count 1. `box` is the sanctioned way to move a value onto the
managed heap — in particular to obtain the `@T` required before constructing an
interface value `@Iface` from it (Ch.11); there is no implicit boxing.

`make`, `make_slice`, and `box` each produce a fresh managed value that, if not
bound to an owning location, is released at the end of the statement (§18).

`builtin.opaque-gate` _(Constraint)_ — `make(Opaque)`, `make_slice(Opaque, n)`,
`sizeof(Opaque)`, and `alignof(Opaque)` are **rejected** for an opaque type
whose layout is not available (a pure forward declaration, or an opaque export
seen only through its `.bni`; §7.12), since each needs the layout. The gate
peels `readonly`, alias, and named-distinct wrappers, so a distinct type *over*
an opaque type (`type Handle Opaque`) is gated the same way; a distinct type
over a *concrete* underlying stays allowed. The diagnostics are "cannot make a
value of an opaque type", "cannot make_slice with an opaque element type", and
"cannot take sizeof/alignof of an opaque type".

## 15.3 Conversion: `cast`, `bit_cast`

`builtin.cast` — `cast(T, e)` converts the value `e` to type `T` and yields `T`.
The conversion semantics — integer wrap/truncate and sign/zero extension,
float↔int (with the saturating float→int contract), and the `readonly` drop —
are specified in Ch.8 (`conv.cast`). At the type-checking layer a `cast` of a
*non-constant* operand is **unchecked** (the checker returns `T` without
validating convertibility); a **constant** operand is fit-checked against `T` and
is not laundered (§8.5 `conv.cast.const-not-laundered`).

`builtin.bit-cast` — `bit_cast(T, e)` reinterprets the bits of `e` as type `T`
with **no** value conversion, yielding `T` — the "I know what I am doing" escape
hatch (§8.6). It is the sanctioned tool for moving between a typed pointer and
the opaque byte pointer `*uint8`, and between scalar bit patterns of the same
width. Like `cast`, it is unchecked at the type layer; reinterpreting between
different sizes, or in a way that violates a type's invariants, is undefined
(Ch.21).

> _Implementation note._ `cast` to a **sub-word integer** type is currently
> miscompiled on the **native aarch64** backend (the result is not narrowed /
> sign-extended to the type width); it is correct on the prebuilt builder, the
> LLVM backend, and the bytecode VM. This is an implementation defect, not a
> change to the intended truncation/extension semantics (`claude-todo.md`,
> `aa64-subword`).

## 15.4 Size and length: `len`, `sizeof`, `alignof`

`builtin.len` — `len(e)` is the number of elements of a **slice**, **managed-slice**,
or **array** (a named type whose underlying is one of these is accepted; the
wrapper is peeled). A string literal — whose natural type is the array
`[N]readonly char` (§6.6) — is accepted, yielding its decoded byte length. The
result is a **signed `int`**. For an array or string literal the value is a
compile-time constant; for a slice it is a run-time read of the length word.
`len(s) == 0` is the sanctioned emptiness test for slices, which are not
comparable to `nil` (§13).

`builtin.sizeof` — `sizeof(T)` is the size of type `T` in bytes; `alignof(T)`
(`builtin.alignof`) is its alignment in bytes. Both take a **type**, yield an
**unsigned `uint`**, and are **compile-time constants**. The size/alignment is
that of the **value itself**, not of any data it points to (`sizeof(*[]int)` is
two words — the raw-slice header — not the backing). Both are
**target-parameterized**: the constant depends on the compilation target's
pointer and integer widths (§7.13), so e.g. `sizeof(*T)` is 8 on a 64-bit target
and 4 on a 32-bit target. (The opaque-type gate noted in §15.2 applies to
`sizeof`/`alignof` as well.)

## 15.5 Reference tests: `present`, `same`

These two built-ins answer the questions `==`/`!=` would mislead about on the
multi-word reference types (slices, interface values, function values), where
those operators are disallowed (§13): `present` answers "is it set?" and `same`
answers "is it *this* one?". Their accepted operand sets differ slightly (`same`
excludes function values) — see each rule below.

`builtin.present` — `present(x)` is `true` iff `x` is **set**. It is defined on
the nullable reference/view types: an **interface value** (its vtable word is
set), a **function value** (its vtable word is set), a **pointer** (non-null), or
a **slice** (length > 0). Value types — scalars, structs, arrays — are **rejected**
(they are never unset). The result is `bool`. `present` is the sanctioned
emptiness/"is-set" test where `== nil` is a footgun or disallowed.

> _Note._ For an interface value, `present` is honest about typed-nil: boxing a
> nil pointer into an interface value still fills the vtable word, so
> `present(iv)` is `true` even though the boxed pointer is nil. The only emptiness
> an interface value has is "the slot was never filled".

`builtin.same` — `same(a, b)` is `true` iff `a` and `b` denote the **same
referent**. Both operands must have the **same static type**, and that type must
be a **pointer**, an **interface value**, or a **slice** — function values
(which have no canonical identity) and value types are **excluded**. Identity is:
the same address (pointers); the same `{data, vtable}` pair (interface values,
both words — so two typed-nil values of different concrete types are correctly
*not* the same); or the same `{data, len}` view (slices). The result is `bool`.
`same` is the sanctioned identity test — e.g. sentinel detection ("is this error
the `io.EOF` object?").

> _Note._ For a managed-slice, `same` compares the `{data, len}` view only, not
> the backing — two subviews with identical data pointer and length compare the
> same regardless of backing. Under the length-0 ⟹ no-backing invariant, all
> empty slices are the canonical `{nil, 0}` and are therefore mutually `same`.

## 15.6 Unchecked access: `unsafe_index`

`builtin.unsafe-index` — `unsafe_index(c, i)` accesses element `i` of `c` — a
**slice**, **array**, or **raw pointer** — by an integer index, yielding the
element type. It is exactly `c[i]` **without the bounds check** (§13): the same
element address computation, but no trap on an out-of-range index. It is the
opt-out from always-on bounds checking for performance-critical code; an
out-of-range index is **undefined** (Ch.21), not a trap. (Unlike `len`,
`unsafe_index` accepts a raw pointer; also unlike `len`, it does not peel a
named-distinct collection type — only an alias.)

## 15.7 Predeclared functions: `print`, `println`, `panic`

`builtin.predeclared` — `print`, `println`, and `panic` are **predeclared
functions** in the universe scope, not keyword-builtins: they lex as ordinary
identifiers and may be **shadowed** by an in-scope binding. They are variadic and
checked specially (each argument is type-checked, but there is no fixed parameter
signature). All three yield no value.

`builtin.print` — `print(args…)` writes its arguments to standard output;
`println(args…)` does the same followed by a newline. Multiple arguments are
separated by a single space. Each argument is formatted by its type (integers in
decimal, `bool` as `true`/`false`, a char slice/array as its bytes, floats in a
fixed-point form).

> _Provisional._ `print`/`println` are a **transitional** facility. Their
> per-type formatting (and the float format in particular) is bootstrap-grade,
> deliberately not `%g`-compatible, and is implemented over temporary scaffolding;
> the intended long-term path is per-type `Format(self) @[]char` rendering
> dispatched through an interface, gated on interfaces/generics. The exact output
> format is therefore **not** a stable normative guarantee (§20, `claude-todo.md`).

`builtin.panic` — `panic(msg)` **aborts the program unrecoverably** with the
diagnostic `msg` — a non-recoverable abort in the same family as the defined
runtime traps (Ch.21). Binate has **no recoverable `panic`/`recover`**: errors
are values (§14.14), and `panic` is reserved for "this must never happen" aborts.
A `panic(…)` expression statement is a control-flow **terminator** for the
missing-return analysis (§14.13).

> _Open (MAJOR — dual-mode divergence)._ `panic` is currently a **no-op in the
> bytecode VM**: the interpreter lowers it to nothing and silently continues
> (discarding the message), whereas the compiled backends abort. So a `panic`
> does not yet behave identically across execution modes, contrary to the
> dual-mode contract (§19); its abort semantics are realized only in compiled
> mode (`builtin.panic.vm-noop`, `claude-todo.md`).

## 15.8 Other built-ins

`builtin.internal` — The implementation reserves further built-in keywords that
are **compiler-internal / low-level** and not part of the everyday surface:
`unsafe_div` and `unsafe_rem` (the guard-free counterparts of `/` and `%`, which
skip the divide-by-zero and signed-`MIN`/`-1` faults of §13.4); `unsafe_shl` and
`unsafe_shr` (the guard-free counterparts of `<<` and `>>`, which skip the
negative-count and overshift handling of §13.5 — the caller asserts the count is
in `[0, width)`); and the foreign-function / introspection primitives used by the
runtime and tooling. They follow the same keyword-builtin reservation rules.

`builtin.proposed` — `move(x)` (explicit ownership transfer that nils the source)
and `ispod(T)` (a compile-time predicate: may `T` be copied by raw `memcpy` and
discarded with a no-op destructor?) are **proposed**, not implemented; they will
be catalogued in Annex D once authored, and are not part of the normative
built-in set above.
