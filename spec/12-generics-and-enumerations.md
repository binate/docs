# 12. Generics and Enumerations

> **Status:** mixed · **Maturity:** language rules Stable (v1 scope); methods + impls on generic types (§12.1 `gen.method.generic-recv` / `gen.impl.generic-recv`) Draft — specified, not yet implemented; one v1-restriction unenforced — see the §12.4 gap (constraint satisfaction unchecked for generic struct/interface instantiation)  
> **Rule-ID prefix:** `gen`

This chapter covers **generics** — type-parameterized functions, structs, and
interfaces, including methods and impls on generic types (§12.1–§12.5) — and the
**enumeration** idiom (§12.6). Several v1 restrictions (no **method-level** type
parameters, no conditional impls, no type inference) are deliberate scope
choices, relaxable later, not instability.

## 12.1 Type parameters and constraints

`gen.typeparams` — A **function**, a **type declaration** (of any underlying
type: a struct, an array, a pointer, a slice, a function value, …), or an
**interface** may declare **type parameters** in a bracketed list after its name,
each with a constraint:

```
TypeParams    = "[" TypeParamDecl { "," TypeParamDecl } "]" ;
TypeParamDecl = identifier Type ;   (* the Type is checker-restricted — see gen.constraint *)
```

The parameter names are **distinct** — no two parameters of one declaration have
the same name — except that any number of them may be the **blank identifier**
`_`, which declares that type parameter **without naming it**
(`func two[_ any, _ any]() int`); `_` is not in scope as a type in the
declaration.

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
predeclared or in-scope type: a bracket entry that resolves to a type
(`Cursor[int]`) would be a **specific-instantiation** receiver, which is
**rejected** (`gen.no-conditional-impls`, §12.4). Predeclared names like `int` are
ordinary identifiers (§5), so this is a semantic check.
The names are **distinct** — no two positions bind the same name — except that any
number of positions may be the **blank identifier** `_`, which binds that type
parameter **without naming it** (`func (p *Pair[_, V]) Second() V`); `_` is not in
scope as a type in the signature or body.
The binders' **constraints are inherited** from the type's declaration **by
position** (they are not restated; an unconstrained `[T any]` type yields an
unconstrained `T`, on which no method may be called — `gen.constraint`): a
constraint that refers to another of the type's parameters (`type W[X any, C
Cont[X]]`) refers to the binder at that parameter's position, whatever the binders
are named (`func (w *W[_, D])`). Their count **must equal** the type's arity. The names are in scope for the whole signature and body; the
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
the constraints of the instantiations in its interface list are satisfied through
the type's parameters' constraints, checked once at the `impl` declaration (§12.3
`gen.mono.check`), while the type argument's satisfaction of the type's own
constraints (`gen.satisfy`, §12.4) and the concrete `(Cursor[int],
Iterator[int])` vtable are resolved **per monomorphized instantiation**. A
**conditional** impl (an extra constraint beyond the type's own) and a
**specific-instantiation** impl (concrete receiver arguments) are **both**
disallowed (`gen.no-conditional-impls`, §12.4): the parameterized form is the
single mechanism, so no impl-overlap can arise.

> _Note (object-safety)._ A parameterized impl of a generic interface stays
> **object-safe**: `iface.self.object-safety` (§11.9) forbids only `Self` in a
> non-receiver position, which the interface's *own* type parameter (`Iterator`'s
> `T`) does not trigger — post-monomorphization `Iterator[int]`'s methods are
> concrete, so a `*Iterator[int]` value dispatches normally.

> _Draft; not yet implemented._ Methods on generic types
> (`gen.method.generic-recv`) and parameterized-receiver impls
> (`gen.impl.generic-recv`) are **specified ahead of implementation** (design
> settled — the **Draft** tier, `conventions.md`). Until they land, a generic type
> can carry no methods and thus satisfy no interface, so a generic interface (e.g.
> `Iterator[T]`) is declarable but **not yet implementable** (Annex C).

> _Note._ A generic-*method* declaration (a method with its own `[…]`) is
> **diagnosed at the declaration** — rejected with "methods cannot have type
> parameters", not deferred to a confusing call-site error.

## 12.2 Instantiation

`gen.instantiate` — A generic is **instantiated** by writing its name followed by
explicit **type arguments**: `Name[T1, T2, …]`. There is **no type inference** —
the type arguments are always written at the instantiation site (`sort[int](xs)`,
`var v Vec[int]`).

`gen.instantiate.type` — An instantiation of a generic type declaration
`type N[P₁, …] U` is a **distinct named type** (`gen.mono`) whose underlying type
is `U` with each type parameter replaced by its type argument, laid out, copied and
operated on as that underlying type, with the methods declared on `N`
(`gen.method.generic-recv`): for `type Pair[T any] [2]T`, `Pair[int32]` is a named
type over `[2]int32`, indexed as an array; for `type List[T any] @[]T`, `List[int]`
is a named managed-slice of `int`. The underlying type may name the instantiation
itself through an indirection (`type Tree[T any] @[]Tree[T]`), but not by value
(`type.named.value-acyclic`).

> _Open._ Whether an **alias** declaration (`type L[T any] = Box[T]`) or a
> declaration with **no** underlying type (an opaque or forward `type L[T any]`)
> may take type parameters is undecided.

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

`gen.mono.instances` _(Constraint)_ — The instantiations a program **names** are:
every instantiation whose type arguments contain no type parameter, written anywhere
in the program's source — in any declaration at any scope, including a function or
method body (whether or not it executes), a signature, a struct field, a variable
or constant declaration, a type or alias declaration, an `impl` declaration's
receiver or interface list, a constraint, a type argument, and a package interface
file (`.bni`) — and, for each instantiation so named, every instantiation its
generic declaration names with its type parameters bound to the type arguments:
for a generic function, in its signature and body; for a generic struct, in its
fields, in the signature and body of **every** method declared on it (whether or
not the program calls it), and in each parameterized `impl` of it
(`gen.impl.generic-recv`); for a generic interface, in its method signatures and
the interfaces it extends. The set of instantiations a program names **shall be
finite**: if an instantiation the program names names, directly or through other
generics, instantiations of its own generic with ever-growing type arguments
(`func f[T any]() { f[@T]() }`, `type L[T any] struct { next @L[@T] }`), the set
is infinite, which is a compile-time error. A generic struct is rejected at its
declaration, whether or not the program names an instantiation of it, if following
fields alone — its own, with its type parameters abstract, then those of each
generic-struct instantiation named there, and so on — reaches instantiations with
ever-growing type arguments (`L` above, or `type E[T any] struct { e E[[1]T] }`):
none of its instantiations could be named. An implementation may bound the length
of a chain of instantiations, each named from the previous one and starting from
one written in the program (which counts as one); the bound is
implementation-defined and at least 128 (§21.4), and a longer chain is a
compile-time error (§2.2 `conf.implementation.limits`).

> _Note._ Every method of a named generic-struct instantiation is included because
> a method on `Box[T]` is promised for every `T` its constraint admits (there are
> no conditional impls, `gen.no-conditional-impls`), and whether a method is
> reachable through an interface's vtable depends on `impl`s anywhere in the
> program. A consequence: the body of a generic in a `.bni` is part of its
> package's interface — a change to it can break a program that names the
> generic.

`gen.mono.check` _(Constraint)_ — In a generic declaration (including a method or
`impl` on a generic type), a construct is **dependent** when checking it needs a
fact that depends on a type argument:
- `sizeof` or `alignof` of a type in which a type parameter occurs (directly, or
  in an element, field or pointee type, a type argument, or an array length),
  `len` of an array whose length is such a value, and a constant expression or
  array length using such a value;
- the rules that consume such a value: the fit of such a constant to the type its
  context requires (§6.4 `const.expr.fit`, including a constant `cast`, §8.5
  `conv.cast.const-not-laundered`), array type identity and assignability where a
  length is such a value (§7.5 `type.array.form`, `type.array.value`; §8.1), the
  positions an array literal of such a length fills (§13.10
  `expr.composite.array`, `expr.composite.array.indexed`), and the size equality
  `bit_cast` requires (§8.6);
- a use of a type in which a type parameter occurs that requires its layout — a
  by-value variable, field, parameter or result, `make` or `make_slice` — which the
  opaque-type gate restricts (§7.12 `type.opaque.builtin-rejection`, §15.2
  `builtin.opaque-gate`);
- the validity of a `cast`, `bit_cast` or `unsafe_cast` whose source or target type
  is one in which a type parameter occurs (§8.9 `conv.typeparam`), and of a type
  assertion or type-switch case whose target names a type parameter (§11.12
  `iface.assert.typeparam`);
- the type a function literal takes from the target of a `cast` or `unsafe_cast`
  in which a type parameter occurs (§10.9 `func.lit.inferred-default`), and with it
  where a capturing literal's closure record lives (§10.10
  `func.closure.allocation`): each instantiation's literal has its own target type,
  so `cast(T, func(x int) int { return x + k })` is a raw closure kept in the frame
  where `T` is a `*func` and a managed closure where it is a `@func`.

The check of a generic declaration against its type parameters' constraints
decides every other rule once, for all its instantiations, and **defers** the
dependent constructs: each is checked for every instantiation the program names
(`gen.mono.instances`), with the type parameters bound to the type arguments, and
a violation is a compile-time error. In that check:
- names resolve where the generic is declared;
- the `impl`s, visibility and opacity of a type supplied by a root instantiation's
  type arguments are those at that root — the instantiation written in the program
  that the chain of instantiations started from; a type written in a generic's own
  declaration is judged where it is written;
- an instantiation whose type arguments are built from the enclosing
  declaration's type parameters satisfies its constraints through those
  parameters' constraints (`gen.satisfy` is not re-established per
  instantiation).

An instantiation named through several chains is checked for each. A generic of
which the program names no instantiation is **not** checked for its dependent
constructs, even ones no type argument could satisfy. A violation found in a named
instantiation (this rule, §8.9 `conv.typeparam`, §11.12
`iface.assert.typeparam`, or `gen.mono.instances`) is
reported at the instantiation written in the program, and identifies the position
of the violating construct in the generic and the chain of instantiations that led
to it. An interactive interpreter checks an instantiation when an input names it
(`conf.implementation.timing`).

> _Example._
> ```
> func scale[T any]() uint8 { return cast(uint8, sizeof(T) * 100) }
> scale[int8]()    // accepted: 100 fits uint8
> scale[int64]()   // compile-time error: 800 does not fit uint8
> ```

> _Note._ Both branches of an `if` whose condition depends on a type parameter are
> checked for every instantiation: `if sizeof(T) == 4 { … bit_cast(uint32, t) … }
> else { … bit_cast(uint64, t) … }` fails at least one branch's size check for
> every `T`, so no instantiation of it is accepted.

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
> has no `impl`) is wrongly accepted (`gen.satisfy.struct-iface-unchecked`;
> Annex C). **`gen.impl.generic-recv` (§12.1) makes this gap
> load-bearing:** a parameterized impl's per-instantiation satisfaction relies on
> the instantiation-time constraint check being performed.

> _Example._ `func sort[T Orderable](xs *[]T) { … xs[i].Compare(xs[j]) … }`
> instantiated at `T = int` works because `pkg/builtins/lang` provides
> `impl int : Orderable` (§11.10); `int.Compare` is called directly.

`gen.no-conditional-impls` _(Constraint)_ — Neither a **conditional** impl (one
carrying an extra constraint beyond the type's own, so it applies only for certain
type arguments) nor a **specific-instantiation** impl (concrete type arguments in
the receiver, `impl Cursor[int] : …`) is allowed in v1. An `impl` on a generic type
uses only the **parameterized** form, which binds the type's parameters and applies
for *all* of them (§12.1 `gen.impl.generic-recv`) — the single mechanism, so no
impl-overlap can arise. (A **plain** type implementing a generic *interface*
instantiation — `impl IntBox : Container[int]` — is unrelated and allowed: its
receiver is not a generic instantiation.) These restrictions are v1 scope choices,
relaxable later.

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
