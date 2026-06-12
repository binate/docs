# 3. Terms and Definitions

> **Status:** normative · **Maturity:** mostly Stable (grows with the spec)  
> **Rule-ID prefix:** `term`

This chapter defines the technical terms used normatively throughout this
specification. A definition given here is **binding**, but it is deliberately
brief: the full rules for each concept live in the cited chapter, which is the
term's normative home. Terms are written in **bold** with a stable anchor of
the form `term.<name>` for cross-reference (§4.5). A term's stability follows
its home chapter.

Where everyday words (such as *type*, *value*, *expression*, *statement*,
*declaration*, *scope*, *package*) are used with their ordinary
programming-language meaning, they are not redefined here; their precise
rules appear in the relevant chapters.

## 3.1 Behavior and the latitude classification

Every behavior this specification describes falls into one of the following
classes. The classification is what the **Conformance** chapter (Ch.2) and the
behavior catalogue (Ch.21) are built on.

`term.target-invariant` — **target-invariant behavior** is behavior the
language fixes identically on every target (for example: two's-complement
integer wraparound; a managed-slice occupies exactly four words). A conforming
implementation shall produce it on all targets.

`term.target-parameterized` — **target-parameterized behavior** is behavior the
language fixes as a function of the **target** (via `TargetInfo`, `term.targetinfo`):
for example the size of `int`, the size of a pointer, and alignment. It is not
a free choice — an implementation shall use the target's values — and an
implementation's compiled and interpreted modes shall agree on a given target
(Ch.2).

`term.implementation-defined` — **implementation-defined behavior** is behavior
the standard permits to vary between conforming implementations, where each
implementation **shall document** its choice, and (where both modes exist) its
compiled and interpreted modes shall agree on a given target. Example
candidates: byte order, the text of a runtime-panic message.

`term.unspecified` — **unspecified behavior** is behavior the standard permits
to vary, within stated bounds, and does **not** require an implementation to
document (for example, the evaluation order of operands where it is not pinned;
the contents of struct padding bytes).

`term.undefined` — **undefined behavior** is behavior for which this
specification imposes **no requirements**. It is the escape-hatch region
entered only through the unsafe facilities (raw pointers, `bit_cast`,
`unsafe_*`) or by violating a stated invariant; reaching it is programmer
error, and an implementation is not required to diagnose or trap it (Ch.21).

`term.backend-private` — **backend-private behavior** is an implementation
choice with no effect observable by a conforming program (for example
instruction selection, register allocation, calling-convention internals, and
object-file format). It is described, where useful, only informatively
(Annex B).

## 3.2 Memory-model terms

The full model is Ch.18.

`term.managed-allocation` — a **managed allocation** is a heap object whose
lifetime is governed by reference counting. It carries a **management header**
(`term.header`) holding its reference count.

`term.refcount` — the **reference count** (refcount) of a managed allocation is
the number of live references that own a count on it. After `make(T)` the
refcount is 1; while any owning reference is live the refcount is positive;
when it reaches 0 the allocation is destroyed.

`term.managed-pointer` — a **managed pointer** `@T` is a reference to a managed
allocation of type `T`. It is itself a value (§3.3): copying a managed pointer
is a *copy* (`term.copy`) and adjusts the pointee's refcount.

`term.raw-pointer` — a **raw pointer** `*T` is an unmanaged reference to a `T`.
Copying it does not affect any refcount; it is the escape hatch used for
borrowing, cycles, and hot paths, and dereferencing a dangling raw pointer is
undefined (Ch.21).

`term.copy` — a **copy** of a managed value (or a value containing managed
fields) runs the **copy constructor** (`term.copy-ctor`), which increments the
refcounts of the managed parts. Copies occur on declaration, assignment,
argument passing, return, and field/element stores (Ch.18).

`term.destructor` — the **destructor** of a type is the *deinitialization* run
when a managed allocation's refcount reaches 0: it decrements the refcounts of
the allocation's managed fields (recursively). It is distinct from the **free
function** (`term.free`) recorded in the management header, which then
deallocates the storage. At refcount 0 the destructor runs first, then the free
function — deinitialization is not deallocation.

`term.ownership` — to **own** a reference is to hold a count that must
eventually be released. **Ownership transfer** moves that responsibility from
one party to another (for example, a function return transfers one count to the
caller); a **borrow** (`term.borrow`) is access to a value without owning a
count on it (for example, a raw-pointer parameter borrows its argument).

`term.move` — a **move** transfers ownership from an expiring source to a
destination without a copy, and zeroes the source so its later destruction is a
no-op. Whether and when a move occurs (rather than a copy-then-destroy), and the
extent to which it is a language guarantee, is settled in Ch.18; reference-count
behavior is deterministic and observable.

`term.immortal` — an **immortal** (or **sentinel**) allocation is static data
given a reserved refcount value so that it is never destroyed; this lets static
data be referred to by managed pointers without ever being freed (Ch.18).

`term.cycle` — a **reference cycle** is a set of managed allocations that
reference one another so that none reaches refcount 0. A cycle is a memory leak
and is the programmer's responsibility (break it with a raw pointer); it is not
a defect in the implementation.

## 3.3 Type-system terms

The full rules are Ch.6–Ch.9.

`term.value-type` — a **value type** is a type whose values are copied on
assignment and passing and stored inline (integers, floats, `bool`, pointers
including managed pointers, structs, arrays, slices, interface values, function
values). A `term.reference-type` (**reference type**) is a managed struct: a
heap allocation reached through a managed pointer. (A managed pointer is itself
a value type whose copy has a refcount side effect.)

`term.named-type` — a **named (distinct) type** is introduced by
`type X U` and is a new type distinct from its **underlying type** `U`
(`term.underlying`); it may have methods and implement interfaces. A
`term.alias` (**type alias**) `type X = U` introduces another name for the same
type and cannot have its own methods.

`term.transparency` — **distinct-type transparency** (Go's defined-type model):
a named (distinct) type behaves as its underlying type for operators, the
built-ins that act on the underlying kind (`len`, `present`, `same`), indexing,
slicing, and field access (read and write, including auto-dereference when the
underlying is a pointer) — the checker peels the named wrapper (and any
`readonly` wrapper) to the underlying. **Methods are not inherited**: a distinct
type does not acquire its underlying's methods or impls; declare those on the
distinct type, and reach the underlying's methods through an explicit
conversion (§7.3).

`term.assignability` — **assignability** governs when a value of one type may be
used where another is expected without an explicit conversion. For named types
the rule is Go's: a value crosses the boundary without a `cast` iff the two
types have identical underlying types **and** at least one side is *unnamed*
(§8). 

`term.equivalence` — type identity is **nominal** for named types (two named
types are distinct even with identical structure) and **structural** for
anonymous struct types (two anonymous structs are the same type iff their field
names and types match in order).

`term.untyped-literal` — an **untyped literal** is a constant whose type is not
yet fixed; in a context that needs a type but supplies none, it takes its
**default type** (`term.default-type`) — for example an integer literal
defaults to `int`, a string literal to `@[]readonly char` (Ch.6).

`term.readonly` — **`readonly`** is a *type modifier* denoting read-only access
to the value it qualifies (a property of the type; §7, §9). It is distinct from
**`const`** (`term.const`), which declares a *compile-time constant* (a value
with no storage; §9). The two are different keywords with different meanings.

`term.managed-slice` — a **managed-slice** `@[]T` (written hyphenated) is a
four-word owning view `{data, len, backing, backingLen}` over a managed
backing allocation. A **raw slice** (`term.raw-slice`) `*[]T` is a two-word
non-owning view `{data, len}` that borrows its backing (§7). A managed-slice
owns; a raw slice borrows.

`term.predeclared-name` — a **predeclared name** is an identifier with a
meaning in the universe scope (for example `int`, `bool`, `char`, `true`,
`iota`). Predeclared *names* are ordinary identifiers lexically (they are not
keywords; §5.6) and may be shadowed.

## 3.4 Interface, dispatch, and generic terms

The full rules are Ch.10–Ch.12.

`term.interface` — an **interface** is a named set of method signatures
(Ch.11). An **interface value** (`term.interface-value`) is a two-word value
`{data, vtable}` holding a concrete value together with a dispatch table; it is
written `*Iface` (raw) or `@Iface` (managed).

`term.impl` — an **impl** is a separate declaration `impl T : I` stating that
type `T` satisfies interface `I`. Satisfaction is **nominal and explicit**
(declared, not inferred from structure — there is no duck typing).

`term.method-set` — the **method set** of a type is the methods declared with
that type as receiver. A `term.vtable` (**vtable**) is the per-type dispatch
table used for **dynamic dispatch** (`term.dispatch`) through an interface
value; the concrete vtable layout is informative (Annex B).

`term.self` — **`Self`** is the type, within an interface declaration, that
denotes the implementing type (Ch.11).

`term.function-value` — a **function value** is a callable value: `*func(...)`
(raw) or `@func(...)` (managed), a two-word value whose layout is given in
Ch.10. A **closure** (`term.closure`) is a function value that captures
variables from its environment (by value; Ch.10).

`term.generic` — a **generic** declaration is parameterized by one or more
**type parameters** (`term.type-parameter`), each bound by a single interface
**constraint** (`term.constraint`). **Monomorphization** (`term.monomorphization`)
is the compilation of each distinct set of type arguments into its own code and
its own distinct type (Ch.12).

`term.any` — **`any`** is the empty interface type, satisfied by every type; an
`any` value is a two-word interface value. It is distinct from the opaque byte
pointer `*uint8` (Ch.11, Ch.15).

## 3.5 Execution-model terms

The full model is Ch.2 and Ch.19.

`term.abstract-machine` — the **abstract machine** is the idealized executor
whose observable behavior this specification defines: a **store**
(`term.store`) mapping locations to values, a **heap** of managed allocations
with their reference counts, and a function-pointer call primitive.

`term.compiled` / `term.interpreted` — **compiled mode** executes a program as
native code; **interpreted mode** executes it through an interpreter. Both are
co-equal conforming implementations of the same semantics (Ch.2). A
**thunk** (`term.thunk`) is the bridge that lets a call cross the mode boundary
through a function pointer without the caller knowing the callee's mode (Ch.19).

`term.dual-mode` — **dual-mode interop** is the property that compiled and
interpreted code interoperate through identical data layouts and a shared
function-pointer call mechanism. The *contract* is settled; full in-process
embedding is a goal, not yet realized (Ch.19).

`term.targetinfo` — **`TargetInfo`** is the target description that parameterizes
target-dependent behavior: at least the pointer size, the `int` size, and the
maximum alignment. All target-parameterized behavior (`term.target-parameterized`)
is a function of it.

`term.retained` / `term.immediate` — in **retained mode** a definition is
parsed and stored with validation completed before execution; in **immediate
mode** an expression or statement is executed as entered (the REPL). A
non-interactive program runs entirely retained and is fully validated before it
begins (Ch.17).

`term.hosted` / `term.freestanding` — a **hosted** implementation provides host
facilities (I/O, a process model); a **freestanding** implementation need not.
The core language is specifiable for both (Ch.2).

## 3.6 Lexical and grammatical terms

The full rules are Ch.5.

`term.token` — a **token** is the smallest lexical unit (an identifier,
keyword, literal, operator, or punctuator). A **keyword** (`term.keyword`) is a
reserved identifier; a **builtin-operation keyword** (`term.builtin`) is a
reserved name with special call syntax (e.g. `make`, `len`, `cast`), several of
which take a type as an argument (Ch.5, Ch.15).

`term.asi` — **automatic semicolon insertion** (ASI) is the rule by which a
statement-terminating semicolon is inserted at a line break following certain
tokens (§5.13).

`term.maximal-munch` — **maximal munch** is the rule that at each position the
longest token forming a valid prefix is taken (§5.12).
