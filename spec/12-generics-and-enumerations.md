# 12. Generics and Enumerations

> **Status:** mixed · **Maturity:** language rules Stable (v1 scope); methods + impls on generic types (§12.1 `gen.method.generic-recv` / `gen.impl.generic-recv`) Draft — specified, not yet implemented; one v1-restriction unenforced — see the §12.4 gap (constraint satisfaction unchecked for generic struct/interface instantiation)  
> **Rule-ID prefix:** `gen`

This chapter covers **generics** — type-parameterized functions, structs, and
interfaces, including methods and impls on generic types (§12.1–§12.5) — and the
**enumeration** idiom (§12.6). Several v1 restrictions (no **method-level** type
parameters, no conditional impls, no type inference) are deliberate scope
choices, relaxable later, not instability.

## 12.1 Type parameters and constraints

`gen.typeparams` — A **function**, **struct**, or **interface** may declare
**type parameters** in a bracketed list after its name, each with a constraint:

```
TypeParams    = "[" TypeParamDecl { "," TypeParamDecl } "]" ;
TypeParamDecl = identifier Type ;   (* the Type is checker-restricted — see gen.constraint *)
```

`gen.constraint` — A type parameter's **constraint** is a **single named
interface** or the bare universal `any` (§11.5). There is **no `+` operator** to
combine constraints: to require that a type argument satisfy several interfaces,
declare a combined interface that **extends** them (§11.6) and use it as the
constraint. A `[T any]` parameter is **unconstrained** — it may be used to store
and move `T` values, but no method may be called on a `T` (there are none). The
surface grammar accepts any `Type` in the constraint position; the restriction to
`any` or a named interface is enforced by the **type-checker**, which rejects any
other form with a diagnostic (`ConstraintName` is not a distinct grammar
production).

`gen.no-generic-methods` _(Constraint)_ — A method may not declare **its own**
type parameters — there is no `[…]` after the method name (unlike a free
function; `MethodDecl` has no `TypeParams` slot). A would-be *generic method*
(`func (v Vec[T]) map[U](…)`, where `map` introduces a fresh `[U]`) is rejected
at the declaration with "methods cannot have type parameters": a vtable slot
would have to vary per instantiation of `U`, so such a method is undispatchable —
use a generic **free function** instead (§10.1). This does **not** forbid a
method on a generic *type* (next rule), whose type parameters come from the
**receiver**, not the method.

`gen.method.generic-recv` _(Constraint)_ — A method **on a generic type** binds
the type's parameters through its **receiver**, written as an identifier list on
the base type: `func (it *Cursor[T]) Next() (T, bool)`, `func (m *HashMap[K, V])
get(k K) (V, bool)`. The bracketed names are **binding** occurrences — fresh
type-parameter names, **not** type arguments — and each **shall not** name a
predeclared or in-scope type (predeclared names like `int` are ordinary
identifiers, §5, so a bracket entry that resolves to a type — `Cursor[int]` — is a
*specific-instantiation* receiver, resolved semantically, not a binder; §12.4).
The binders' **constraints are inherited** from the type's declaration (they are
not restated; an unconstrained `[T any]` type yields an unconstrained `T`, on
which no method may be called — `gen.constraint`), and their count **must equal**
the type's arity. The names are in scope for the whole signature and body; the
method itself introduces no type parameter (`gen.no-generic-methods`). Each
`(type, type-argument)` instantiation **monomorphizes** the method to a concrete
signature (`Cursor[int].Next() (int, bool)`; `gen.mono`), so it occupies a fixed
vtable slot and dispatches like any method.

`gen.impl.generic-recv` _(Constraint)_ — An `impl` may have a **parameterized
receiver** that binds the type's parameters (binder names, not type arguments,
per `gen.method.generic-recv`), and its interface list may reference them:
`impl *Cursor[T] : Iterator[T]` asserts that `Cursor[T]`
satisfies `Iterator[T]` for **every** `T` (§11.3 `iface.impl.form`). The
method-shape match (`iface.impl.coverage`) is verified **abstractly** at the `impl`
declaration with the binders held abstract, exactly as for a non-generic impl;
constraint satisfaction and the concrete `(Cursor[int], Iterator[int])` vtable are
resolved **per monomorphized instantiation** (`gen.satisfy`, §12.4). A
**conditional** impl — one carrying an extra constraint beyond the type's own, so
it applies only for some type arguments — is disallowed (`gen.no-conditional-impls`,
§12.4).

> _Note (object-safety)._ A parameterized impl of a generic interface stays
> **object-safe**: `iface.self.object-safety` (§11.9) forbids only `Self` in a
> non-receiver position, which the interface's *own* type parameter (`Iterator`'s
> `T`) does not trigger — post-monomorphization `Iterator[int]`'s methods are
> concrete, so a `*Iterator[int]` value dispatches normally.

> _Open._ A parameterized impl `impl *Cursor[T] : I` **overlaps** a
> *specific-instantiation* impl `impl Cursor[int] : I` (which §12.4
> `gen.no-conditional-impls` currently permits) at `T = int` — two impls of the
> same `(Cursor[int], I)`. The coherence rule for that overlap is **unresolved**; a
> clean v1 choice is to forbid a specific-instantiation impl where a parameterized
> one applies (or specific-instantiation impls entirely). Tracked in
> `claude-todo.md`.

> _Draft; not yet implemented._ Methods on generic types
> (`gen.method.generic-recv`) and parameterized-receiver impls
> (`gen.impl.generic-recv`) are **specified ahead of implementation** (design
> settled — the **Draft** tier, `conventions.md`). Until they land, a generic type
> can carry no methods and thus satisfy no interface, so a generic interface (e.g.
> `Iterator[T]`) is declarable but **not yet implementable**; the high-level plan
> is `explorations/plan-generic-type-methods.md` (tracked in `claude-todo.md`).

> _Note._ A generic-*method* declaration (a method with its own `[…]`) is
> **diagnosed at the declaration** — rejected with "methods cannot have type
> parameters", not deferred to a confusing call-site error.

## 12.2 Instantiation

`gen.instantiate` — A generic is **instantiated** by writing its name followed by
explicit **type arguments**: `Name[T1, T2, …]`. There is **no type inference** —
the type arguments are always written at the instantiation site (`sort[int](xs)`,
`var v Vec[int]`).

`gen.instantiate.disambiguation` — The form `name[…]` is disambiguated between a
type-argument list and an index expression by what `name` resolves to: if it
resolves to a generic declaration, `[…]` is a type-argument list; if it resolves
to an indexable value (a slice or array), `[…]` is an index (§13). This ambiguity
arises **only in expression position**, where the parser emits a combined node and
the type-checker resolves it; in **type-syntax** position (e.g. `var v Vec[int]`)
`Name[…]` is unconditionally a type-argument list — there is no value indexing in
type syntax. The full set of disambiguation rules (D1–D11) is consolidated in
Annex A once authored.

## 12.3 Monomorphization and constraint dispatch

`gen.mono` — Each distinct **(generic declaration, type-argument tuple)** is
**monomorphized** into its own specialized code, and is a **distinct type** (two
instantiations with the same type arguments are the same; with different
arguments are different). There is **no run-time generic dispatch** — a generic
body is specialized per instantiation.

`gen.mono.constraint-call` — A call **through a constraint** in a generic body
(`t.M(…)` where `t : T` and `T`'s constraint declares `M`) is type-checked
against the **constraint interface's** abstract signature at body-check time, and
lowered at instantiation time to a **direct call** to the concrete method named
by the type argument's `impl` — **no vtable, no indirection** (unlike interface
dispatch, §11.11). The instantiated body has the shape of hand-written code over
the concrete type.

## 12.4 Constraint satisfaction

`gen.satisfy` _(Constraint)_ — A type argument `T` satisfies its constraint
interface `I` iff a matching **`impl T : I`** is **visible** at the instantiation
site (nominal and explicit — no duck typing; §11.3). Satisfaction consults `I`'s
**full** method set, including methods inherited from extended interfaces (§11.6).
The method-shape match was verified when the `impl` was declared; instantiation
only confirms a visible `impl` exists. A missing `impl` is an instantiation error
naming the missing satisfaction. (A `[T any]` parameter always satisfies; §12.1.)

> _Open / known gap._ The checker currently enforces constraint satisfaction only
> at **generic-function** instantiation. Generic **struct** and **interface**
> instantiations do not check the type-parameter constraint, so an unsatisfying
> type argument (e.g. `Box[NoOrder]` for `type Box[T Orderable]`, where `NoOrder`
> has no `impl`) is wrongly accepted (`gen.satisfy.struct-iface-unchecked`,
> `claude-todo.md`). **`gen.impl.generic-recv` (§12.1) makes this gap
> load-bearing:** a parameterized impl's per-instantiation satisfaction relies on
> the instantiation-time constraint check being performed.

> _Example._ `func sort[T Orderable](xs *[]T) { … xs[i].Compare(xs[j]) … }`
> instantiated at `T = int` works because `pkg/builtins/lang` provides
> `impl int : Orderable` (§11.10); `int.Compare` is called directly.

`gen.no-conditional-impls` — There are **no conditional impls** in v1 (an `impl`
carrying an extra constraint beyond the type's own, so it applies only for certain
type arguments). A **parameterized** impl that binds the type's parameters and
applies for *all* of them is a different thing and **is** allowed (§12.1
`gen.impl.generic-recv`). A **specific-instantiation** impl (concrete type
arguments, `impl Cursor[int] : …`) may be declared, subject to the unresolved
overlap-with-parameterized question flagged as _Open_ in `gen.impl.generic-recv`.

## 12.5 Cross-package generics

`gen.crosspkg.body` — A consumer package monomorphizes a generic by specializing
its **body**, so the body must be available across the package boundary.
Therefore a **generic** declaration (`func f[T …]`, `type Vec[T …] struct{…}`,
`interface Container[T …] {…}`) carries its full **source-text body** in the
package's `.bni` interface file; **non-generic** declarations remain
signature-only (§16). This is the C++ "template definitions in the header"
model.

> _Note._ Binary-only distribution remains viable for everything except
> generics. `.bni` body versioning across compiler/package versions is out of
> scope for v1.

## 12.6 Enumerations

`gen.enum.no-first-class` — Binate has **no first-class enum type**. An enumeration
is expressed as a **named integer type** together with a grouped `const` block
using `iota` (§9.1):

```
type Opcode uint8

const (
    OpAdd Opcode = iota   // 0
    OpSub                  // 1
    OpMul                  // 2
)
```

The members are typed constants of the named type. Converting between the named
type and its underlying integer (or another integer type) requires an explicit
`cast` (it is a distinct type; §7.3). There is **no exhaustiveness checking** on
such a type.

`gen.enum.bitflags` — A bit-flag set uses `1 << iota`:

```
type Flags uint32

const (
    FlagRead  Flags = 1 << iota   // 1
    FlagWrite                      // 2
    FlagExec                       // 4
)
```

> _Note._ Discriminated (tagged) unions are a separate, future feature; they are
> not provided by this idiom (see Annex D once authored).
